import hashlib
import json
from decimal import Decimal
from typing import Any


class DecimalJsonEncoder(json.JSONEncoder):
    """JSON Encoder ensuring Decimal is formatted with fixed standard string representation."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return f"{obj:.4f}" if obj.as_tuple().exponent < -2 else f"{obj:.2f}"
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


def canonical_json_dumps(data: Any) -> str:
    """Serialize dictionary or object to sorted, UTF-8 canonical JSON string."""
    return json.dumps(
        data,
        cls=DecimalJsonEncoder,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def compute_sha256_hash(data: Any) -> str:
    """Compute SHA-256 hex digest of canonical JSON serialized data."""
    if isinstance(data, str):
        payload = data.encode("utf-8")
    else:
        payload = canonical_json_dumps(data).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
