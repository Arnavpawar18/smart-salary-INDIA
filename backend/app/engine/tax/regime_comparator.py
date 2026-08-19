from decimal import Decimal

from app.engine.common.enums import TaxRegime
from app.engine.dto.tax_dto import TaxCalculationInput, TaxRuleSet
from app.engine.tax.tax_calculator import TaxCalculator


class RegimeComparator:
    """
    Simultaneously computes tax liability under both OLD and NEW regimes
    for the exact same normalized salary input and compares savings.
    """

    @classmethod
    def compare(
        cls,
        base_input: TaxCalculationInput,
        old_rules: TaxRuleSet,
        new_rules: TaxRuleSet,
    ) -> tuple[dict[str, Decimal], dict[str, Decimal], Decimal, TaxRegime, str]:
        # Calculate Old Regime
        old_inp = TaxCalculationInput(
            financial_year=base_input.financial_year,
            regime=TaxRegime.OLD,
            annual_gross_salary=base_input.annual_gross_salary,
            age=base_input.age,
            residential_status=base_input.residential_status,
            section_80c=base_input.section_80c,
            section_80d=base_input.section_80d,
            other_exemptions=base_input.other_exemptions,
            other_deductions=base_input.other_deductions,
            tds_already_deducted=base_input.tds_already_deducted,
        )
        old_res = TaxCalculator.calculate_tax(old_inp, old_rules)

        # Calculate New Regime
        new_inp = TaxCalculationInput(
            financial_year=base_input.financial_year,
            regime=TaxRegime.NEW,
            annual_gross_salary=base_input.annual_gross_salary,
            age=base_input.age,
            residential_status=base_input.residential_status,
            section_80c=Decimal("0.00"),  # 80C not allowed in New Regime
            section_80d=Decimal("0.00"),  # 80D not allowed in New Regime
            other_exemptions=Decimal("0.00"),
            other_deductions=Decimal("0.00"),
            tds_already_deducted=base_input.tds_already_deducted,
        )
        new_res = TaxCalculator.calculate_tax(new_inp, new_rules)

        old_tax = old_res["total_annual_tax_liability"]
        new_tax = new_res["total_annual_tax_liability"]

        tax_diff = abs(old_tax - new_tax)

        if new_tax < old_tax:
            recommended = TaxRegime.NEW
            note = f"New Tax Regime results in lower estimated tax liability by ₹{tax_diff:,.2f} based on the supplied income and deductions."
        elif old_tax < new_tax:
            recommended = TaxRegime.OLD
            note = f"Old Tax Regime results in lower estimated tax liability by ₹{tax_diff:,.2f} based on the claimed Chapter VI-A deductions."
        else:
            recommended = TaxRegime.NEW
            note = (
                "Both Old and New regimes result in identical estimated tax liability for the supplied income profile."
            )

        return old_res, new_res, tax_diff, recommended, note
