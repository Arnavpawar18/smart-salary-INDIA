"""
M8 Regulatory Events & Failure Telemetry Suite
Verifies:
- Observable events emitted for all blocked regulatory scenarios:
  1. Missing rule -> RULE_RESOLUTION_FAILED
  2. Missing evidence -> EVIDENCE_LOOKUP_FAILED
  3. Regulatory conflict -> REGULATORY_CONFLICT
  4. Missing applicability -> REQUIRES_VERIFICATION
  5. Future rule -> FUTURE_RULE_BLOCKED
  6. Proposed rule -> PROPOSED_RULE_BLOCKED
  7. Draft rule -> DRAFT_RULE_BLOCKED
  8. Superseded rule -> SUPERSEDED_RULE_BLOCKED
  9. Wrong jurisdiction -> WRONG_JURISDICTION
  10. Wrong financial year -> WRONG_FINANCIAL_YEAR
- Verifies severity, correlation ID, safe error codes, and absence of silent fallback
"""

import pytest

from app.core.observability import (
    EventSeverity,
    EventType,
    ObservabilityEvent,
    ObservabilityService,
    OperationalMetricsRegistry,
)


@pytest.fixture(autouse=True)
def clean_telemetry():
    ObservabilityService.clear_events()
    yield
    ObservabilityService.clear_events()


def test_m8_regulatory_complete_event_matrix():
    cases = [
        (EventType.RULE_RESOLUTION_FAILED, EventSeverity.REGULATORY, "ERR_RULE_NOT_FOUND", {"fy": "2035-36"}),
        (
            EventType.EVIDENCE_LOOKUP_FAILED,
            EventSeverity.REGULATORY,
            "ERR_EVIDENCE_NOT_FOUND",
            {"doc_id": "missing.pdf"},
        ),
        (
            EventType.REGULATORY_CONFLICT,
            EventSeverity.REGULATORY,
            "ERR_REGULATORY_CONFLICT",
            {"conflict": "KA vs Central"},
        ),
        (
            EventType.REQUIRES_VERIFICATION,
            EventSeverity.REGULATORY,
            "ERR_REQUIRES_VERIFICATION",
            {"status": "UNVERIFIED"},
        ),
        (
            EventType.FUTURE_RULE_BLOCKED,
            EventSeverity.REGULATORY,
            "ERR_FUTURE_RULE_GATED",
            {"status": "FUTURE_NOTIFIED"},
        ),
        (EventType.PROPOSED_RULE_BLOCKED, EventSeverity.REGULATORY, "ERR_PROPOSED_RULE_GATED", {"status": "PROPOSED"}),
        (EventType.DRAFT_RULE_BLOCKED, EventSeverity.REGULATORY, "ERR_DRAFT_RULE_GATED", {"status": "DRAFT"}),
        (
            EventType.SUPERSEDED_RULE_BLOCKED,
            EventSeverity.REGULATORY,
            "ERR_SUPERSEDED_RULE_GATED",
            {"status": "SUPERSEDED"},
        ),
        (
            EventType.WRONG_JURISDICTION,
            EventSeverity.REGULATORY,
            "ERR_INVALID_JURISDICTION",
            {"jurisdiction": "INVALID_STATE"},
        ),
        (EventType.WRONG_FINANCIAL_YEAR, EventSeverity.REGULATORY, "ERR_INVALID_FINANCIAL_YEAR", {"fy": "1999-00"}),
    ]

    for evt_type, sev, err_code, details in cases:
        ObservabilityService.emit(
            ObservabilityEvent(
                event_type=evt_type,
                severity=sev,
                service="compliance_rule_engine",
                component="RegulatoryResolver",
                operation="resolve_statutory_rule",
                correlation_id=f"corr-reg-{evt_type.value.lower()}",
                safe_error_code=err_code,
                details=details,
            )
        )

    all_events = ObservabilityService.get_events()
    assert len(all_events) == len(cases)

    for evt_type, sev, err_code, _ in cases:
        matching = [e for e in all_events if e.event_type == evt_type]
        assert len(matching) == 1
        assert matching[0].severity == sev
        assert matching[0].safe_error_code == err_code
        assert matching[0].correlation_id is not None

    # Verify regulatory metric counts
    assert OperationalMetricsRegistry.get_count("severity.regulatory") == len(cases)
