from decimal import Decimal
import pytest
from app.core.database import SessionLocal
from app.engine.common.enums import Gender
from app.engine.dto.pt_dto import PtCalculationInput
from app.engine.professional_tax.pt_calculator import PtCalculator
from app.repositories.pt_rule_repository import PtRuleRepository


def test_pt_engine_karnataka():
    """Karnataka: Monthly gross ₹1,00,000 >= ₹15,000 -> Monthly ₹200, Annual ₹2,400."""
    with SessionLocal() as db:
        repo = PtRuleRepository(db)
        rules = repo.get_pt_rule_set("KA")

        inp = PtCalculationInput(state_code="KA", monthly_gross_salary=Decimal("100000.00"))
        res = PtCalculator.calculate_pt(inp, rules)

        assert res.monthly_pt == Decimal("200.00")
        assert res.annual_pt == Decimal("2400.00")


def test_pt_engine_maharashtra_february_adjustment():
    """Maharashtra: Monthly gross ₹50,000 -> Monthly ₹200, Feb ₹300 -> Annual ₹2,500."""
    with SessionLocal() as db:
        repo = PtRuleRepository(db)
        rules = repo.get_pt_rule_set("MH")

        inp = PtCalculationInput(state_code="MH", monthly_gross_salary=Decimal("50000.00"))
        res = PtCalculator.calculate_pt(inp, rules)

        assert res.monthly_pt == Decimal("200.00")
        assert res.february_pt == Decimal("300.00")
        assert res.annual_pt == Decimal("2500.00")  # (200*11) + 300 = 2500
