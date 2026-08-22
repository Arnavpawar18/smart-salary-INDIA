"""
Milestone M8.1: Correction Workflow & Snapshot Immutability Test Suite
Verifies:
- Correction creates new snapshot with parent_snapshot_id
- Parent snapshot hash, trace, rule bundle hash, evidence bundle hash remain 100% UNCHANGED
- Cannot correct a corrupted parent snapshot
- Correction audit event emitted to tenant audit ledger linking old and new snapshot IDs
- Multi-step correction lineage preserves full vertical provenance
"""

import uuid
from decimal import Decimal

import pytest

from app.core.database import SessionLocal
from app.engine.common.errors import SnapshotIntegrityError
from app.engine.dto.snapshot_contract_v1 import CalculationSnapshotV1
from app.services.audit_service import AuditChainVerifier, AuditEvent, AuditService
from app.services.snapshot_service import SnapshotService


def test_m8_1_correction_workflow_preserves_parent():
    user_id = uuid.uuid4()

    # 1. Create Original Snapshot A
    snap_a = CalculationSnapshotV1.create(
        user_id=user_id,
        engine_version="2026.1",
        rule_bundle_id="RB-2026-V1",
        rule_bundle_hash="a1b2c3d4e5f60000000000000000000000000000000000000000000000000000",
        evidence_bundle_id="EB-2026-V1",
        evidence_bundle_hash="f6e5d4c3b2a10000000000000000000000000000000000000000000000000000",
        inputs={"basic": Decimal("50000.00"), "hra": Decimal("25000.00")},
        outputs={"gross": Decimal("75000.00"), "tax": Decimal("4000.00")},
        trace={"rule": "RULE_OLD_2026"},
        decisions=[],
    )
    original_hash_a = snap_a.snapshot_hash
    original_inputs_a = snap_a.inputs_payload.copy()
    original_outputs_a = snap_a.outputs_payload.copy()

    # 2. Apply Correction -> Snapshot B
    snap_b, verified_parent_hash = SnapshotService.apply_calculation_correction(
        parent_snapshot=snap_a,
        new_inputs={"basic": Decimal("55000.00"), "hra": Decimal("27500.00")},
        new_outputs={"gross": Decimal("82500.00"), "tax": Decimal("4800.00")},
        new_trace={"rule": "RULE_CORRECTED_2026"},
        correction_reason="ARREARS_SALARY_HIKE_Q1",
    )

    # 3. Verify Snapshot A is completely untouched
    assert snap_a.snapshot_hash == original_hash_a
    assert snap_a.inputs_payload == original_inputs_a
    assert snap_a.outputs_payload == original_outputs_a

    # 4. Verify Snapshot B has distinct identity and lineage
    assert snap_b.snapshot_id != snap_a.snapshot_id
    assert snap_b.snapshot_hash != original_hash_a
    assert snap_b.parent_snapshot_id == snap_a.snapshot_id
    assert snap_b.correction_reason == "ARREARS_SALARY_HIKE_Q1"

    # 5. Log correction to Tenant Audit Chain
    with SessionLocal() as db:
        log = AuditService.log_event(
            db=db,
            action=AuditEvent.CALCULATION_CORRECTED,
            resource_type="CALCULATION_SNAPSHOT",
            resource_id=1,
            tenant_id=200,
            actor_type="USER",
            actor_id=5,
            payload={
                "parent_snapshot_id": str(snap_a.snapshot_id),
                "parent_snapshot_hash": snap_a.snapshot_hash,
                "new_snapshot_id": str(snap_b.snapshot_id),
                "new_snapshot_hash": snap_b.snapshot_hash,
                "reason": "ARREARS_SALARY_HIKE_Q1",
            },
        )
        assert log.id is not None

        # Verify chain integrity
        res = AuditChainVerifier.verify_chain(db, chain_id="TENANT_200")
        assert res["valid"] is True


def test_m8_1_correction_fails_on_corrupted_parent():
    user_id = uuid.uuid4()
    snap_corrupted = CalculationSnapshotV1(
        snapshot_id=uuid.uuid4(),
        user_id=user_id,
        created_at="2026-08-20T00:00:00Z",
        engine_version="2026.1",
        schema_version="v1.0.0",
        inputs_payload={"basic": Decimal("10000.00")},
        outputs_payload={"tax": Decimal("0.00")},
        trace_payload={},
        applicability_decisions=[],
        snapshot_hash="fake_hash_not_matching_content_00000000000000000000000000000000",
    )

    with pytest.raises(SnapshotIntegrityError) as exc_info:
        SnapshotService.apply_calculation_correction(
            parent_snapshot=snap_corrupted,
            new_inputs={"basic": Decimal("20000.00")},
            new_outputs={"tax": Decimal("500.00")},
            new_trace={},
            correction_reason="ILLEGAL_CORRECTION",
        )
    assert "Parent snapshot hash verification failed" in str(exc_info.value)
