"""
Milestone M9.2: Jurisdiction Legality & State PT Isolation Matrix
Verifies statutory PT calculation across KA, MH, TN, TS, WB, GJ and fail-closed handling for unsupported/unconfigured states.
"""

from decimal import Decimal

import pytest

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.engine.oracle.independent_oracle import IndependentRegulatoryOracle
from app.services.calculation_service import CalculationService


@pytest.mark.parametrize(
    "state_code,annual_gross,expected_annual_pt",
    [
        ("KA", Decimal("1200000.00"), Decimal("2400.00")),
        ("MH", Decimal("1200000.00"), Decimal("2500.00")),
        ("TS", Decimal("1200000.00"), Decimal("2400.00")),
        ("WB", Decimal("1200000.00"), Decimal("2400.00")),
        ("GJ", Decimal("1200000.00"), Decimal("2400.00")),
        ("TN", Decimal("1200000.00"), Decimal("2500.00")),
    ],
)
def test_m9_jurisdiction_pt_rates_match_oracle(state_code, annual_gross, expected_annual_pt):
    oracle_pt = IndependentRegulatoryOracle.calculate_annual_pt(state_code, annual_gross)
    assert oracle_pt == expected_annual_pt

    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=annual_gross)
        res = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code=state_code, persist=False)
        assert res.annual_professional_tax == expected_annual_pt


def test_m9_jurisdiction_unsupported_state_fails_closed():
    with SessionLocal() as db:
        service = CalculationService(db)
        with pytest.raises(Exception):
            inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1000000.00"))
            service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="XX_INVALID", persist=False)
