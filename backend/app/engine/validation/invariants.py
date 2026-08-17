from decimal import Decimal
from app.engine.common.errors import CalculationInvariantViolationError
from app.engine.dto.salary_dto import NormalizedSalary


class FinancialInvariantsValidator:
    """Validates mathematical and financial invariants before calculation persistence."""

    @staticmethod
    def validate(
        salary: NormalizedSalary,
        total_tax: Decimal,
        employee_pf: Decimal,
        annual_pt: Decimal,
        take_home_annual: Decimal,
    ) -> None:
        if salary.annual_gross < Decimal("0.00"):
            raise CalculationInvariantViolationError(f"Gross salary cannot be negative: {salary.annual_gross}")

        if total_tax < Decimal("0.00"):
            raise CalculationInvariantViolationError(f"Tax liability cannot be negative: {total_tax}")

        if employee_pf < Decimal("0.00"):
            raise CalculationInvariantViolationError(f"Employee PF cannot be negative: {employee_pf}")

        if annual_pt < Decimal("0.00"):
            raise CalculationInvariantViolationError(f"Professional tax cannot be negative: {annual_pt}")

        expected_take_home = salary.annual_gross - total_tax - employee_pf - annual_pt - salary.other_employee_deductions
        if abs(take_home_annual - expected_take_home) > Decimal("1.00"):
            raise CalculationInvariantViolationError(
                f"Take-home reconciliation invariant failed: computed {take_home_annual}, expected {expected_take_home}"
            )
