from decimal import Decimal
from typing import List
from app.engine.common.money import quantize_currency
from app.engine.dto.tax_dto import TaxSurchargeRuleDTO


class SurchargeCalculator:
    """Calculates income tax surcharge based on income brackets."""

    @staticmethod
    def calculate_surcharge(
        taxable_income: Decimal,
        tax_after_rebate: Decimal,
        surcharge_rules: List[TaxSurchargeRuleDTO],
    ) -> Decimal:
        if tax_after_rebate <= Decimal("0.00") or not surcharge_rules:
            return Decimal("0.00")

        matching_rule = next(
            (r for r in surcharge_rules if r.from_income <= taxable_income and (r.to_income is None or taxable_income <= r.to_income)),
            None,
        )

        if not matching_rule:
            return Decimal("0.00")

        return quantize_currency(tax_after_rebate * matching_rule.surcharge_rate)
