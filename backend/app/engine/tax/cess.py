from decimal import Decimal
from typing import List
from app.engine.common.money import quantize_currency
from app.engine.dto.tax_dto import TaxCessRuleDTO


class CessCalculator:
    """Calculates Health and Education Cess on (Tax + Surcharge - Relief)."""

    @staticmethod
    def calculate_cess(tax_base: Decimal, cess_rules: List[TaxCessRuleDTO]) -> Decimal:
        if tax_base <= Decimal("0.00") or not cess_rules:
            return Decimal("0.00")

        total_cess = Decimal("0.00")
        for rule in cess_rules:
            total_cess += quantize_currency(tax_base * rule.cess_rate)

        return total_cess
