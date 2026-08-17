from decimal import Decimal

from app.engine.common.hashing import canonical_json_dumps, compute_sha256_hash
from app.engine.common.money import Money, quantize_currency, quantize_rate, to_decimal
from app.engine.common.rounding import RoundingPolicy


def test_to_decimal_and_quantization():
    assert to_decimal(100) == Decimal("100")
    assert to_decimal("1500.50") == Decimal("1500.50")
    assert to_decimal(None) == Decimal("0.00")
    # Float conversion without binary precision leak
    assert to_decimal(0.1) == Decimal("0.1")
    assert quantize_currency("123.456") == Decimal("123.46")
    assert quantize_currency("123.454") == Decimal("123.45")
    assert quantize_rate("0.12345") == Decimal("0.1235")


def test_money_class_arithmetic():
    m1 = Money("1000.50")
    m2 = Money("500.25")

    assert str(m1 + m2) == "1500.75"
    assert str(m1 - m2) == "500.25"
    assert str(m1 * 2) == "2001.00"
    assert str(m1 / 2) == "500.25"
    assert m1 > m2
    assert m2 < m1
    assert Money("100.00") == Decimal("100.00")


def test_rounding_policy_statutory():
    policy = RoundingPolicy()
    # Section 288A/288B round to nearest 10
    assert policy.round_to_nearest_ten("1234.40") == Decimal("1230.00")
    assert policy.round_to_nearest_ten("1235.00") == Decimal("1240.00")
    assert policy.round_to_nearest_ten("1236.80") == Decimal("1240.00")


def test_canonical_json_and_hashing():
    d1 = {"b": 2, "a": Decimal("100.50")}
    d2 = {"a": Decimal("100.50"), "b": 2}

    # Order-independent canonical json representation
    assert canonical_json_dumps(d1) == canonical_json_dumps(d2)
    assert compute_sha256_hash(d1) == compute_sha256_hash(d2)
    assert len(compute_sha256_hash(d1)) == 64
