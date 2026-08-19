"""
Tests for Expense & Savings Financial Health Engine (M2.4)
Validates Cash Surplus, Savings Rate, Essential vs Discretionary splits, and Statutory Bridges.
"""
from decimal import Decimal
import pytest

from app.engine.analytics.expense_savings_engine import (
    ExpenseFrequency,
    ExpenseItemInput,
    ExpenseNature,
    ExpenseSavingsEngine,
    SavingsItemInput,
    SavingsVehicle,
)


def test_expense_savings_engine_surplus_and_ratios():
    # Net Take Home: ₹1,00,000 / month = ₹12,00,000 / year
    annual_take_home = Decimal("1200000.00")

    expenses = [
        ExpenseItemInput(
            category="Rent",
            amount=Decimal("25000.00"),
            frequency=ExpenseFrequency.MONTHLY,
            nature=ExpenseNature.ESSENTIAL,
        ),
        ExpenseItemInput(
            category="Groceries & Utilities",
            amount=Decimal("15000.00"),
            frequency=ExpenseFrequency.MONTHLY,
            nature=ExpenseNature.ESSENTIAL,
        ),
        ExpenseItemInput(
            category="Dining & Subscriptions",
            amount=Decimal("10000.00"),
            frequency=ExpenseFrequency.MONTHLY,
            nature=ExpenseNature.DISCRETIONARY,
        ),
        ExpenseItemInput(
            category="Annual Vacation",
            amount=Decimal("60000.00"),
            frequency=ExpenseFrequency.ANNUAL,
            nature=ExpenseNature.DISCRETIONARY,
        ),
    ]

    savings = [
        SavingsItemInput(
            vehicle=SavingsVehicle.PPF,
            amount=Decimal("12500.00"),
            frequency=ExpenseFrequency.MONTHLY,
            qualifies_section_80c=True,
        ),
        SavingsItemInput(
            vehicle=SavingsVehicle.NPS,
            amount=Decimal("4166.67"),
            frequency=ExpenseFrequency.MONTHLY,
            qualifies_section_80ccd_1b=True,
        ),
        SavingsItemInput(
            vehicle=SavingsVehicle.MUTUAL_FUNDS,
            amount=Decimal("10000.00"),
            frequency=ExpenseFrequency.MONTHLY,
        ),
    ]

    summary = ExpenseSavingsEngine.evaluate(
        net_take_home_annual=annual_take_home,
        expenses=expenses,
        savings=savings,
    )

    # Assertions
    # Essential = (25k + 15k) * 12 = 4.8L
    assert summary.annual_essential_expenses == Decimal("480000.00")
    # Discretionary = (10k * 12) + 60k = 1.8L
    assert summary.annual_discretionary_expenses == Decimal("180000.00")
    # Total Expenses = 6.6L
    assert summary.total_annual_expenses == Decimal("660000.00")

    # Savings = (12.5k * 12 = 1.5L PPF) + (50k NPS) + (1.2L MF) = 3.2L
    assert summary.statutory_80c_from_savings == Decimal("150000.00")
    assert summary.statutory_80ccd_from_savings == Decimal("50000.00")
    assert summary.annual_total_savings == Decimal("320000.04")

    # Cash Surplus = 12L - (6.6L + 3.2L) = 2.2L
    assert summary.annual_cash_surplus == Decimal("219999.96")
    assert summary.is_negative_cash_flow is False

    # Check Ratios
    # Savings Rate = 3.2L / 12L ≈ 26.67%
    assert summary.savings_rate_pct == Decimal("26.67")
    # Expense Ratio = 6.6L / 12L = 55.00%
    assert summary.expense_to_income_ratio_pct == Decimal("55.00")


def test_negative_cash_flow_detection():
    annual_take_home = Decimal("600000.00")  # 50k / month
    expenses = [
        ExpenseItemInput(
            category="High EMI",
            amount=Decimal("60000.00"),
            frequency=ExpenseFrequency.MONTHLY,
            nature=ExpenseNature.ESSENTIAL,
        )
    ]
    summary = ExpenseSavingsEngine.evaluate(
        net_take_home_annual=annual_take_home,
        expenses=expenses,
        savings=[],
    )
    # Total Expenses = 7.2L > 6L
    assert summary.is_negative_cash_flow is True
    assert summary.annual_cash_surplus < Decimal("0.00")
