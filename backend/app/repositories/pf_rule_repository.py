
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.common.errors import RuleNotFoundError
from app.engine.common.hashing import compute_sha256_hash
from app.engine.dto.pf_dto import PfRuleSet
from app.models.pf import PFRuleVersion


class PfRuleRepository:
    """Hydrates immutable PfRuleSet DTO from PostgreSQL with statutory EPFO provenance."""

    def __init__(self, db: Session):
        self.db = db

    def get_pf_rule_set(self, financial_year: str) -> PfRuleSet:
        stmt = select(PFRuleVersion).where(
            PFRuleVersion.version_code.like(f"PFRV-{financial_year}%"),
            PFRuleVersion.status == "ACTIVE",
        )
        pfrv: PFRuleVersion | None = self.db.scalar(stmt)
        if not pfrv or not pfrv.rules:
            # Fallback to current active rule if specific FY shell not distinct
            pfrv = self.db.scalar(select(PFRuleVersion).where(PFRuleVersion.status == "ACTIVE"))
            if not pfrv or not pfrv.rules:
                raise RuleNotFoundError(f"No active statutory EPFO PF rule version found for Financial Year '{financial_year}'.")

        rule = pfrv.rules[0]
        source_citation = "EPFO India / Employees' Provident Funds Scheme, 1952"
        source_doc_hash = compute_sha256_hash("EPFO-STATUTORY-SCHEDULE-1952")

        raw_rule_dict = {
            "version_code": pfrv.version_code,
            "employee_epf_rate": str(rule.employee_epf_rate),
            "employer_epf_rate": str(rule.employer_epf_rate),
            "employer_eps_rate": str(rule.employer_eps_rate),
            "employer_edli_rate": str(rule.employer_edli_rate),
            "wage_ceiling": str(rule.statutory_wage_ceiling),
        }
        rule_set_hash = compute_sha256_hash(raw_rule_dict)

        return PfRuleSet(
            rule_version_code=pfrv.version_code,
            employee_epf_rate=rule.employee_epf_rate,
            employer_epf_rate=rule.employer_epf_rate,
            employer_eps_rate=rule.employer_eps_rate,
            employer_edli_rate=rule.employer_edli_rate,
            admin_charges_rate=rule.admin_charges_rate,
            statutory_wage_ceiling=rule.statutory_wage_ceiling,
            eps_wage_ceiling=rule.eps_wage_ceiling,
            vpf_allowed=rule.vpf_allowed,
            source_citation=source_citation,
            source_document_hash=source_doc_hash,
            rule_set_hash=rule_set_hash,
        )
