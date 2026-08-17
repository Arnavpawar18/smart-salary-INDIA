import pytest
from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.common.errors import ProfessionalTaxRuleNotConfiguredError, RuleNotFoundError
from app.services.rule_applicability import RuleApplicabilityResolver


def test_rule_resolver_success_for_ka_new_regime():
    with SessionLocal() as db:
        resolver = RuleApplicabilityResolver(db)
        tax_rules, pf_rules, pt_rules = resolver.resolve_all("2025-26", TaxRegime.NEW, "KA")

        assert tax_rules.financial_year == "2025-26"
        assert tax_rules.regime == TaxRegime.NEW
        assert len(tax_rules.slabs) == 7
        assert pf_rules.employee_epf_rate > 0
        assert pt_rules.state_code == "KA"
        assert len(tax_rules.rule_set_hash) == 64


def test_rule_resolver_fail_closed_unconfigured_state():
    with SessionLocal() as db:
        resolver = RuleApplicabilityResolver(db)
        with pytest.raises(ProfessionalTaxRuleNotConfiguredError):
            # Himachal Pradesh PT is not configured
            resolver.resolve_all("2025-26", TaxRegime.NEW, "HP")


def test_rule_resolver_fail_closed_invalid_fy():
    with SessionLocal() as db:
        resolver = RuleApplicabilityResolver(db)
        with pytest.raises(RuleNotFoundError):
            resolver.resolve_all("1999-00", TaxRegime.NEW, "KA")
