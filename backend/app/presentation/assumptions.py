from dataclasses import dataclass
from decimal import Decimal

from app.engine.dto.salary_dto import NormalizedSalary


@dataclass(frozen=True)
class QuickEstimateAssumptionSet:
    """
    Formal, transparent assumption contract for Quick Estimate mode.
    Exposes exact normalizer defaults used in the calculation.
    """

    is_quick_mode: bool
    basic_salary_percentage_derived: str
    additional_allowances_assumed: Decimal
    additional_deductions_assumed: Decimal
    pf_applicability_assumed: str
    regime_default_applied: str
    monthly_tax_allocation_method: str
    assumption_bullet_points: list[str]

    @classmethod
    def from_normalized_salary(
        cls,
        normalized: NormalizedSalary,
        is_quick_mode: bool,
        regime_str: str,
    ) -> "QuickEstimateAssumptionSet":
        if is_quick_mode:
            bullets = [
                f"Basic salary derived as 50% of monthly gross (₹{normalized.basic_salary / Decimal('12'):,.2f}/mo) for PF wage evaluation.",
                "Standard statutory deduction under Section 16(ia) automatically applied.",
                "No additional Chapter VI-A investments (80C/80D) or HRA exemptions assumed in Quick Mode.",
                "Provident Fund capped at statutory ₹15,000 monthly wage ceiling.",
                "Monthly tax is an estimated even allocation (Annual Tax ÷ 12); actual payroll TDS may vary.",
            ]
            return cls(
                is_quick_mode=True,
                basic_salary_percentage_derived="50.0%",
                additional_allowances_assumed=Decimal("0.00"),
                additional_deductions_assumed=Decimal("0.00"),
                pf_applicability_assumed="Statutory ₹15k Ceiling",
                regime_default_applied=regime_str,
                monthly_tax_allocation_method="Annual Tax / 12 (Projected)",
                assumption_bullet_points=bullets,
            )
        else:
            bullets = [
                "Calculation computed using explicit employee-supplied salary component breakdown.",
                "Provident Fund computed on explicit Basic + DA wage base.",
                "Statutory Standard Deduction applied automatically.",
                "Monthly tax is an estimated even allocation (Annual Tax ÷ 12); actual payroll TDS may vary.",
            ]
            return cls(
                is_quick_mode=False,
                basic_salary_percentage_derived="Explicit Component Breakdown",
                additional_allowances_assumed=normalized.special_allowance
                + normalized.bonus
                + normalized.other_allowances,
                additional_deductions_assumed=normalized.other_employee_deductions,
                pf_applicability_assumed="Explicit Basic Base",
                regime_default_applied=regime_str,
                monthly_tax_allocation_method="Annual Tax / 12 (Projected)",
                assumption_bullet_points=bullets,
            )
