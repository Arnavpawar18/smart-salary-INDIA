from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_middleware import get_current_user
from app.core.config import rate_limit_settings
from app.core.database import get_db
from app.core.limiter import RateLimiter
from app.engine.common.enums import TaxRegime
from app.engine.common.errors import FinancialEngineError
from app.engine.dto.salary_dto import SalaryInput
from app.models.auth import User
from app.models.calculation import CalculationRun, CalculationSnapshot
from app.models.employee import Employee
from app.schemas.calculation import (
    CalculationRequest,
    CalculationResponse,
    RegimeComparisonResponse,
)
from app.services.calculation_service import CalculationService

router = APIRouter()


@router.post("", response_model=CalculationResponse, status_code=status.HTTP_201_CREATED)
async def calculate_salary(
    req: CalculationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    # Apply calculation rate limiting
    await RateLimiter.check_rate_limit(
        request,
        max_requests=rate_limit_settings.CALC_RATE_LIMIT,
        window_seconds=rate_limit_settings.CALC_RATE_WINDOW,
        key_prefix="calc",
    )
    """Execute authoritative salary, tax, PF, and PT calculation with ledger and trace."""
    try:
        service = CalculationService(db)
        regime_enum = TaxRegime(req.regime.upper())

        salary_inp = SalaryInput(
            financial_year=req.financial_year,
            annual_gross=req.annual_gross_salary,
            monthly_gross=req.monthly_gross_salary,
            annual_ctc=req.annual_ctc,
            basic_salary=req.components.basic if req.components else None,
            da=req.components.da if req.components else None,
            hra=req.components.hra if req.components else None,
            special_allowance=req.components.special_allowance if req.components else None,
            bonus=req.components.bonus if req.components else None,
            other_allowances=req.components.other_allowances if req.components else None,
            other_employee_deductions=req.components.other_deductions if req.components else None,
            pf_opt_in_higher_wage=req.pf_opt_in_higher_wage,
        )

        emp = db.scalar(select(Employee).where(Employee.user_id == current_user.id)) if current_user else None
        emp_id = emp.id if emp else None

        res = service.calculate_salary(
            salary_input=salary_inp,
            regime=regime_enum,
            state_code=req.state_code.upper(),
            age=req.age,
            employee_id=emp_id,
            persist=True,
        )
        return res.to_dict()
    except FinancialEngineError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calculation failed: {str(e)}")


@router.post("/compare-regimes", response_model=RegimeComparisonResponse)
async def compare_tax_regimes(
    req: CalculationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Apply calculation rate limiting for regime comparison
    await RateLimiter.check_rate_limit(
        request,
        max_requests=rate_limit_settings.CALC_RATE_LIMIT,
        window_seconds=rate_limit_settings.CALC_RATE_WINDOW,
        key_prefix="calc_compare",
    )
    """Compare Old vs New tax regimes simultaneously using identical normalized salary input."""
    try:
        service = CalculationService(db)
        salary_inp = SalaryInput(
            financial_year=req.financial_year,
            annual_gross=req.annual_gross_salary,
            monthly_gross=req.monthly_gross_salary,
            annual_ctc=req.annual_ctc,
            basic_salary=req.components.basic if req.components else None,
            da=req.components.da if req.components else None,
            hra=req.components.hra if req.components else None,
            special_allowance=req.components.special_allowance if req.components else None,
            bonus=req.components.bonus if req.components else None,
            other_allowances=req.components.other_allowances if req.components else None,
            other_employee_deductions=req.components.other_deductions if req.components else None,
            pf_opt_in_higher_wage=req.pf_opt_in_higher_wage,
        )

        comp = service.compare_regimes(
            salary_input=salary_inp,
            state_code=req.state_code.upper(),
            age=req.age,
            persist=False,
        )
        return comp.to_dict()
    except FinancialEngineError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/history")
def get_calculation_history(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns paginated calculation history strictly scoped to authenticated employee.
    Enforces object-level authorization (IDOR defense).
    """
    emp = db.scalar(select(Employee).where(Employee.user_id == current_user.id))
    if not emp:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size

    stmt = (
        select(CalculationRun)
        .where(
            CalculationRun.employee_id == emp.id,
            CalculationRun.status != "DELETED",
        )
        .order_by(CalculationRun.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(db.scalars(stmt).all())

    return {
        "items": [
            {
                "id": r.id,
                "financial_year": r.financial_year,
                "regime": r.regime,
                "total_taxable_income": str(r.total_taxable_income),
                "total_tax_liability": str(r.total_tax_liability),
                "net_take_home_annual": str(r.net_take_home_annual),
                "net_take_home_monthly": str(r.net_take_home_monthly),
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ],
        "page": page,
        "page_size": page_size,
    }


@router.get("/{calculation_id}")
def get_calculation_detail(
    calculation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns immutable calculation run, snapshot, and mathematical trace.
    Strict Object-Level IDOR defense: calculation must belong to current_user.employee_id.
    """
    emp = db.scalar(select(Employee).where(Employee.user_id == current_user.id))
    employee_id = emp.id if emp else -1

    run = db.scalar(
        select(CalculationRun).where(
            CalculationRun.id == calculation_id,
            CalculationRun.employee_id == employee_id,
            CalculationRun.status != "DELETED",
        )
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found or unauthorized")

    snapshot = db.scalar(select(CalculationSnapshot).where(CalculationSnapshot.calculation_run_id == run.id))

    return {
        "id": run.id,
        "employee_id": run.employee_id,
        "financial_year": run.financial_year,
        "regime": run.regime,
        "status": run.status,
        "total_taxable_income": str(run.total_taxable_income),
        "total_tax_liability": str(run.total_tax_liability),
        "net_take_home_annual": str(run.net_take_home_annual),
        "net_take_home_monthly": str(run.net_take_home_monthly),
        "snapshot": {
            "input_snapshot": snapshot.input_snapshot if snapshot else {},
            "result_snapshot": snapshot.result_snapshot if snapshot else {},
            "input_hash": snapshot.input_hash if snapshot else "",
            "result_hash": snapshot.result_hash if snapshot else "",
            "engine_version": snapshot.engine_version if snapshot else "1.0.0",
            "rounding_policy_version": snapshot.rounding_policy_version if snapshot else "1.0.0",
        }
        if snapshot
        else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


@router.delete("/{calculation_id}")
def delete_calculation_from_history(
    calculation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Logical/Soft-Delete Calculation from User's History.
    IDOR Protected: User can only soft-delete their own calculations.
    Statutory Snapshot Immutability: The underlying CalculationSnapshot audit record is preserved.
    """
    emp = db.scalar(select(Employee).where(Employee.user_id == current_user.id))
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee record not found")

    run = db.scalar(
        select(CalculationRun).where(
            CalculationRun.id == calculation_id,
            CalculationRun.employee_id == emp.id,
        )
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found or unauthorized")

    # Mark as logically deleted without mutating or deleting the immutable CalculationSnapshot
    run.status = "DELETED"
    db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Calculation #{calculation_id} removed from history.",
        "calculation_id": calculation_id,
    }
