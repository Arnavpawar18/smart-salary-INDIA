from decimal import Decimal

from app.engine.common.money import quantize_currency
from app.engine.dto.tax_dto import TaxSlabRuleDTO


class SlabCalculator:
    """Calculates progressive income tax bracket-by-bracket based on statutory slabs."""

    @staticmethod
    def calculate_slab_tax(taxable_income: Decimal, slabs: list[TaxSlabRuleDTO]) -> tuple[Decimal, list[dict]]:
        total_tax = Decimal("0.00")
        slab_breakdowns = []

        sorted_slabs = sorted(slabs, key=lambda s: s.slab_order)

        for slab in sorted_slabs:
            from_amt = slab.from_amount
            to_amt = slab.to_amount
            rate = slab.tax_rate

            if taxable_income <= from_amt:
                # Income does not reach this slab
                taxable_in_slab = Decimal("0.00")
                tax_in_slab = Decimal("0.00")
            else:
                if to_amt is not None:
                    taxable_in_slab = min(taxable_income, to_amt) - from_amt
                else:
                    taxable_in_slab = taxable_income - from_amt

                tax_in_slab = quantize_currency(taxable_in_slab * rate)
                total_tax += tax_in_slab

            slab_breakdowns.append(
                {
                    "slab_order": slab.slab_order,
                    "from_amount": from_amt,
                    "to_amount": to_amt,
                    "tax_rate": rate,
                    "taxable_in_slab": taxable_in_slab,
                    "tax_in_slab": tax_in_slab,
                }
            )

        return total_tax, slab_breakdowns
