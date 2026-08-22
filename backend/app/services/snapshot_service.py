from typing import Any

from app.engine.common.errors import SnapshotIntegrityError
from app.engine.common.hashing import compute_sha256_hash
from app.engine.dto.snapshot_contract_v1 import CalculationSnapshotV1


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

    @staticmethod
    def apply_calculation_correction(
        parent_snapshot: CalculationSnapshotV1,
        new_inputs: dict[str, Any],
        new_outputs: dict[str, Any],
        new_trace: dict[str, Any],
        correction_reason: str,
        decisions: list | None = None,
    ) -> tuple[CalculationSnapshotV1, str]:
        """
        Creates an immutable correction snapshot linking to the parent snapshot.
        Guarantees the parent snapshot remains unaltered in-place.
        """
        parent_hash_before = parent_snapshot.snapshot_hash

        # Verify parent snapshot integrity
        recomputed_parent_hash = compute_sha256_hash(
            {
                "inputs": parent_snapshot.inputs_payload,
                "outputs": parent_snapshot.outputs_payload,
                "rule_bundle_hash": parent_snapshot.rule_bundle_hash,
                "evidence_bundle_hash": parent_snapshot.evidence_bundle_hash,
                "engine_version": parent_snapshot.engine_version,
                "schema_version": parent_snapshot.schema_version,
            }
        )
        if recomputed_parent_hash != parent_snapshot.snapshot_hash:
            raise SnapshotIntegrityError(
                "Cannot apply correction: Parent snapshot hash verification failed (Corrupted Parent)."
            )

        new_snapshot = CalculationSnapshotV1.create(
            user_id=parent_snapshot.user_id,
            engine_version=parent_snapshot.engine_version,
            rule_bundle_id=parent_snapshot.rule_bundle_id,
            rule_bundle_hash=parent_snapshot.rule_bundle_hash,
            evidence_bundle_id=parent_snapshot.evidence_bundle_id,
            evidence_bundle_hash=parent_snapshot.evidence_bundle_hash,
            inputs=new_inputs,
            outputs=new_outputs,
            trace=new_trace,
            decisions=decisions or [],
            parent_snapshot_id=parent_snapshot.snapshot_id,
            correction_reason=correction_reason,
        )

        # Invariant check: parent snapshot hash must be 100% identical
        assert parent_snapshot.snapshot_hash == parent_hash_before, (
            "CRITICAL INVARIANT VIOLATION: Parent snapshot mutated during correction!"
        )

        return new_snapshot, parent_hash_before
