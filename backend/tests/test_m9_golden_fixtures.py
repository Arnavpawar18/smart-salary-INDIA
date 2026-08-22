"""
Milestone M9.7: Golden Fixtures & Trace Hash Baselines
Validates standardized golden benchmark profiles (Fresher, Mid-Level, Executive, Contractor).
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_m9_golden_fresher_bangalore():
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("450000.00"))
        res = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="KA", persist=False)
        assert res.standard_deduction == Decimal("75000.00")
        assert res.taxable_income == Decimal("375000.00")
        assert res.total_annual_tax_liability == Decimal("0.00")
        assert res.annual_employee_pf == Decimal("21600.00")
        assert res.annual_professional_tax == Decimal("2400.00")
        assert res.estimated_annual_take_home == Decimal("426000.00")


def test_m9_golden_senior_lead_mumbai():
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("2400000.00"))
        res = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="MH", persist=False)
        assert res.standard_deduction == Decimal("75000.00")
        assert res.taxable_income == Decimal("2325000.00")
        # 23.25L taxable: 0-4L 0; 4-8L 20k; 8-12L 40k; 12-16L 60k; 16-20L 80k; 20-23.25L (3.25L @ 25%) = 81,250 -> Total slab tax = 281,250 -> Cess 4% = 11,250 -> Total = 292,500
        assert res.slab_tax == Decimal("281250.00")
        assert res.total_annual_tax_liability == Decimal("292500.00")
        assert res.annual_professional_tax == Decimal("2500.00")
