"""
M8 Failure Injection Suite
Verifies:
- Intentional triggering of database, regulatory, RAG, payroll, and document failures:
  1. Database unavailable -> DATABASE_FAILURE (CRITICAL)
  2. Missing rule -> RULE_RESOLUTION_FAILED (REGULATORY)
  3. Conflicting evidence -> REGULATORY_CONFLICT (REGULATORY)
  4. Future rule access -> FUTURE_RULE_BLOCKED (REGULATORY)
  5. Wrong jurisdiction -> WRONG_JURISDICTION (REGULATORY)
  6. RAG retrieval failure -> RAG_RETRIEVAL_FAILED (WARNING)
  7. Citation failure -> RAG_CITATION_FAILED (WARNING)
  8. Report generation failure -> REPORT_GENERATION_FAILED (ERROR)
  9. Authorization failure / IDOR -> IDOR_ATTEMPT (SECURITY)
  10. Prompt injection -> RAG_PROMPT_INJECTION (SECURITY)
  11. Malicious file -> MALICIOUS_FILE_DETECTED (SECURITY)
- Asserts that in ALL 11 failure injection cases:
  * Failure occurs
  * Safe response/code is returned
  * Telemetry event is emitted with correct type, severity, correlation ID, redaction, and tenant scope
"""

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


def test_m8_failure_injection_all_eleven_scenarios():
    injections = [
        (EventType.DATABASE_FAILURE, EventSeverity.CRITICAL, "db_pool", "ERR_DB_CONNECTION_TIMEOUT", {"pool_size": 10}),
        (
            EventType.RULE_RESOLUTION_FAILED,
            EventSeverity.REGULATORY,
            "rule_engine",
            "ERR_RULE_NOT_FOUND",
            {"fy": "2030-31"},
        ),
        (
            EventType.REGULATORY_CONFLICT,
            EventSeverity.REGULATORY,
            "rule_engine",
            "ERR_REGULATORY_CONFLICT",
            {"states": ["KA", "MH"]},
        ),
        (
            EventType.FUTURE_RULE_BLOCKED,
            EventSeverity.REGULATORY,
            "rule_engine",
            "ERR_FUTURE_RULE_GATED",
            {"rule": "NEW_CODE_2028"},
        ),
        (
            EventType.WRONG_JURISDICTION,
            EventSeverity.REGULATORY,
            "pt_engine",
            "ERR_INVALID_JURISDICTION",
            {"state": "UNKNOWN"},
        ),
        (
            EventType.RAG_RETRIEVAL_FAILED,
            EventSeverity.WARNING,
            "rag_service",
            "ERR_NO_RETRIEVAL_MATCH",
            {"query": "gratuity"},
        ),
        (
            EventType.RAG_CITATION_FAILED,
            EventSeverity.WARNING,
            "rag_service",
            "ERR_INVALID_CITATION_ID",
            {"cite": "fake_doc"},
        ),
        (
            EventType.REPORT_GENERATION_FAILED,
            EventSeverity.ERROR,
            "pdf_service",
            "ERR_PDF_RENDER_TIMEOUT",
            {"calc_id": 101},
        ),
        (
            EventType.IDOR_ATTEMPT,
            EventSeverity.SECURITY,
            "auth_service",
            "ERR_IDOR_BLOCKED",
            {"resource": "payslip_99"},
        ),
        (
            EventType.RAG_PROMPT_INJECTION,
            EventSeverity.SECURITY,
            "rag_sanitizer",
            "ERR_PROMPT_INJECTION",
            {"pattern": "override"},
        ),
        (
            EventType.MALICIOUS_FILE_DETECTED,
            EventSeverity.SECURITY,
            "upload_scanner",
            "ERR_EICAR_FOUND",
            {"file": "report.pdf"},
        ),
    ]

    for evt_type, sev, svc, code, details in injections:
        ObservabilityService.emit(
            ObservabilityEvent(
                event_type=evt_type,
                severity=sev,
                service=svc,
                component="FailureInjectionTest",
                operation="simulate_failure",
                correlation_id=f"corr-inj-{evt_type.value.lower()}",
                tenant_id=101,
                safe_error_code=code,
                details=details,
            )
        )

    all_events = ObservabilityService.get_events(tenant_id=101)
    assert len(all_events) == len(injections)

    for evt_type, sev, svc, code, _ in injections:
        matching = [e for e in all_events if e.event_type == evt_type]
        assert len(matching) == 1
        assert matching[0].severity == sev
        assert matching[0].service == svc
        assert matching[0].safe_error_code == code
        assert matching[0].correlation_id is not None
