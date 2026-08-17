from typing import Tuple
from sqlalchemy.orm import Session

from app.engine.common.enums import TaxRegime
from app.engine.dto.pf_dto import PfRuleSet
from app.engine.dto.pt_dto import PtRuleSet
from app.engine.dto.tax_dto import TaxRuleSet
from app.repositories.pf_rule_repository import PfRuleRepository
from app.repositories.pt_rule_repository import PtRuleRepository
from app.repositories.tax_rule_repository import TaxRuleRepository


class RuleApplicabilityResolver:
    """
    Evaluates context (FY, Regime, State, Profile, Wage characteristics)
    and resolves authoritative, immutable RuleSets across Tax, PF, and PT domains.
    """

    def __init__(self, db: Session):
        self.tax_repo = TaxRuleRepository(db)
        self.pf_repo = PfRuleRepository(db)
        self.pt_repo = PtRuleRepository(db)

    def resolve_all(
        self,
        financial_year: str,
        regime: TaxRegime,
        state_code: str,
    ) -> Tuple[TaxRuleSet, PfRuleSet, PtRuleSet]:
        """Resolves immutable rule sets with fail-closed domain error checking."""
        tax_rules = self.tax_repo.get_tax_rule_set(financial_year, regime)
        pf_rules = self.pf_repo.get_pf_rule_set(financial_year)
        pt_rules = self.pt_repo.get_pt_rule_set(state_code)

        return tax_rules, pf_rules, pt_rules
