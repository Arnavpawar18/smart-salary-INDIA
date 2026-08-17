from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.engine.common.enums import TaxRegime
from app.engine.common.errors import FinancialEngineError
from app.engine.dto.salary_dto import SalaryInput
from app.schemas.calculation import (
    CalculationRequest,
    CalculationResponse,
    RegimeComparisonResponse,
)
from app.services.calculation_service import CalculationService

router = APIRouter()


@router.post("", response_model=CalculationResponse, status_code=status.HTTP_201_CREATED)
def calculate_salary(
    req: CalculationRequest,
    db: Session = Depends(get_db),
):
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

        res = service.calculate_salary(
            salary_input=salary_inp,
            regime=regime_enum,
            state_code=req.state_code.upper(),
            age=req.age,
            persist=True,
        )
        return res.to_dict()
    except FinancialEngineError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calculation failed: {str(e)}")


@router.post("/compare-regimes", response_model=RegimeComparisonResponse)
def compare_tax_regimes(
    req: CalculationRequest,
    db: Session = Depends(get_db),
):
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
