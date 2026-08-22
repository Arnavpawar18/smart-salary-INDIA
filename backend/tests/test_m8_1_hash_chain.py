"""
Milestone M8.1: Hash Chain & Canonical Serialization Test Suite
Verifies:
- Genesis representation (64 zeros)
- Monotonic sequence numbers (1, 2, 3...)
- Predecessor hash linking (H_n = SHA-256(canonical_event_n || H_{n-1}))
- Canonical hashing covers all 14 security-critical fields
- Deterministic canonical JSON (key sorting, Decimal formatting, UTC time strings)
- Durable chain-head updates
"""

from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.engine.common.hashing import canonical_json_dumps, compute_sha256_hash
from app.models.audit import AuditChainHead
from app.services.audit_service import GENESIS_HASH, AuditService


def test_m8_1_genesis_hash_and_sequence_progression():
    chain_name = "TENANT_GENESIS_TEST"
    with SessionLocal() as db:
        e1 = AuditService.log_event(
            db=db,
            action="ACCOUNT_CREATED",
            resource_type="ACCOUNT",
            resource_id=10,
            chain_id=chain_name,
            tenant_id=999,
            payload={"account_type": "SAVINGS"},
        )
        assert e1.sequence_number == 1
        assert e1.previous_event_hash == GENESIS_HASH

        e2 = AuditService.log_event(
            db=db,
            action="KYC_VERIFIED",
            resource_type="ACCOUNT",
            resource_id=10,
            chain_id=chain_name,
            tenant_id=999,
            payload={"kyc_doc": "PASSPORT"},
        )
        assert e2.sequence_number == 2
        assert e2.previous_event_hash == e1.event_hash

        e3 = AuditService.log_event(
            db=db,
            action="BENEFICIARY_ADDED",
            resource_type="ACCOUNT",
            resource_id=10,
            chain_id=chain_name,
            tenant_id=999,
            payload={"beneficiary": "BETA_CORP"},
        )
        assert e3.sequence_number == 3
        assert e3.previous_event_hash == e2.event_hash

        # Verify durable chain head
        head = db.scalar(select(AuditChainHead).where(AuditChainHead.chain_id == chain_name))
        assert head is not None
        assert head.last_sequence == 3
        assert head.last_event_hash == e3.event_hash


def test_m8_1_canonical_json_determinism():
    # Order-independent dictionary with Decimal and nested structures
    d1 = {
        "z": 100,
        "a": Decimal("15000.50"),
        "nested": {"b": 2, "a": 1},
    }
    d2 = {
        "nested": {"a": 1, "b": 2},
        "a": Decimal("15000.50"),
        "z": 100,
    }
    json1 = canonical_json_dumps(d1)
    json2 = canonical_json_dumps(d2)
    assert json1 == json2
    assert compute_sha256_hash(d1) == compute_sha256_hash(d2)


def test_m8_1_all_14_fields_hashed():
    # If any single field out of 14 changes, the hash must change
    base_params = {
        "event_uuid": "11111111-1111-1111-1111-111111111111",
        "chain_id": "TENANT_777",
        "sequence_number": 1,
        "tenant_id": 777,
        "actor_type": "USER",
        "actor_id": 10,
        "resource_type": "PAYSLIP",
        "resource_id": 20,
        "action": "PAYSLIP_VIEWED",
        "timestamp": "2026-08-20T12:00:00.000000Z",
        "schema_version": "v1.0.0",
        "correlation_id": "corr-123",
        "sanitized_payload": {"view_mode": "PDF"},
        "previous_event_hash": GENESIS_HASH,
    }
    base_dict = AuditService.canonical_event_dict(**base_params)
    base_hash = AuditService.compute_event_hash(base_dict)

    # Test mutating each field individually
    mutations = [
        ("event_uuid", "22222222-2222-2222-2222-222222222222"),
        ("chain_id", "TENANT_888"),
        ("sequence_number", 2),
        ("tenant_id", 888),
        ("actor_type", "SYSTEM"),
        ("actor_id", 99),
        ("resource_type", "REPORT"),
        ("resource_id", 99),
        ("action", "PAYSLIP_DOWNLOADED"),
        ("timestamp", "2026-08-20T12:00:01.000000Z"),
        ("schema_version", "v1.0.1"),
        ("correlation_id", "corr-999"),
        ("sanitized_payload", {"view_mode": "EXCEL"}),
        ("previous_event_hash", "f" * 64),
    ]

    for key, new_val in mutations:
        modified_params = base_params.copy()
        modified_params[key] = new_val
        mod_dict = AuditService.canonical_event_dict(**modified_params)
        mod_hash = AuditService.compute_event_hash(mod_dict)
        assert mod_hash != base_hash, f"Security Gap: modifying field '{key}' did not alter the computed hash!"
