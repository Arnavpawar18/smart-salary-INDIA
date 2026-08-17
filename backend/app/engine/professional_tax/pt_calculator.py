from decimal import Decimal
from app.engine.common.enums import Gender
from app.engine.common.money import quantize_currency
from app.engine.dto.pt_dto import PtCalculationInput, PtCalculationResult, PtRuleSet


class PtCalculator:
    """
    Pure Zero-I/O Professional Tax Engine.
    Matches monthly gross salary against state slab schedules and evaluates February adjustments.
    """

    @classmethod
    def calculate_pt(
        cls,
        inp: PtCalculationInput,
        rules: PtRuleSet,
    ) -> PtCalculationResult:
        monthly_gross = inp.monthly_gross_salary
        gender = inp.gender

        matching_slab = None
        for slab in sorted(rules.slabs, key=lambda s: s.slab_order):
            if monthly_gross >= slab.from_monthly_salary:
                if slab.to_monthly_salary is None or monthly_gross <= slab.to_monthly_salary:
                    # Check gender applicability
                    if slab.gender_applicable == Gender.ALL or slab.gender_applicable == gender:
                        matching_slab = slab
                        break

        if not matching_slab:
            monthly_pt = Decimal("0.00")
            february_pt = Decimal("0.00")
        else:
            monthly_pt = matching_slab.monthly_tax_amount
            february_pt = (
                matching_slab.february_tax_amount
                if matching_slab.february_tax_amount is not None
                else monthly_pt
            )

        # 11 months standard + 1 month February
        annual_pt = quantize_currency((monthly_pt * Decimal("11")) + february_pt)

        return PtCalculationResult(
            state_code=rules.state_code,
            monthly_pt=monthly_pt,
            february_pt=february_pt,
            annual_pt=annual_pt,
            rule_version_code=rules.rule_version_code,
        )
