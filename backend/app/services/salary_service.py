from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.engine.common.money import quantize_currency
from app.engine.dto.result_dto import VerifiedCalculationResult


@dataclass(frozen=True)
class MonthlyPaycheckRow:
    month_index: int
    month_name: str
    calendar_year: int
    gross_salary: Decimal
    estimated_tax_allocation: Decimal
    employee_epf: Decimal
    professional_tax: Decimal
    other_deductions: Decimal
    net_take_home: Decimal
    employer_epf: Decimal
    employer_eps: Decimal
    employer_edli: Decimal
    total_employer_contribution: Decimal


@dataclass(frozen=True)
class PaycheckProjectionPolicy:
    """
    Explicit projection policy for 12-month payroll schedule:
    - Monthly Tax: Annual tax / 12 (labeled as Estimated Monthly Tax Allocation, not actual Form 16 withholding)
    - Monthly EPF: Actual statutory monthly contribution
    - Monthly PT: Actual state monthly schedule (e.g., MH Feb = ₹300)
    - Non-deductible employer contributions (EPF, EPS, EDLI) isolated as employer value.
    """

    disclaimer: str = (
        "Notice: Monthly tax is an estimated even allocation (Annual Tax ÷ 12). "
        "Actual employer payroll TDS may vary based on investment proof submission timing and bonuses."
    )


class SalaryService:
    """Application service for presentation projections, monthly paychecks, and employer contribution isolation."""

    MONTH_NAMES = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]

    @classmethod
    def generate_monthly_schedule(
        cls,
        result: VerifiedCalculationResult,
        is_mh_state: bool = False,
    ) -> list[MonthlyPaycheckRow]:
        start_year = int(result.financial_year[:4])
        monthly_gross = quantize_currency(result.annual_gross_salary / Decimal("12"))
        monthly_tax = result.estimated_monthly_tax
        monthly_epf = result.monthly_employee_pf
        other_ded = quantize_currency(result.other_employee_deductions / Decimal("12"))

        # Employer breakdown
        total_monthly_employer = result.monthly_employer_contribution
        employer_eps = min(Decimal("1249.50"), quantize_currency(monthly_gross * Decimal("0.0833")))
        employer_edli = Decimal("75.00") if total_monthly_employer > 0 else Decimal("0.00")
        employer_epf = max(Decimal("0.00"), total_monthly_employer - employer_eps - employer_edli)

        schedule = []
        for i, m_name in enumerate(cls.MONTH_NAMES):
            cal_year = start_year if i < 9 else start_year + 1

            # PT month-awareness
            if result.state_code == "MH" and m_name == "Feb":
                pt_amount = Decimal("300.00")
            elif result.state_code == "DL":
                pt_amount = Decimal("0.00")
            else:
                pt_amount = result.monthly_professional_tax

            take_home = max(Decimal("0.00"), monthly_gross - monthly_tax - monthly_epf - pt_amount - other_ded)

            schedule.append(
                MonthlyPaycheckRow(
                    month_index=i + 1,
                    month_name=m_name,
                    calendar_year=cal_year,
                    gross_salary=monthly_gross,
                    estimated_tax_allocation=monthly_tax,
                    employee_epf=monthly_epf,
                    professional_tax=pt_amount,
                    other_deductions=other_ded,
                    net_take_home=take_home,
                    employer_epf=employer_epf,
                    employer_eps=employer_eps,
                    employer_edli=employer_edli,
                    total_employer_contribution=total_monthly_employer,
                )
            )

        return schedule

    @classmethod
    def compute_analytical_metrics(
        cls,
        result: VerifiedCalculationResult,
    ) -> dict[str, Any]:
        """
        Derives presentation-only analytical metrics from Phase 2 authoritative result.
        """
        gross = result.annual_gross_salary
        take_home = result.estimated_annual_take_home
        tax = result.total_annual_tax_liability
        taxable_inc = result.taxable_income

        effective_take_home_rate = (take_home / gross * Decimal("100")) if gross > 0 else Decimal("0.00")
        effective_tax_rate = (tax / taxable_inc * Decimal("100")) if taxable_inc > 0 else Decimal("0.00")
        total_statutory_deductions = tax + result.annual_employee_pf + result.annual_professional_tax
        indicative_employment_cost = gross + result.annual_employer_contribution

        return {
            "effective_take_home_rate": quantize_currency(effective_take_home_rate),
            "effective_tax_rate": quantize_currency(effective_tax_rate),
            "total_statutory_deductions": total_statutory_deductions,
            "indicative_employment_cost": indicative_employment_cost,
        }
