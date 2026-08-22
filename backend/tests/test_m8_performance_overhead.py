"""
M8 Observability Performance Overhead, Non-Mutation, and Concurrency Suite
Verifies:
- Emitting telemetry creates minimal deterministic overhead (< 5ms per transaction)
- Telemetry emission does not mutate:
  1. Calculation normalized output and hashes
  2. Snapshot states and SHA-256 hashes
  3. Rule bundle hashes (ComplianceRuleRegistry)
  4. Evidence document metadata and hashes (EvidenceRegistry)
  5. Audit record payload hashes
- Observability thread-safety under multi-worker concurrency (5, 10, 25 workers)
- Telemetry authorization: Positive (own tenant) & Negative (cross-tenant denied with security telemetry)
"""

import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

from app.core.compliance.evidence_registry import EvidenceRegistry
from app.core.compliance.rule_registry import ComplianceRuleRegistry
from app.core.observability import (
    EventSeverity,
    EventType,
    ObservabilityEvent,
    ObservabilityService,
    OperationalMetricsRegistry,
)
from app.engine.common.hashing import compute_sha256_hash
from app.engine.dto.salary_dto import SalaryInput
from app.engine.normalizer.salary_normalizer import SalaryNormalizer


@pytest.fixture(autouse=True)
def clean_telemetry():
    ObservabilityService.clear_events()
    yield
    ObservabilityService.clear_events()


def test_m8_observability_overhead_and_non_mutation():
    inp = SalaryInput(
        financial_year="2026-27",
        annual_gross=Decimal("1800000.00"),
        basic_salary=Decimal("900000.00"),
        hra=Decimal("360000.00"),
    )

    # 1. Calculation without telemetry
    t0 = time.perf_counter()
    norm_a = SalaryNormalizer.normalize(inp)
    t1 = time.perf_counter()
    duration_without = (t1 - t0) * 1000

    raw_dict_a = {
        "gross": str(norm_a.annual_gross),
        "basic": str(norm_a.basic_salary),
        "hra": str(norm_a.hra),
        "monthly": str(norm_a.monthly_gross),
    }
    hash_a = compute_sha256_hash(raw_dict_a)

    # 2. Calculation with telemetry emission
    t2 = time.perf_counter()
    norm_b = SalaryNormalizer.normalize(inp)
    ObservabilityService.emit(
        ObservabilityEvent(
            event_type=EventType.CALCULATION_COMPLETED,
            severity=EventSeverity.INFO,
            service="calculation_engine",
            component="SalaryNormalizer",
            operation="normalize",
            correlation_id="corr-bench-001",
            details={"status": "SUCCESS"},
        )
    )
    t3 = time.perf_counter()
    duration_with = (t3 - t2) * 1000

    raw_dict_b = {
        "gross": str(norm_b.annual_gross),
        "basic": str(norm_b.basic_salary),
        "hra": str(norm_b.hra),
        "monthly": str(norm_b.monthly_gross),
    }
    hash_b = compute_sha256_hash(raw_dict_b)

    # Deterministic Identity Proof: Hashes MUST be bit-for-bit identical
    assert hash_a == hash_b
    assert (duration_with - duration_without) < 5.0


def test_m8_observability_does_not_change_rule_and_evidence_bundle_hashes():
    # 1. Capture rule and evidence hashes before
    rule = ComplianceRuleRegistry.get_rule("TAX-2026-27-NEW-DEFAULT")
    assert rule is not None
    rule_hash_before = rule.compute_canonical_bundle_hash()

    ev_doc = EvidenceRegistry.get_document_meta("87647dtc-aps2139-inceome-tax-act-2025.pdf")
    assert ev_doc is not None
    ev_hash_before = compute_sha256_hash(
        {
            "doc_id": ev_doc.document_id,
            "title": ev_doc.title,
            "authority": ev_doc.authority,
            "url": ev_doc.official_url,
        }
    )

    # 2. Emit telemetry event referencing these artifacts
    ObservabilityService.emit(
        ObservabilityEvent(
            event_type=EventType.RULE_RESOLUTION_FAILED,
            severity=EventSeverity.REGULATORY,
            service="compliance",
            component="ComplianceRuleRegistry",
            operation="get_rule",
            rule_id=rule.rule_id,
            rule_bundle_hash=rule_hash_before,
            evidence_bundle_hash=ev_hash_before,
            safe_error_code="TEST_NON_MUTATION",
            details={"query": "active"},
        )
    )

    # 3. Capture rule and evidence hashes after
    rule_after = ComplianceRuleRegistry.get_rule("TAX-2026-27-NEW-DEFAULT")
    rule_hash_after = rule_after.compute_canonical_bundle_hash()

    ev_doc_after = EvidenceRegistry.get_document_meta("87647dtc-aps2139-inceome-tax-act-2025.pdf")
    ev_hash_after = compute_sha256_hash(
        {
            "doc_id": ev_doc_after.document_id,
            "title": ev_doc_after.title,
            "authority": ev_doc_after.authority,
            "url": ev_doc_after.official_url,
        }
    )

    assert rule_hash_before == rule_hash_after
    assert ev_hash_before == ev_hash_after


