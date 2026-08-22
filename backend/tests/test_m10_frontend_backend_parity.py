"""
Milestone M10.13: Frontend-to-Backend Parity
Validates that string currency formatting and rounding preserves exact backend Decimal precision.
"""

from decimal import Decimal

from app.presentation.money import format_inr


def test_m10_frontend_backend_inr_formatting_parity():
    val = Decimal("1575000.00")
    formatted = format_inr(val)
    assert formatted == "₹15,75,000"

    with_paise = format_inr(Decimal("1575000.50"), include_paise=True)
    assert with_paise == "₹15,75,000.50"
