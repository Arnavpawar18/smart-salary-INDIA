from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.pf import PFRuleVersion
from app.models.pt import ProfessionalTaxRuleVersion
from app.models.tax import TaxRuleVersion

router = APIRouter()


@router.get("/summary")
def get_rules_summary(db: Session = Depends(get_db)):
    """Expose active statutory rule summaries without revealing sensitive parameters."""
    tax_rules = db.scalars(select(TaxRuleVersion).where(TaxRuleVersion.status == "ACTIVE")).all()
    pf_rules = db.scalars(select(PFRuleVersion).where(PFRuleVersion.status == "ACTIVE")).all()
    pt_rules = db.scalars(select(ProfessionalTaxRuleVersion).where(ProfessionalTaxRuleVersion.status == "ACTIVE")).all()

    return {
        "tax_rule_versions": [{"version": tr.version_code, "regime": tr.regime, "status": tr.status} for tr in tax_rules],
        "pf_rule_versions": [{"version": pf.version_code, "status": pf.status} for pf in pf_rules],
        "professional_tax_configured_states": [{"version": pt.version_code, "state_id": pt.state_id} for pt in pt_rules],
    }