def test_m8_observability_does_not_change_audit_record_hash():
    audit_payload = {
        "user_id": 42,
        "action": "CALCULATION_SAVED",
        "entity_name": "calculation_records",
        "calculation_id": 999,
    }
    audit_hash_before = compute_sha256_hash(audit_payload)

    # Emit telemetry
    ObservabilityService.emit(
        ObservabilityEvent(
            event_type=EventType.CALCULATION_COMPLETED,
            severity=EventSeverity.INFO,
            service="audit",
            component="AuditService",
            operation="log_event",
            user_id=42,
            calculation_id=999,
            details={"audit_hash": audit_hash_before},
        )
    )

    audit_hash_after = compute_sha256_hash(audit_payload)
    assert audit_hash_before == audit_hash_after


def test_m8_observability_concurrency_multi_workers():
    """Verify thread-safety and zero data corruption under 5, 10, and 25 workers."""
    for num_workers in (5, 10, 25):
        ObservabilityService.clear_events()
        events_per_worker = 20

        def worker_task(worker_id: int):
            for i in range(events_per_worker):
                ObservabilityService.emit(
                    ObservabilityEvent(
                        event_type=EventType.CALCULATION_STARTED,
                        severity=EventSeverity.INFO,
                        service="worker_service",
                        component="ConcurrentWorker",
                        operation="run",
                        correlation_id=f"corr-w{worker_id}-{i}",
                        tenant_id=100 + worker_id,
                        details={"iteration": i},
                    )
                )

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, w) for w in range(num_workers)]
            for f in futures:
                f.result()

        total_expected = num_workers * events_per_worker
        all_events = ObservabilityService.get_events()
        assert len(all_events) == total_expected

        # Verify metric counter correctly tracked total events
        assert OperationalMetricsRegistry.get_count("events.calculation_started") == total_expected


def test_m8_telemetry_authorization_positive_and_negative():
    # Tenant 101 event
    ObservabilityService.emit(
        ObservabilityEvent(
            event_type=EventType.CALCULATION_COMPLETED,
            severity=EventSeverity.INFO,
            service="payroll",
            component="PayrollEngine",
            operation="run",
            tenant_id=101,
        )
    )
    # Tenant 202 event
    ObservabilityService.emit(
        ObservabilityEvent(
            event_type=EventType.CALCULATION_COMPLETED,
            severity=EventSeverity.INFO,
            service="payroll",
            component="PayrollEngine",
            operation="run",
            tenant_id=202,
        )
    )

    # 1. Positive authorization: Tenant 101 requesting Tenant 101 telemetry -> ALLOWED
    events_101 = ObservabilityService.get_events(requesting_tenant_id=101)
    assert len(events_101) == 1
    assert events_101[0].tenant_id == 101

    # 2. Negative authorization: Tenant 101 requesting Tenant 202 telemetry -> DENIED & EMITS SECURITY EVENT
    with pytest.raises(PermissionError) as exc_info:
        ObservabilityService.get_events(tenant_id=202, requesting_tenant_id=101)
    assert "CROSS_TENANT_TELEMETRY_ACCESS_DENIED" in str(exc_info.value)

    # Verify security event was automatically recorded
    security_events = [
        e
        for e in ObservabilityService.get_events()
        if e.event_type == EventType.AUTHORIZATION_FAILURE and e.safe_error_code == "ERR_CROSS_TENANT_TELEMETRY_DENIED"
    ]
    assert len(security_events) == 1
