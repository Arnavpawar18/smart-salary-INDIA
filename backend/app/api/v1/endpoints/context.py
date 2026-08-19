from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.employee import Department, JobRole, State
from app.models.pt import ProfessionalTaxRuleVersion
from app.presentation.financial_year import FinancialYearResolver

router = APIRouter()


@router.get("/context")
def get_ui_context(db: Session = Depends(get_db)):
    """Provides dynamic Indian FY, active states with PT availability status, departments, and job roles."""
    current_fy = FinancialYearResolver.get_current_financial_year()
    supported_fys = FinancialYearResolver.validate_and_get_supported_years(db)

    # Active states and PT configuration status
    active_pt_state_ids = set(
        db.scalars(
            select(ProfessionalTaxRuleVersion.state_id).where(ProfessionalTaxRuleVersion.status == "ACTIVE")
        ).all()
    )

    states = db.scalars(select(State).order_by(State.name)).all()
    states_data = []
    for s in states:
        has_pt = s.id in active_pt_state_ids or s.code == "DL"  # Delhi is officially exempt
        states_data.append(
            {
                "code": s.code,
                "name": s.name,
                "is_union_territory": s.is_union_territory,
                "pt_configured": has_pt,
                "pt_status_label": "Exempt" if s.code == "DL" else ("Configured" if has_pt else "Not Configured"),
            }
        )

    departments = db.scalars(select(Department).order_by(Department.name)).all()
    depts_data = [{"code": d.code, "name": d.name} for d in departments]

    job_roles = db.scalars(select(JobRole).order_by(JobRole.title)).all()
    jobs_data = [{"code": j.code, "title": j.title} for j in job_roles]

    return {
        "current_financial_year": current_fy,
        "supported_financial_years": supported_fys,
        "default_regime": "NEW",
        "states": states_data,
        "departments": depts_data,
        "job_roles": jobs_data,
        "capabilities": {
            "income_tax_slabs": True,
            "section_87a_rebate": True,
            "standard_deduction": True,
            "section_80c_old_regime": True,
            "section_80d_old_regime": True,
            "epfo_provident_fund": True,
            "state_professional_tax": True,
            "hra_exemption_calculation": False,
            "senior_citizen_special_slabs": False,
        },
    }
