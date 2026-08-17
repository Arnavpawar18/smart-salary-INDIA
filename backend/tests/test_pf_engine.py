from decimal import Decimal
import pytest
from app.core.database import SessionLocal
from app.engine.dto.pf_dto import PfCalculationInput
from app.engine.pf.pf_calculator import PfCalculator
from app.repositories.pf_rule_repository import PfRuleRepository


def test_pf_engine_statutory_ceiling_default():
    """Basic ₹50,000/mo without higher-wage opt-in -> capped at ₹15,000 ceiling -> Employee PF = 12% of 15k = ₹1,800/mo (₹21,600/yr)."""
    with SessionLocal() as db:
        repo = PfRuleRepository(db)
        rules = repo.get_pf_rule_set("2025-26")

        inp = PfCalculationInput(
            pf_wage_base_monthly=Decimal("50000.00"),
            is_pf_applicable=True,
            opt_in_higher_wage=False,
        )
        res = PfCalculator.calculate_pf(inp, rules)

        assert res.monthly_employee_epf == Decimal("1800.00")
        assert res.annual_employee_epf == Decimal("21600.00")
        assert res.monthly_employer_eps == Decimal("1249.50")  # 8.33% of 15k
        assert res.monthly_employer_edli == Decimal("75.00")   # 0.50% of 15k


def test_pf_engine_higher_wage_opt_in():
    """Basic ₹50,000/mo with higher-wage opt-in -> Employee PF = 12% of ₹50,000 = ₹6,000/mo (₹72,000/yr), EPS capped at ₹1,249.50."""
    with SessionLocal() as db:
        repo = PfRuleRepository(db)
        rules = repo.get_pf_rule_set("2025-26")

        inp = PfCalculationInput(
            pf_wage_base_monthly=Decimal("50000.00"),
            is_pf_applicable=True,
            opt_in_higher_wage=True,
        )
        res = PfCalculator.calculate_pf(inp, rules)

        assert res.monthly_employee_epf == Decimal("6000.00")
        assert res.annual_employee_epf == Decimal("72000.00")
        assert res.monthly_employer_eps == Decimal("1249.50")
        assert res.monthly_employer_epf == Decimal("4750.50")  # 6000 - 1249.50
