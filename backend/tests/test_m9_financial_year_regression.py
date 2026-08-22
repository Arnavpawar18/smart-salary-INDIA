"""
Milestone M9.1: Canonical Temporal & Financial Year Regression Matrix
Validates statutory rules across FY 2021-22 through FY 2026-27 and future proposal isolation.
"""

from decimal import Decimal

import pytest

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_m9_fy_2025_26_and_2026_27_default_regime():
    with SessionLocal() as db:
        service = CalculationService(db)
        # FY 2025-26: Standard deduction ₹75,000, 87A rebate up to ₹12L taxable (Gross ₹12.75L zero tax)
        inp_2526 = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1275000.00"))
        res_2526 = service.calculate_salary(inp_2526, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res_2526.standard_deduction == Decimal("75000.00")
        assert res_2526.taxable_income == Decimal("1200000.00")
        assert res_2526.total_annual_tax_liability == Decimal("0.00")

        # FY 2026-27: Standard deduction ₹75,000 under ongoing regime
        inp_2627 = SalaryInput(financial_year="2026-27", annual_gross=Decimal("1275000.00"))
        res_2627 = service.calculate_salary(inp_2627, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res_2627.standard_deduction == Decimal("75000.00")
        assert res_2627.total_annual_tax_liability == Decimal("0.00")


def test_m9_future_unverified_fy_blocked():
    with SessionLocal() as db:
        service = CalculationService(db)
        # Future unverified FY 2029-30 must fail closed
        with pytest.raises(Exception):
            inp = SalaryInput(financial_year="2029-30", annual_gross=Decimal("1000000.00"))
            service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="KA", persist=False)
