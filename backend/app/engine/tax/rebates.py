from decimal import Decimal

from app.engine.common.money import quantize_currency
from app.engine.dto.tax_dto import TaxRebateRuleDTO


class RebateCalculator:
    """Calculates Section 87A rebate based on statutory thresholds and maximum rebate limits."""

    @staticmethod
    def calculate_rebate(
        taxable_income: Decimal,
        slab_tax: Decimal,
        rebate_rules: list[TaxRebateRuleDTO],
        is_resident: bool = True,
    ) -> Decimal:
        if not is_resident or slab_tax <= Decimal("0.00") or not rebate_rules:
            return Decimal("0.00")

        # Pick matching rule
        matching_rule: TaxRebateRuleDTO | None = None
        for r in rebate_rules:
            if taxable_income <= r.taxable_income_threshold:
                matching_rule = r
                break

        if not matching_rule:
            return Decimal("0.00")

        # Rebate is lower of actual slab tax or max rebate amount
        return quantize_currency(min(slab_tax, matching_rule.max_rebate_amount))
