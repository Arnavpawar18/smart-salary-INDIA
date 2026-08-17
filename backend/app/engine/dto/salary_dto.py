from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class SalaryInput:
    """Raw user input for salary calculation."""
    financial_year: str
    annual_ctc: Decimal | None = None
    annual_gross: Decimal | None = None
    monthly_gross: Decimal | None = None
    basic_salary: Decimal | None = None
    da: Decimal | None = None
    hra: Decimal | None = None
    special_allowance: Decimal | None = None
    bonus: Decimal | None = None
    other_allowances: Decimal | None = None
    other_employee_deductions: Decimal | None = None
    pf_opt_in_higher_wage: bool = False
    custom_components: dict[str, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedSalary:
    """Validated, categorized, annualized salary structure with distinct deduction breakdowns."""
    annual_gross: Decimal
    basic_salary: Decimal
    da: Decimal
    hra: Decimal
    special_allowance: Decimal
    bonus: Decimal
    other_allowances: Decimal
    other_employee_deductions: Decimal
    monthly_gross: Decimal
    pf_wage_base_monthly: Decimal
    annual_ctc: Decimal | None = None

    def to_dict(self) -> dict:
        return {
            "annual_gross": f"{self.annual_gross:.2f}",
            "basic_salary": f"{self.basic_salary:.2f}",
            "da": f"{self.da:.2f}",
            "hra": f"{self.hra:.2f}",
            "special_allowance": f"{self.special_allowance:.2f}",
            "bonus": f"{self.bonus:.2f}",
            "other_allowances": f"{self.other_allowances:.2f}",
            "other_employee_deductions": f"{self.other_employee_deductions:.2f}",
            "monthly_gross": f"{self.monthly_gross:.2f}",
            "pf_wage_base_monthly": f"{self.pf_wage_base_monthly:.2f}",
            "annual_ctc": f"{self.annual_ctc:.2f}" if self.annual_ctc is not None else None,
        }
