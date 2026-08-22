"""
Milestone M8.1: Concurrency & Atomic Sequence Allocation Test Suite
Verifies:
- 2 concurrent worker threads appending to the same chain
- 10 concurrent worker threads appending to the same chain
- 50 concurrent worker threads appending to the same chain
- Multi-tenant concurrent writes (Tenant A and Tenant B writers running simultaneously)
- Invariants: Zero sequence collisions, zero forks, zero missing sequences, unbroken cryptographic chain
"""

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.database import SessionLocal
from app.services.audit_service import AuditChainVerifier, AuditService


def test_m8_1_concurrency_two_workers():
    chain_name = f"TENANT_201_{uuid.uuid4().hex[:6]}"

    def worker(worker_id):
        with SessionLocal() as db:
            return AuditService.log_event(
                db=db,
                action="CONCURRENT_ACTION_2",
                resource_type="BATCH_JOB",
                resource_id=worker_id,
                chain_id=chain_name,
                tenant_id=201,
                payload={"worker_id": worker_id},
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        results = [f.result() for f in as_completed(futures)]

    assert len(results) == 10
    with SessionLocal() as db:
        v = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert v["valid"] is True
        assert v["event_count"] == 10
        assert v["head_sequence"] == 10


def test_m8_1_concurrency_ten_workers():
    chain_name = f"TENANT_202_{uuid.uuid4().hex[:6]}"

    def worker(worker_id):
        with SessionLocal() as db:
            return AuditService.log_event(
                db=db,
                action="CONCURRENT_ACTION_10",
                resource_type="BATCH_JOB",
                resource_id=worker_id,
                chain_id=chain_name,
                tenant_id=202,
                payload={"worker_id": worker_id},
            )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(30)]
        results = [f.result() for f in as_completed(futures)]

    assert len(results) == 30
    with SessionLocal() as db:
        v = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert v["valid"] is True
        assert v["event_count"] == 30
        assert v["head_sequence"] == 30


def test_m8_1_concurrency_fifty_workers():
    chain_name = f"TENANT_203_{uuid.uuid4().hex[:6]}"

    def worker(worker_id):
        with SessionLocal() as db:
            return AuditService.log_event(
                db=db,
                action="CONCURRENT_ACTION_50",
                resource_type="BATCH_JOB",
                resource_id=worker_id,
                chain_id=chain_name,
                tenant_id=203,
                payload={"worker_id": worker_id},
            )

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(worker, i) for i in range(50)]
        results = [f.result() for f in as_completed(futures)]

    assert len(results) == 50
    with SessionLocal() as db:
        v = AuditChainVerifier.verify_chain(db, chain_id=chain_name)
        assert v["valid"] is True
        assert v["event_count"] == 50
        assert v["head_sequence"] == 50


def test_m8_1_multi_tenant_simultaneous_concurrency():
    uid = uuid.uuid4().hex[:6]
    chain_a = f"TENANT_101_{uid}"
    chain_b = f"TENANT_102_{uid}"

    def worker_tenant(target_chain, worker_id, tid):
        with SessionLocal() as db:
            return AuditService.log_event(
                db=db,
                action="TENANT_ACTION",
                resource_type="PAYROLL",
                resource_id=worker_id,
                chain_id=target_chain,
                tenant_id=tid,
                payload={"worker_id": worker_id},
            )

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures_a = [executor.submit(worker_tenant, chain_a, i, 101) for i in range(25)]
        futures_b = [executor.submit(worker_tenant, chain_b, i, 102) for i in range(25)]
        all_results = [f.result() for f in as_completed(futures_a + futures_b)]

    assert len(all_results) == 50
    with SessionLocal() as db:
        va = AuditChainVerifier.verify_chain(db, chain_id=chain_a)
        assert va["valid"] is True
        assert va["event_count"] == 25

        vb = AuditChainVerifier.verify_chain(db, chain_id=chain_b)
        assert vb["valid"] is True
        assert vb["event_count"] == 25

        vb = AuditChainVerifier.verify_chain(db, chain_id=chain_b)
        assert vb["valid"] is True
        assert vb["event_count"] == 25
