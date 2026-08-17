from decimal import ROUND_HALF_UP, Decimal
from typing import Union

# Standard Precision
CURRENCY_PRECISION = Decimal("0.01")
RATE_PRECISION = Decimal("0.0001")


def to_decimal(val: int | float | str | Decimal | None, default: str = "0.00") -> Decimal:
    """Safely convert any numeric input or string representation to Decimal."""
    if val is None:
        return Decimal(default)
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, str)):
        return Decimal(str(val))
    if isinstance(val, float):
        # Convert float via string representation to avoid float binary representation artifacts
        return Decimal(str(val))
    return Decimal(default)


def quantize_currency(amount: Decimal | int | float | str) -> Decimal:
    """Quantize monetary amount to exactly 2 decimal places using ROUND_HALF_UP."""
    dec = to_decimal(amount)
    return dec.quantize(CURRENCY_PRECISION, rounding=ROUND_HALF_UP)


def quantize_rate(rate: Decimal | int | float | str) -> Decimal:
    """Quantize rate or percentage to exactly 4 decimal places using ROUND_HALF_UP."""
    dec = to_decimal(rate)
    return dec.quantize(RATE_PRECISION, rounding=ROUND_HALF_UP)


class Money:
    """Immutable monetary value wrapper with strict arithmetic and 2-decimal quantization."""

    __slots__ = ("_amount",)

    def __init__(self, amount: Union[Decimal, int, float, str, "Money"] = 0):
        if isinstance(amount, Money):
            self._amount = amount._amount
        else:
            self._amount = quantize_currency(amount)

    @property
    def amount(self) -> Decimal:
        return self._amount

    def __repr__(self) -> str:
        return f"Money('{self._amount:.2f}')"

    def __str__(self) -> str:
        return f"{self._amount:.2f}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self._amount == other._amount
        if isinstance(other, (int, float, str, Decimal)):
            return self._amount == quantize_currency(other)
        return False

    def __lt__(self, other: Union["Money", Decimal, int, str]) -> bool:
        if isinstance(other, Money):
            return self._amount < other._amount
        return self._amount < quantize_currency(other)

    def __le__(self, other: Union["Money", Decimal, int, str]) -> bool:
        if isinstance(other, Money):
            return self._amount <= other._amount
        return self._amount <= quantize_currency(other)

    def __gt__(self, other: Union["Money", Decimal, int, str]) -> bool:
        if isinstance(other, Money):
            return self._amount > other._amount
        return self._amount > quantize_currency(other)

    def __ge__(self, other: Union["Money", Decimal, int, str]) -> bool:
        if isinstance(other, Money):
            return self._amount >= other._amount
        return self._amount >= quantize_currency(other)

    def __add__(self, other: Union["Money", Decimal, int, str]) -> "Money":
        if isinstance(other, Money):
            return Money(self._amount + other._amount)
        return Money(self._amount + quantize_currency(other))

    def __radd__(self, other: Union["Money", Decimal, int, str]) -> "Money":
        return self.__add__(other)

    def __sub__(self, other: Union["Money", Decimal, int, str]) -> "Money":
        if isinstance(other, Money):
            return Money(self._amount - other._amount)
        return Money(self._amount - quantize_currency(other))

    def __rsub__(self, other: Union["Money", Decimal, int, str]) -> "Money":
        if isinstance(other, Money):
            return Money(other._amount - self._amount)
        return Money(quantize_currency(other) - self._amount)

    def __mul__(self, other: Decimal | int | float | str) -> "Money":
        rate = to_decimal(other)
        return Money(self._amount * rate)

    def __rmul__(self, other: Decimal | int | float | str) -> "Money":
        return self.__mul__(other)

    def __truediv__(self, other: Decimal | int | float | str) -> "Money":
        divisor = to_decimal(other)
        if divisor == Decimal("0"):
            raise ZeroDivisionError("Division by zero in Money")
        return Money(self._amount / divisor)

    def __neg__(self) -> "Money":
        return Money(-self._amount)

    def __abs__(self) -> "Money":
        return Money(abs(self._amount))
