from decimal import Decimal
from typing import Any


def format_inr(value: Any, include_paise: bool = False) -> str:
    """
    Authoritatively formats a number or Decimal according to the Indian numbering system.
    Examples:
    1000 => '₹1,000'
    1250000 => '₹12,50,000'
    10000000 => '₹1,00,00,000'
    -50000 => '-₹50,000'
    1250.50 with include_paise=True => '₹1,250.50'
    """
    if value is None:
        return "₹0"

    try:
        dec = Decimal(str(value))
    except Exception:
        return f"₹{value}"

    is_negative = dec < 0
    dec = abs(dec)

    # Separate integer and fractional part
    int_part = int(dec)
    paise_part = int(round((dec - int_part) * 100))

    s = str(int_part)
    if len(s) <= 3:
        formatted_int = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted_int = ",".join(groups) + "," + last3

    prefix = "-₹" if is_negative else "₹"

    if include_paise and (paise_part > 0 or "." in str(value)):
        return f"{prefix}{formatted_int}.{paise_part:02d}"
    return f"{prefix}{formatted_int}"
