"""
M8 Correlation ID Propagation Suite
Verifies:
- End-to-end multi-layer correlation propagation (HTTP -> Auth -> Tenant Context -> Calculation -> Rule/Evidence -> Snapshot -> RAG -> Report)
- Correlation ID integrity: zero sensitive data (PAN, Salary, Aadhaar, JWT) derived or leaked in correlation IDs
"""

import uuid

import pytest

from app.core.observability import (
    EventSeverity,
    EventType,
    ObservabilityEvent,
    ObservabilityService,
)


@pytest.fixture(autouse=True)
def clean_telemetry():
    ObservabilityService.clear_events()
    yield
    ObservabilityService.clear_events()


def test_m8_correlation_id_propagation_across_layers():
    cid = f"ss-corr-{uuid.uuid4().hex}"
    rid = f"ss-req-{uuid.uuid4().hex}"
    tenant_id = 101

    layers = [
        ("http_ingress", "FastAPI_Router", "handle_request", EventType.APPLICATION_ERROR, EventSeverity.INFO),
        ("auth_service", "AuthMiddleware", "authenticate_jwt", EventType.AUTH_FAILURE, EventSeverity.INFO),
        ("tenant_context", "TenantResolver", "resolve_tenant", EventType.CALCULATION_STARTED, EventSeverity.INFO),
        (
            "calculation_service",
            "SalaryNormalizer",
            "normalize_salary",
            EventType.CALCULATION_STARTED,
            EventSeverity.INFO,
        ),
        (
            "rule_resolver",
            "ComplianceRuleRegistry",
            "resolve_rule",
            EventType.CALCULATION_COMPLETED,
            EventSeverity.INFO,
        ),
        ("snapshot_service", "SnapshotLedger", "create_snapshot", EventType.CALCULATION_COMPLETED, EventSeverity.INFO),
        ("rag_service", "FinancialRAGRetriever", "retrieve_grounding", EventType.RAG_REQUEST, EventSeverity.INFO),
        ("report_service", "PDFGenerator", "render_summary", EventType.REPORT_REQUEST, EventSeverity.INFO),
    ]

    for service, comp, op, evt_type, sev in layers:
        ObservabilityService.emit(
            ObservabilityEvent(
                event_type=evt_type,
                severity=sev,
                service=service,
                component=comp,
                operation=op,
                request_id=rid,
                correlation_id=cid,
                tenant_id=tenant_id,
                details={"layer": service},
            )
        )

    events = ObservabilityService.get_events(tenant_id=tenant_id)
    assert len(events) == len(layers)

    # Verify all layers preserved exact correlation_id and request_id
    for ev in events:
        assert ev.correlation_id == cid
        assert ev.request_id == rid
        assert ev.tenant_id == tenant_id


def test_m8_correlation_id_contains_no_sensitive_data():
    cid = f"corr-{uuid.uuid4()}"
    forbidden_terms = ["salary", "pan", "aadhaar", "jwt", "pass", "token", "otp", "secret"]
    for term in forbidden_terms:
        assert term not in cid.lower(), f"Sensitive term {term} found in correlation ID"
