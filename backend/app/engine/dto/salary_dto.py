from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Optional
from app.engine.common.money import to_decimal


@dataclass(frozen=True)
class SalaryInput:
    """Raw user input for salary calculation."""
    financial_year: str
    annual_ctc: Optional[Decimal] = None
    annual_gross: Optional[Decimal] = None
    monthly_gross: Optional[Decimal] = None
    basic_salary: Optional[Decimal] = None
    da: Optional[Decimal] = None
    hra: Optional[Decimal] = None
    special_allowance: Optional[Decimal] = None
    bonus: Optional[Decimal] = None
    other_allowances: Optional[Decimal] = None
    other_employee_deductions: Optional[Decimal] = None
    pf_opt_in_higher_wage: bool = False
    custom_components: Dict[str, Decimal] = field(default_factory=dict)


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
    annual_ctc: Optional[Decimal] = None

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
