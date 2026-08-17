from decimal import Decimal

from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.tax_dto import TaxCalculationInput
from app.engine.tax.tax_calculator import TaxCalculator
from app.repositories.tax_rule_repository import TaxRuleRepository


def test_tax_engine_zero_tax_under_rebate_new_regime_ay2627():
    """Salary ₹12,00,000 under FY 2025-26 New Regime with ₹75k std deduction -> Taxable ₹11.25L <= ₹12L -> Tax = ₹0."""
    with SessionLocal() as db:
        repo = TaxRuleRepository(db)
        rules = repo.get_tax_rule_set("2025-26", TaxRegime.NEW)

        inp = TaxCalculationInput(
            financial_year="2025-26",
            regime=TaxRegime.NEW,
            annual_gross_salary=Decimal("1200000.00"),
        )
        res = TaxCalculator.calculate_tax(inp, rules)

        assert res["standard_deduction"] == Decimal("75000.00")
        assert res["taxable_income"] == Decimal("1125000.00")
        # Slab tax: 0-4L:0, 4-8L(5%):20k, 8-11.25L(10%):32.5k -> Total ₹52,500
        assert res["slab_tax"] == Decimal("52500.00")
        assert res["section_87a_rebate"] == Decimal("52500.00")
        assert res["total_annual_tax_liability"] == Decimal("0.00")


def test_tax_engine_taxable_above_rebate_new_regime_ay2627():
    """Salary ₹15,75,000 under FY 2025-26 New Regime -> Taxable ₹15,00,000 -> Slabs: 0-4L:0, 4-8L:20k, 8-12L:40k, 12-15L(15%):45k -> Slab Tax ₹1,05,000 + 4% cess = ₹1,09,200."""
    with SessionLocal() as db:
        repo = TaxRuleRepository(db)
        rules = repo.get_tax_rule_set("2025-26", TaxRegime.NEW)

        inp = TaxCalculationInput(
            financial_year="2025-26",
            regime=TaxRegime.NEW,
            annual_gross_salary=Decimal("1575000.00"),
        )
        res = TaxCalculator.calculate_tax(inp, rules)

        assert res["taxable_income"] == Decimal("1500000.00")
        assert res["slab_tax"] == Decimal("105000.00")
        assert res["section_87a_rebate"] == Decimal("0.00")
        assert res["health_education_cess"] == Decimal("4200.00")
        assert res["total_annual_tax_liability"] == Decimal("109200.00")


def test_tax_engine_old_regime():
    """Old Regime ₹12,00,000 with ₹50k std deduction and ₹1.5L 80C -> Taxable ₹10,00,000 -> Slab Tax: 0-2.5L:0, 2.5-5L:12.5k, 5-10L(20%):100k -> ₹1,12,500 + 4% = ₹1,17,000."""
    with SessionLocal() as db:
        repo = TaxRuleRepository(db)
        rules = repo.get_tax_rule_set("2025-26", TaxRegime.OLD)

        inp = TaxCalculationInput(
            financial_year="2025-26",
            regime=TaxRegime.OLD,
            annual_gross_salary=Decimal("1200000.00"),
            section_80c=Decimal("150000.00"),
        )
        res = TaxCalculator.calculate_tax(inp, rules)

        assert res["standard_deduction"] == Decimal("50000.00")
        assert res["claimed_80c"] == Decimal("150000.00")
        assert res["taxable_income"] == Decimal("1000000.00")
        assert res["slab_tax"] == Decimal("112500.00")
        assert res["health_education_cess"] == Decimal("4500.00")
        assert res["total_annual_tax_liability"] == Decimal("117000.00")
