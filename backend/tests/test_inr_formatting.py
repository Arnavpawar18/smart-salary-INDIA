from decimal import Decimal

from app.presentation.money import format_inr


def test_inr_formatting_lakhs_crores_paise():
    assert format_inr(Decimal("1000")) == "₹1,000"
    assert format_inr(Decimal("12500")) == "₹12,500"
    assert format_inr(Decimal("120000")) == "₹1,20,000"
    assert format_inr(Decimal("1250000")) == "₹12,50,000"
    assert format_inr(Decimal("10000000")) == "₹1,00,00,000"
    assert format_inr(Decimal("-50000")) == "-₹50,000"
    assert format_inr(Decimal("1250.50"), include_paise=True) == "₹1,250.50"
    assert format_inr(0) == "₹0"
