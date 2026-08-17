from typing import Any

from app.engine.common.errors import SnapshotIntegrityError
from app.engine.common.hashing import compute_sha256_hash


class SnapshotService:
    """Manages canonical serialization, hashing, and immutability validation for calculation snapshots."""

    @staticmethod
    def build_snapshots(
        input_data: dict[str, Any],
        result_data: dict[str, Any],
        rule_set_data: dict[str, Any],
    ) -> dict[str, Any]:
        input_hash = compute_sha256_hash(input_data)
        result_hash = compute_sha256_hash(result_data)
        rule_set_hash = compute_sha256_hash(rule_set_data)

        return {
            "input_snapshot": input_data,
            "result_snapshot": result_data,
            "input_hash": input_hash,
            "result_hash": result_hash,
            "rule_set_hash": rule_set_hash,
        }

    @staticmethod
    def verify_snapshot_integrity(
        input_snapshot: dict[str, Any],
        result_snapshot: dict[str, Any],
        expected_input_hash: str,
        expected_result_hash: str,
    ) -> bool:
        actual_input_hash = compute_sha256_hash(input_snapshot)
        actual_result_hash = compute_sha256_hash(result_snapshot)

        if actual_input_hash != expected_input_hash:
            raise SnapshotIntegrityError("Input snapshot hash mismatch. Data integrity compromised.")

        if actual_result_hash != expected_result_hash:
            raise SnapshotIntegrityError("Result snapshot hash mismatch. Data integrity compromised.")

        return True
