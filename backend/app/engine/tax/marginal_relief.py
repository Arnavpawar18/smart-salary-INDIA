from decimal import Decimal

from app.engine.common.money import quantize_currency
from app.engine.dto.tax_dto import TaxRebateRuleDTO, TaxSurchargeRuleDTO


class MarginalReliefCalculator:
    """Calculates Section 87A rebate marginal relief and high-income surcharge marginal relief."""

    @staticmethod
    def calculate_rebate_marginal_relief(
        taxable_income: Decimal,
        slab_tax: Decimal,
        rebate_rules: list[TaxRebateRuleDTO],
    ) -> Decimal:
        """
        Under the New Regime (Section 115BAC), if taxable income slightly exceeds the rebate limit
        (e.g., ₹12,00,000 for AY 26-27 or ₹7,00,000 for AY 25-26), the tax payable cannot exceed
        the income in excess of the threshold.
        """
        if not rebate_rules or slab_tax <= Decimal("0.00"):
            return Decimal("0.00")

        # Find highest threshold rule where marginal relief applies
        rule = next((r for r in rebate_rules if r.marginal_relief_applicable), None)
        if not rule:
            return Decimal("0.00")

        threshold = rule.taxable_income_threshold
        if taxable_income <= threshold:
            return Decimal("0.00")  # Handled by standard full rebate

        excess_income = taxable_income - threshold
        if slab_tax > excess_income:
            relief = slab_tax - excess_income
            return quantize_currency(relief)

        return Decimal("0.00")

    @staticmethod
    def calculate_surcharge_marginal_relief(
        taxable_income: Decimal,
        tax_on_income: Decimal,
        surcharge_amount: Decimal,
        surcharge_rules: list[TaxSurchargeRuleDTO],
    ) -> Decimal:
        """Calculates marginal relief on surcharge thresholds (e.g. ₹50L, ₹1Cr)."""
        if surcharge_amount <= Decimal("0.00") or not surcharge_rules:
            return Decimal("0.00")

        # Find matching threshold
        matching_rule = next(
            (
                r
                for r in surcharge_rules
                if r.from_income <= taxable_income and (r.to_income is None or taxable_income <= r.to_income)
            ),
            None,
        )
        if not matching_rule or not matching_rule.marginal_relief_applicable:
            return Decimal("0.00")

        threshold = matching_rule.from_income
        excess_income = taxable_income - threshold

        # Tax payable on threshold income
        # Surcharge marginal relief caps (tax + surcharge) to (tax on threshold + excess income)
        # For simplicity, calculate maximum excess cap
        total_tax_and_surcharge = tax_on_income + surcharge_amount
        max_allowed = tax_on_income + excess_income

        if total_tax_and_surcharge > max_allowed:
            return quantize_currency(total_tax_and_surcharge - max_allowed)

        return Decimal("0.00")
