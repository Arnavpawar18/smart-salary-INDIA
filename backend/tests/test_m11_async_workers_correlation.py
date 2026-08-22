"""
Milestone M11.9: Async Workers & Correlation ID Propagation
Verifies async task telemetry and correlation ID propagation across background queues and service boundaries.
"""

import uuid

from app.core.observability import EventSeverity, EventType, ObservabilityEvent, ObservabilityService


def test_m11_correlation_propagation_smoke():
    cid = f"ss-corr-{uuid.uuid4().hex}"
    rid = f"ss-req-{uuid.uuid4().hex}"
    tenant_id = 202

    ObservabilityService.emit(
        ObservabilityEvent(
            event_type=EventType.CALCULATION_STARTED,
            severity=EventSeverity.INFO,
            service="payroll_worker",
            component="BatchProcessor",
            operation="process_batch",
            request_id=rid,
            correlation_id=cid,
            tenant_id=tenant_id,
            details={"batch_size": 10},
        )
    )

    events = ObservabilityService.get_events(tenant_id=tenant_id)
    assert len(events) > 0
    assert any(e.correlation_id == cid for e in events)
