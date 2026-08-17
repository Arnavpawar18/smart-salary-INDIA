from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService


def test_golden_scenario_1_rebate_limit_zero_tax():
    """
    Scenario 1: Gross ₹12,00,000 in KA under FY 2025-26 New Regime.
    - Gross: ₹12,00,000
    - Std Ded: ₹75,000 -> Taxable: ₹11,25,000
    - Slab Tax: ₹52,500
    - 87A Rebate: ₹52,500 (since taxable <= 12L)
    - Income Tax: ₹0.00
    - Employee PF: ₹21,600 (12% of capped 15k)
    - Professional Tax (KA): ₹2,400
    - Take-Home: 12,00,000 - 0 - 21,600 - 2,400 = ₹11,76,000
    """
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1200000.00"))
        res = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="KA", persist=False)

        assert res.annual_gross_salary == Decimal("1200000.00")
        assert res.standard_deduction == Decimal("75000.00")
        assert res.taxable_income == Decimal("1125000.00")
        assert res.slab_tax == Decimal("52500.00")
        assert res.section_87a_rebate == Decimal("52500.00")
        assert res.total_annual_tax_liability == Decimal("0.00")
        assert res.annual_employee_pf == Decimal("21600.00")
        assert res.annual_professional_tax == Decimal("2400.00")
        assert res.estimated_annual_take_home == Decimal("1176000.00")
        assert res.estimated_monthly_take_home == Decimal("98000.00")


def test_golden_scenario_2_taxable_above_rebate():
    """
    Scenario 2: Gross ₹15,75,000 in MH under FY 2025-26 New Regime.
    - Gross: ₹15,75,000
    - Std Ded: ₹75,000 -> Taxable: ₹15,00,000
    - Slabs: 0-4L:0, 4-8L(5%):20k, 8-12L(10%):40k, 12-15L(15%):45k -> Slab Tax ₹1,05,000
    - Rebate 87A: ₹0.00
    - Cess (4%): ₹4,200
    - Total Tax: ₹1,09,200
    - Employee PF: ₹21,600
    - Professional Tax (MH): ₹2,500 (with Feb adjustment)
    - Take-Home: 15,75,000 - 1,09,200 - 21,600 - 2,500 = ₹14,41,700
    """
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1575000.00"))
        res = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="MH", persist=False)

        assert res.taxable_income == Decimal("1500000.00")
        assert res.slab_tax == Decimal("105000.00")
        assert res.section_87a_rebate == Decimal("0.00")
        assert res.health_education_cess == Decimal("4200.00")
        assert res.total_annual_tax_liability == Decimal("109200.00")
        assert res.annual_professional_tax == Decimal("2500.00")
        assert res.estimated_annual_take_home == Decimal("1441700.00")


def test_golden_scenario_3_regime_comparison():
    """
    Scenario 3: Gross ₹15,75,000 in KA comparison.
    - New Regime Tax: ₹1,09,200
    - Old Regime Tax (without 80C declarations): Std Ded 50k -> Taxable 15.25L -> Slab Tax 2.70L + 4% = ₹2,80,800
    - Recommendation: NEW REGIME by ₹1,71,600
    """
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1575000.00"))
        comp = service.compare_regimes(inp, state_code="KA", persist=False)

        assert comp.new_regime.total_annual_tax_liability == Decimal("109200.00")
        assert comp.old_regime.total_annual_tax_liability == Decimal("280800.00")
        assert comp.tax_difference == Decimal("171600.00")
        assert comp.recommended_regime == TaxRegime.NEW
