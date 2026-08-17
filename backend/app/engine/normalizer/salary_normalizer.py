from decimal import Decimal

from app.engine.common.errors import InvalidSalaryInputError
from app.engine.common.money import quantize_currency, to_decimal
from app.engine.dto.salary_dto import NormalizedSalary, SalaryInput


class SalaryNormalizer:
    """Validates salary inputs, annualizes figures, and categorizes components into a strict NormalizedSalary."""

    STANDARD_BASIC_RATIO = Decimal("0.50")
    STANDARD_HRA_RATIO = Decimal("0.20")
    STANDARD_SPECIAL_ALLOWANCE_RATIO = Decimal("0.30")

    @classmethod
    def normalize(cls, inp: SalaryInput) -> NormalizedSalary:
        # Validate non-negativity across all fields
        for attr, val in inp.__dict__.items():
            if isinstance(val, Decimal) and val < Decimal("0"):
                raise InvalidSalaryInputError(f"Salary field '{attr}' cannot be negative: {val}")

        # Determine gross salary
        annual_gross: Decimal | None = None
        if inp.annual_gross is not None and inp.annual_gross > Decimal("0"):
            annual_gross = quantize_currency(inp.annual_gross)
        elif inp.monthly_gross is not None and inp.monthly_gross > Decimal("0"):
            annual_gross = quantize_currency(inp.monthly_gross * Decimal("12"))
        elif inp.annual_ctc is not None and inp.annual_ctc > Decimal("0"):
            # If CTC is provided without gross, baseline gross estimation uses CTC (employer PF separated later)
            annual_gross = quantize_currency(inp.annual_ctc)

        # Process individual components if supplied
        basic = to_decimal(inp.basic_salary)
        da = to_decimal(inp.da)
        hra = to_decimal(inp.hra)
        special = to_decimal(inp.special_allowance)
        bonus = to_decimal(inp.bonus)
        other_allowances = to_decimal(inp.other_allowances)
        other_deductions = to_decimal(inp.other_employee_deductions)

        sum_components = basic + da + hra + special + bonus + other_allowances

        # If individual components are provided and gross was not explicitly given, gross = sum of components
        if sum_components > Decimal("0"):
            if annual_gross is not None and annual_gross > Decimal("0"):
                # If both provided, verify consistency (allowing special allowance to balance if needed)
                if abs(sum_components - annual_gross) > Decimal("1.00"):
                    # Adjust special allowance to reconcile if components are partial
                    if special == Decimal("0") and sum_components < annual_gross:
                        special = annual_gross - (basic + da + hra + bonus + other_allowances)
            else:
                annual_gross = quantize_currency(sum_components)
        elif annual_gross is not None and annual_gross > Decimal("0"):
            # Standard Indian compensation structure default distribution (50% Basic, 20% HRA, 30% Special)
            basic = quantize_currency(annual_gross * cls.STANDARD_BASIC_RATIO)
            hra = quantize_currency(annual_gross * cls.STANDARD_HRA_RATIO)
            special = quantize_currency(annual_gross - (basic + hra))
        else:
            raise InvalidSalaryInputError("At least one positive salary amount (annual_gross, monthly_gross, or annual_ctc) must be provided.")

        if annual_gross <= Decimal("0"):
            raise InvalidSalaryInputError("Annual gross salary must be greater than zero.")

        monthly_gross = quantize_currency(annual_gross / Decimal("12"))
        pf_wage_base_monthly = quantize_currency((basic + da) / Decimal("12"))

        return NormalizedSalary(
            annual_gross=annual_gross,
            basic_salary=basic,
            da=da,
            hra=hra,
            special_allowance=special,
            bonus=bonus,
            other_allowances=other_allowances,
            other_employee_deductions=other_deductions,
            monthly_gross=monthly_gross,
            pf_wage_base_monthly=pf_wage_base_monthly,
            annual_ctc=inp.annual_ctc,
        )
