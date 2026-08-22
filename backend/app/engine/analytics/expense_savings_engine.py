"""
SmartSalary India — Expense & Savings Financial Health Engine (M2.4)
Enforces statutory invariant: Expense != Tax Deduction unless explicitly authorized by a verified statutory rule.
Computes Cash Surplus, Savings Rate, Expense Ratio, Discretionary Breakdowns, and Negative Cash-Flow alerts.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.engine.common.errors import InvalidSalaryInputError
from app.engine.common.money import quantize_currency, to_decimal


class ExpenseFrequency(StrEnum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    ANNUAL = "ANNUAL"
    ONE_TIME = "ONE_TIME"


class ExpenseNature(StrEnum):
    ESSENTIAL = "ESSENTIAL"  # Rent, Groceries, Utilities, Healthcare, Debt EMIs
    DISCRETIONARY = "DISCRETIONARY"  # Dining, Travel, Entertainment, Subscriptions
    ONE_TIME = "ONE_TIME"  # Major asset purchase, emergency repairs


class SavingsVehicle(StrEnum):
    EPF = "EPF"
    PPF = "PPF"
    NPS = "NPS"
    ELSS = "ELSS"
    DIRECT_EQUITY = "DIRECT_EQUITY"
    MUTUAL_FUNDS = "MUTUAL_FUNDS"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"
    GOLD = "GOLD"
    SAVINGS_ACCOUNT = "SAVINGS_ACCOUNT"
    OTHER = "OTHER"


@dataclass(frozen=True)
class ExpenseItemInput:
    category: str
    amount: Decimal
    frequency: ExpenseFrequency = ExpenseFrequency.MONTHLY
    nature: ExpenseNature = ExpenseNature.ESSENTIAL
    is_statutory_deduction_claim: bool = False
    statutory_section: str | None = None  # e.g., "80C", "80D", "24(b)"


@dataclass(frozen=True)
class SavingsItemInput:
    vehicle: SavingsVehicle
    amount: Decimal
    frequency: ExpenseFrequency = ExpenseFrequency.MONTHLY
    qualifies_section_80c: bool = False
    qualifies_section_80ccd_1b: bool = False  # NPS ₹50k additional


@dataclass(frozen=True)
class NormalizedExpenseSummary:
    annual_essential_expenses: Decimal
    annual_discretionary_expenses: Decimal
    annual_one_time_expenses: Decimal
    total_annual_expenses: Decimal
    monthly_average_expenses: Decimal

    # Financial Health Metrics
    annual_net_take_home: Decimal
    annual_total_savings: Decimal
    annual_cash_surplus: Decimal
    monthly_cash_surplus: Decimal

    savings_rate_pct: Decimal
    expense_to_income_ratio_pct: Decimal
    essential_to_income_ratio_pct: Decimal
    is_negative_cash_flow: bool

    # Categorized Mappings for Tax Bridge
    statutory_tax_deductions_from_expenses: Decimal
    statutory_80c_from_savings: Decimal
    statutory_80ccd_from_savings: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "annual_essential_expenses": f"{self.annual_essential_expenses:.2f}",
            "annual_discretionary_expenses": f"{self.annual_discretionary_expenses:.2f}",
            "annual_one_time_expenses": f"{self.annual_one_time_expenses:.2f}",
            "total_annual_expenses": f"{self.total_annual_expenses:.2f}",
            "monthly_average_expenses": f"{self.monthly_average_expenses:.2f}",
            "annual_net_take_home": f"{self.annual_net_take_home:.2f}",
            "annual_total_savings": f"{self.annual_total_savings:.2f}",
            "annual_cash_surplus": f"{self.annual_cash_surplus:.2f}",
            "monthly_cash_surplus": f"{self.monthly_cash_surplus:.2f}",
            "savings_rate_pct": f"{self.savings_rate_pct:.2f}",
            "expense_to_income_ratio_pct": f"{self.expense_to_income_ratio_pct:.2f}",
            "essential_to_income_ratio_pct": f"{self.essential_to_income_ratio_pct:.2f}",
            "is_negative_cash_flow": self.is_negative_cash_flow,
            "statutory_tax_deductions_from_expenses": f"{self.statutory_tax_deductions_from_expenses:.2f}",
            "statutory_80c_from_savings": f"{self.statutory_80c_from_savings:.2f}",
            "statutory_80ccd_from_savings": f"{self.statutory_80ccd_from_savings:.2f}",
        }


class ExpenseSavingsEngine:
    """
    Computes cash flow health and builds the strict boundary between Personal Expenses and Tax Deductions.
    """

    @classmethod
    def annualize_amount(cls, amount: Decimal, freq: ExpenseFrequency) -> Decimal:
        dec = to_decimal(amount)
        if freq == ExpenseFrequency.MONTHLY:
            return quantize_currency(dec * Decimal("12"))
        elif freq == ExpenseFrequency.QUARTERLY:
            return quantize_currency(dec * Decimal("4"))
        elif freq == ExpenseFrequency.SEMI_ANNUAL:
            return quantize_currency(dec * Decimal("2"))
        elif freq in (ExpenseFrequency.ANNUAL, ExpenseFrequency.ONE_TIME):
            return quantize_currency(dec)
        return quantize_currency(dec)

    @classmethod
    def evaluate(
        cls,
        net_take_home_annual: Decimal,
        expenses: list[ExpenseItemInput],
        savings: list[SavingsItemInput],
    ) -> NormalizedExpenseSummary:
        net_income = to_decimal(net_take_home_annual)
        if net_income < Decimal("0"):
            raise InvalidSalaryInputError("Net take home salary cannot be negative.")

        essential = Decimal("0.00")
        discretionary = Decimal("0.00")
        one_time = Decimal("0.00")
        statutory_deductions_from_exp = Decimal("0.00")

        for exp in expenses:
            ann_amt = cls.annualize_amount(exp.amount, exp.frequency)
            if exp.nature == ExpenseNature.ESSENTIAL:
                essential += ann_amt
            elif exp.nature == ExpenseNature.DISCRETIONARY:
                discretionary += ann_amt
            elif exp.nature == ExpenseNature.ONE_TIME:
                one_time += ann_amt

            # Invariant check: Expense != Tax Deduction unless backed by a verified section
            if exp.is_statutory_deduction_claim and exp.statutory_section:
                statutory_deductions_from_exp += ann_amt

        total_expenses = essential + discretionary + one_time
        monthly_avg_exp = quantize_currency(total_expenses / Decimal("12"))

        # Process savings
        total_savings = Decimal("0.00")
        claim_80c = Decimal("0.00")
        claim_80ccd = Decimal("0.00")

        for sav in savings:
            ann_sav = cls.annualize_amount(sav.amount, sav.frequency)
            total_savings += ann_sav
            if sav.qualifies_section_80c:
                claim_80c += ann_sav
            if sav.qualifies_section_80ccd_1b:
                claim_80ccd += ann_sav

        # Cap standard section limits for verified bridges
        claim_80c = min(claim_80c, Decimal("150000.00"))
        claim_80ccd = min(claim_80ccd, Decimal("50000.00"))

        cash_surplus = net_income - (total_expenses + total_savings)
        monthly_surplus = quantize_currency(cash_surplus / Decimal("12"))
        is_negative = cash_surplus < Decimal("0.00")

        # Ratios
        savings_rate = Decimal("0.00")
        expense_ratio = Decimal("0.00")
        essential_ratio = Decimal("0.00")

        if net_income > Decimal("0.00"):
            savings_rate = quantize_currency((total_savings / net_income) * Decimal("100"))
            expense_ratio = quantize_currency((total_expenses / net_income) * Decimal("100"))
            essential_ratio = quantize_currency((essential / net_income) * Decimal("100"))

        return NormalizedExpenseSummary(
            annual_essential_expenses=quantize_currency(essential),
            annual_discretionary_expenses=quantize_currency(discretionary),
            annual_one_time_expenses=quantize_currency(one_time),
            total_annual_expenses=quantize_currency(total_expenses),
            monthly_average_expenses=monthly_avg_exp,
            annual_net_take_home=quantize_currency(net_income),
            annual_total_savings=quantize_currency(total_savings),
            annual_cash_surplus=quantize_currency(cash_surplus),
            monthly_cash_surplus=monthly_surplus,
            savings_rate_pct=savings_rate,
            expense_to_income_ratio_pct=expense_ratio,
            essential_to_income_ratio_pct=essential_ratio,
            is_negative_cash_flow=is_negative,
            statutory_tax_deductions_from_expenses=quantize_currency(statutory_deductions_from_exp),
            statutory_80c_from_savings=quantize_currency(claim_80c),
            statutory_80ccd_from_savings=quantize_currency(claim_80ccd),
        )
