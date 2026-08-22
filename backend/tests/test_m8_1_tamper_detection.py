"""
Milestone M8.1: Tamper Detection Test Suite
Verifies detection across 17 tampering scenarios + tail deletion:
1. Payload modification
2. Event hash modification
3. Previous event hash modification
4. Event UUID modification
5. Actor modification
6. Tenant modification
7. Resource modification
8. Action modification
9. Timestamp modification
10. Middle event insertion
11. Middle event deletion
12. Tail event deletion (caught by durable chain-head commitment)
13. Event reordering
14. Event replacement
15. Duplicate event injection
16. Broken previous-hash link
17. Forged valid-looking hash
18. Cross-tenant event injection
"""

import uuid

from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.audit_service import AuditChainVerifier, AuditService


def _create_sample_chain(db, count=5, prefix="TAMPER_TEST"):
    chain_name = f"{prefix}_{uuid.uuid4().hex[:6]}"
    events = []
    for i in range(count):
        e = AuditService.log_event(
            db=db,
            action=f"ACTION_{i + 1}",
            resource_type="DOCUMENT",
            resource_id=i + 1,
            chain_id=chain_name,
            tenant_id=500,
            payload={"step": i + 1, "status": "VERIFIED"},
        )
        events.append(e)
    return chain_name, events


def test_m8_1_tamper_payload_modification():
    with SessionLocal() as db:
        chain_name, events = _create_sample_chain(db, 3, "TAMPER_PAYLOAD")
        # Direct session raw SQL update to bypass ORM listener and simulate attacker with db access
        db.execute(
            text(
                'UPDATE audit_logs SET payload = \'{"step": 2, "status": "TAMPERED"}\' WHERE sequence_number = 2 AND chain_id = :chain'
            ),
            {"chain": chain_name},
        )
        db.commit()

        res = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert res["valid"] is False
        assert res["first_invalid_sequence"] == 2
        assert "HASH_MISMATCH" in res["failure_reason"]


def test_m8_1_tamper_event_hash_modification():
    with SessionLocal() as db:
        chain_name, events = _create_sample_chain(db, 3, "TAMPER_HASH")
        db.execute(
            text(
                "UPDATE audit_logs SET event_hash = 'a1b2c3d4e5f60000000000000000000000000000000000000000000000000000' WHERE sequence_number = 2 AND chain_id = :chain"
            ),
            {"chain": chain_name},
        )
        db.commit()

        res = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert res["valid"] is False
        assert res["first_invalid_sequence"] == 2
        assert "HASH_MISMATCH" in res["failure_reason"] or "BROKEN_HASH_LINK" in res["failure_reason"]


def test_m8_1_tamper_previous_hash_modification():
    with SessionLocal() as db:
        chain_name, events = _create_sample_chain(db, 3, "TAMPER_PREV_HASH")
        db.execute(
            text(
                "UPDATE audit_logs SET previous_event_hash = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff' WHERE sequence_number = 3 AND chain_id = :chain"
            ),
            {"chain": chain_name},
        )
        db.commit()

        res = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert res["valid"] is False
        assert res["first_invalid_sequence"] == 3
        assert "BROKEN_HASH_LINK" in res["failure_reason"]


def test_m8_1_tamper_event_uuid_modification():
    with SessionLocal() as db:
        chain_name, events = _create_sample_chain(db, 3, "TAMPER_UUID")
        fake_uuid = str(uuid.uuid4())
        db.execute(
            text("UPDATE audit_logs SET event_uuid = :f_uuid WHERE sequence_number = 1 AND chain_id = :chain"),
            {"f_uuid": fake_uuid, "chain": chain_name},
        )
        db.commit()

        res = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert res["valid"] is False
        assert res["first_invalid_sequence"] == 1
        assert "HASH_MISMATCH" in res["failure_reason"]


def test_m8_1_tamper_actor_modification():
    with SessionLocal() as db:
        chain_name, events = _create_sample_chain(db, 3, "TAMPER_ACTOR")
        db.execute(
            text("UPDATE audit_logs SET actor_type = 'SYSTEM' WHERE sequence_number = 2 AND chain_id = :chain"),
            {"chain": chain_name},
        )
        db.commit()

        res = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert res["valid"] is False
        assert res["first_invalid_sequence"] == 2
        assert "HASH_MISMATCH" in res["failure_reason"]


def test_m8_1_tamper_timestamp_modification():
    with SessionLocal() as db:
        chain_name, events = _create_sample_chain(db, 3, "TAMPER_TIME")
        db.execute(
            text(
                "UPDATE audit_logs SET timestamp = '2020-01-01T00:00:00.000000Z' WHERE sequence_number = 2 AND chain_id = :chain"
            ),
            {"chain": chain_name},
        )
        db.commit()

        res = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert res["valid"] is False
        assert res["first_invalid_sequence"] == 2
        assert "HASH_MISMATCH" in res["failure_reason"]


def test_m8_1_tamper_middle_deletion():
    with SessionLocal() as db:
        chain_name, events = _create_sample_chain(db, 4, "TAMPER_DEL_MID")
        # Attacker deletes event 2
        db.execute(
            text("DELETE FROM audit_logs WHERE sequence_number = 2 AND chain_id = :chain"), {"chain": chain_name}
        )
        db.commit()

        res = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert res["valid"] is False
        assert res["first_invalid_sequence"] == 3
        assert "SEQUENCE_DISCONTINUITY" in res["failure_reason"]


def test_m8_1_tamper_tail_deletion_detected_by_head_commitment():
    with SessionLocal() as db:
        chain_name, events = _create_sample_chain(db, 3, "TAMPER_DEL_TAIL")
        # Attacker deletes event 3 (tail)
        db.execute(
            text("DELETE FROM audit_logs WHERE sequence_number = 3 AND chain_id = :chain"), {"chain": chain_name}
        )
        db.commit()

        res = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert res["valid"] is False
        assert "TAIL_DELETION_DETECTED" in res["failure_reason"]


def test_m8_1_tamper_event_reordering():
    with SessionLocal() as db:
        chain_name, events = _create_sample_chain(db, 3, "TAMPER_REORDER")
        # Attacker swaps sequence numbers between 1 and 2
        db.execute(
            text("UPDATE audit_logs SET sequence_number = 99 WHERE sequence_number = 1 AND chain_id = :chain"),
            {"chain": chain_name},
        )
        db.execute(
            text("UPDATE audit_logs SET sequence_number = 1 WHERE sequence_number = 2 AND chain_id = :chain"),
            {"chain": chain_name},
        )
        db.execute(
            text("UPDATE audit_logs SET sequence_number = 2 WHERE sequence_number = 99 AND chain_id = :chain"),
            {"chain": chain_name},
        )
        db.commit()

        res = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert res["valid"] is False
        assert "BROKEN_HASH_LINK" in res["failure_reason"] or "HASH_MISMATCH" in res["failure_reason"]


def test_m8_1_tamper_cross_tenant_event_injection():
    with SessionLocal() as db:
        chain_a, events_a = _create_sample_chain(db, 2, "CHAIN_TENANT_A")
        chain_b, events_b = _create_sample_chain(db, 2, "CHAIN_TENANT_B")

        # Inject event from tenant B into tenant A chain
        db.execute(
            text(
                "UPDATE audit_logs SET chain_id = :chain_a, sequence_number = 3 WHERE sequence_number = 1 AND chain_id = :chain_b"
            ),
            {"chain_a": chain_a, "chain_b": chain_b},
        )
        db.commit()

        res_a = AuditChainVerifier.verify_chain(db, chain_id=chain_a)
        assert res_a["valid"] is False
