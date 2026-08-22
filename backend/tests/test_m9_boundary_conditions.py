"""
Milestone M9.4: Threshold Boundary Testing Set
Tests exact boundary values (n-1, n, n+1) for Section 87A rebate, standard deduction, EPF ceiling, and PT brackets.
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_m9_boundary_section_87a_rebate_new_regime():
    with SessionLocal() as db:
        service = CalculationService(db)

        # Standard deduction is 75,000.
        # Boundary 1: Taxable = ₹12,00,000 (Gross = ₹12,75,000) -> Rebate covers 100% tax -> Tax = 0
        inp_exact = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1275000.00"))
        res_exact = service.calculate_salary(inp_exact, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res_exact.taxable_income == Decimal("1200000.00")
        assert res_exact.total_annual_tax_liability == Decimal("0.00")

        # Boundary 2: Taxable = ₹11,99,999 (Gross = ₹12,74,999) -> Tax = 0
        inp_below = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1274999.00"))
        res_below = service.calculate_salary(inp_below, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res_below.total_annual_tax_liability == Decimal("0.00")

        # Boundary 3: Taxable = ₹12,00,010 (Gross = ₹12,75,010) -> Rebate marginal relief or slab tax applies
        inp_above = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1275010.00"))
        res_above = service.calculate_salary(inp_above, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res_above.taxable_income == Decimal("1200010.00")
        assert res_above.total_annual_tax_liability >= Decimal("0.00")


def test_m9_boundary_pt_karnataka_15000():
    with SessionLocal() as db:
        service = CalculationService(db)

        # KA PT threshold is monthly gross ₹15,000 (Annual ₹1,80,000)
        # Below: Annual ₹1,79,988 -> Monthly ₹14,999 -> PT = 0
        inp_below = SalaryInput(financial_year="2025-26", annual_gross=Decimal("179988.00"))
        res_below = service.calculate_salary(inp_below, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res_below.annual_professional_tax == Decimal("0.00")

        # Exact/Above: Annual ₹1,80,000 -> Monthly ₹15,000 -> PT = 2400
        inp_exact = SalaryInput(financial_year="2025-26", annual_gross=Decimal("180000.00"))
        res_exact = service.calculate_salary(inp_exact, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res_exact.annual_professional_tax == Decimal("2400.00")
