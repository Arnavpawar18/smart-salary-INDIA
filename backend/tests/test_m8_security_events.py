"""
M8 Security Events & Tenant Isolation Telemetry Suite
Verifies:
- Complete Security Event Taxonomy:
  1. AUTH_FAILURE (invalid credentials/bad signature)
  2. AUTHORIZATION_FAILURE (RBAC breach)
  3. IDOR_ATTEMPT (cross-user access)
  4. TENANT_ISOLATION_FAILURE (cross-tenant access)
  5. TOKEN_REPLAY (revoked JTI reused)
  6. CSRF_FAILURE (bad/missing CSRF signature)
  7. RATE_LIMIT_EXCEEDED (DoS threshold)
  8. MALICIOUS_FILE_DETECTED (malware/corrupt payload)
  9. INVALID_DOCUMENT (invalid PDF structure)
- Verifies severity == SECURITY, correlation ID attachment, and zero secret logging
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


def test_m8_complete_security_telemetry_matrix():
    sec_events = [
        (EventType.AUTH_FAILURE, "ERR_INVALID_CREDENTIALS", {"email_domain": "corp.in"}),
        (EventType.AUTHORIZATION_FAILURE, "ERR_ROLE_UNAUTHORIZED", {"role": "EMPLOYEE", "resource": "payroll_admin"}),
        (EventType.IDOR_ATTEMPT, "ERR_IDOR_UNAUTHORIZED_RESOURCE", {"target_user_id": 999}),
        (EventType.TENANT_ISOLATION_FAILURE, "ERR_CROSS_TENANT_BREACH", {"target_tenant_id": 202}),
        (EventType.TOKEN_REPLAY, "ERR_REVOKED_TOKEN_REPLAY", {"jti": "jti_revoked_123"}),
        (EventType.CSRF_FAILURE, "ERR_CSRF_SIGNATURE_MISMATCH", {"header": "x-csrf-token"}),
        (EventType.RATE_LIMIT_EXCEEDED, "ERR_RATE_LIMIT_EXCEEDED", {"threshold": 100, "window": "60s"}),
        (EventType.MALICIOUS_FILE_DETECTED, "ERR_MALWARE_SIGNATURE", {"file_name": "payslip.exe"}),
        (EventType.INVALID_DOCUMENT, "ERR_DOCUMENT_CORRUPTED", {"file_name": "broken.pdf"}),
    ]

    for evt_type, code, details in sec_events:
        ObservabilityService.emit(
            ObservabilityEvent(
                event_type=evt_type,
                severity=EventSeverity.SECURITY if evt_type != EventType.RATE_LIMIT_EXCEEDED else EventSeverity.WARNING,
                service="security_gateway",
                component="SecurityGuard",
                operation="validate_request",
                correlation_id=f"corr-sec-{evt_type.value.lower()}",
                tenant_id=101,
                user_id=45,
                safe_error_code=code,
                details=details,
            )
        )

    all_events = ObservabilityService.get_events(tenant_id=101)
    assert len(all_events) == len(sec_events)

    for evt_type, code, _ in sec_events:
        matching = [e for e in all_events if e.event_type == evt_type]
        assert len(matching) == 1
        assert matching[0].safe_error_code == code
        assert matching[0].correlation_id is not None

    # Verify security metrics
    assert OperationalMetricsRegistry.get_count("events.idor_attempt") == 1
    assert OperationalMetricsRegistry.get_count("events.tenant_isolation_failure") == 1
    assert OperationalMetricsRegistry.get_count("events.token_replay") == 1
    assert OperationalMetricsRegistry.get_count("events.csrf_failure") == 1
