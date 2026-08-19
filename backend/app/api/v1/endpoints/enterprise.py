from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant_context import TenantContext, get_tenant_context
from app.models.compliance import StatutoryComplianceEvent, TaxDeclaration
from app.models.employee import Employee
from app.models.payroll import PayrollRun

router = APIRouter(prefix="/enterprise", tags=["Enterprise Admin & Payroll"])


@router.get("/dashboard-summary")
def get_enterprise_dashboard(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Returns executive metrics for the enterprise tenant:
    - Active headcount
    - Latest payroll run status & summary
    - Compliance status & pending events
    - Tax declaration progress
    """
    org_id = ctx.organization_id

    # 1. Headcount
    headcount = (
        db.scalar(
            select(func.count(Employee.id)).where(
                Employee.organization_id == org_id,
                Employee.employment_status == "ACTIVE",
            )
        )
        or 0
    )

    # 2. Latest Payroll Run
    latest_run = db.scalar(
        select(PayrollRun).where(PayrollRun.organization_id == org_id).order_by(PayrollRun.created_at.desc())
    )

    # 3. Pending Declarations
    pending_declarations = (
        db.scalar(
            select(func.count(TaxDeclaration.id)).where(
                TaxDeclaration.organization_id == org_id,
                TaxDeclaration.status.in_(["SUBMITTED", "UNDER_REVIEW"]),
            )
        )
        or 0
    )

    # 4. Pending Compliance Events
    pending_compliance = (
        db.scalar(
            select(func.count(StatutoryComplianceEvent.id)).where(
                StatutoryComplianceEvent.organization_id == org_id,
                StatutoryComplianceEvent.status == "PENDING",
            )
        )
        or 0
    )

    return {
        "organization": {
            "id": ctx.organization.id,
            "legal_name": ctx.organization.legal_name,
            "display_name": ctx.organization.display_name,
            "organization_code": ctx.organization.organization_code,
            "role": ctx.role_name,
        },
        "headcount": headcount,
        "latest_payroll_run": {
            "id": latest_run.id if latest_run else None,
            "status": latest_run.status if latest_run else "NONE",
            "total_gross_earnings": str(latest_run.total_gross_earnings) if latest_run else "0.00",
            "total_net_pay": str(latest_run.total_net_pay) if latest_run else "0.00",
            "total_employer_cost": str(latest_run.total_employer_cost) if latest_run else "0.00",
            "result_hash": latest_run.result_hash if latest_run else None,
        }
        if latest_run
        else None,
        "pending_declarations_count": pending_declarations,
        "pending_compliance_events_count": pending_compliance,
    }


@router.get("/employees")
def list_organization_employees(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lists employees scoped strictly to the authenticated tenant."""
    stmt = (
        select(Employee)
        .where(Employee.organization_id == ctx.organization_id)
        .order_by(Employee.id)
        .limit(limit)
        .offset(offset)
    )
    employees = list(db.scalars(stmt).all())
    return [
        {
            "id": e.id,
            "employee_code": e.employee_code,
            "name": f"{e.first_name} {e.last_name}",
            "email": e.email,
            "employment_status": e.employment_status,
            "date_of_joining": e.date_of_joining.isoformat(),
        }
        for e in employees
    ]
