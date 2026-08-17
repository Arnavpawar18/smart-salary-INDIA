from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR, ROUND_CEILING
from enum import Enum
from typing import Union


class RoundingMode(str, Enum):
    HALF_UP = "HALF_UP"
    FLOOR = "FLOOR"
    CEILING = "CEILING"


class RoundingPolicy:
    """Configurable rounding policy for reproducible calculation traces."""

    POLICY_VERSION: str = "ROUND-1.0.0"

    def __init__(
        self,
        policy_version: str = "ROUND-1.0.0",
        currency_places: int = 2,
        rate_places: int = 4,
        intermediate_rounding: bool = False,
    ):
        self.policy_version = policy_version
        self.currency_places = currency_places
        self.rate_places = rate_places
        self.intermediate_rounding = intermediate_rounding
        self._currency_unit = Decimal(10) ** -currency_places
        self._rate_unit = Decimal(10) ** -rate_places

    def round_currency(
        self,
        value: Union[Decimal, int, float, str],
        mode: RoundingMode = RoundingMode.HALF_UP,
    ) -> Decimal:
        dec = Decimal(str(value)) if not isinstance(value, Decimal) else value
        if mode == RoundingMode.HALF_UP:
            return dec.quantize(self._currency_unit, rounding=ROUND_HALF_UP)
        elif mode == RoundingMode.FLOOR:
            return dec.quantize(self._currency_unit, rounding=ROUND_FLOOR)
        elif mode == RoundingMode.CEILING:
            return dec.quantize(self._currency_unit, rounding=ROUND_CEILING)
        return dec.quantize(self._currency_unit, rounding=ROUND_HALF_UP)

    def round_rate(self, value: Union[Decimal, int, float, str]) -> Decimal:
        dec = Decimal(str(value)) if not isinstance(value, Decimal) else value
        return dec.quantize(self._rate_unit, rounding=ROUND_HALF_UP)

    def round_to_nearest_ten(self, value: Union[Decimal, int, float, str]) -> Decimal:
        """Section 288A/288B statutory rounding to nearest 10 rupees."""
        dec = Decimal(str(value)) if not isinstance(value, Decimal) else value
        # Divide by 10, round half up, multiply by 10
        return (dec / Decimal("10")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal("10")


DEFAULT_ROUNDING_POLICY = RoundingPolicy()
