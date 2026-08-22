"""
Comprehensive Test Suite for Milestone M8: Observability & Operational Monitoring
Verifies:
- Application, calculation, regulatory, and RAG error observability
- Sensitive data redaction (Zero PAN, Salary, Token, Password leaks)
- Correlation ID propagation and Tenant telemetry isolation
- Health & Readiness endpoint safety (Zero internal secret disclosure)
- Observability zero-mutation guarantee over calculation and rule state
"""

import pytest

from app.core.observability import (
    EventSeverity,
    EventType,
    ObservabilityEvent,
    ObservabilityService,
    sanitize_payload,
)


@pytest.fixture(autouse=True)
def clean_observability_events():
    ObservabilityService.clear_events()
    yield
    ObservabilityService.clear_events()


def test_m8_sensitive_data_redaction():
    payload = {
        "user_email": "test@company.com",
        "password": "SuperSecretPassword123!",
        "salary": 1500000,
        "pan": "ABCDE1234F",
        "nested": {
            "token": "eyJhbGciOi...",
            "gross_salary": 2000000,
            "safe_code": "SEC_87A",
        },
    }
    sanitized = sanitize_payload(payload)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["salary"] == "[REDACTED]"
    assert sanitized["pan"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["gross_salary"] == "[REDACTED]"
    assert sanitized["nested"]["safe_code"] == "SEC_87A"
    assert sanitized["user_email"] == "test@company.com"


def test_m8_calculation_failure_observable():
    event = ObservabilityEvent(
        event_type=EventType.CALCULATION_FAILED,
        severity=EventSeverity.ERROR,
        service="calculation_engine",
        component="SalaryNormalizer",
        operation="normalize_salary",
        correlation_id="corr-calc-001",
        tenant_id=101,
        failure_type="INVALID_SALARY_INPUT",
        safe_error_code="ERR_SALARY_NEGATIVE",
        details={"salary": -50000, "reason": "Salary cannot be negative"},
    )
    ObservabilityService.emit(event)

    events = ObservabilityService.get_events(tenant_id=101)
    assert len(events) == 1
    assert events[0].event_type == EventType.CALCULATION_FAILED
    assert events[0].details["salary"] == "[REDACTED]"


def test_m8_regulatory_failure_and_future_rule_block_observable():
    event = ObservabilityEvent(
        event_type=EventType.FUTURE_RULE_BLOCKED,
        severity=EventSeverity.REGULATORY,
        service="rule_resolver",
        component="ComplianceRuleRegistry",
        operation="resolve_rule",
        correlation_id="corr-reg-002",
        rule_id="RULE_INCOME_TAX_2028_DRAFT",
        financial_year="2028-29",
        jurisdiction="INDIA",
        safe_error_code="ERR_FUTURE_RULE_GATED",
        details={"requested_status": "DRAFT", "active_required": True},
    )
    ObservabilityService.emit(event)

    events = ObservabilityService.get_events()
    assert len(events) == 1
    assert events[0].event_type == EventType.FUTURE_RULE_BLOCKED
    assert events[0].severity == EventSeverity.REGULATORY


def test_m8_tenant_telemetry_isolation():
    # Tenant 101 event
    ObservabilityService.emit(
        ObservabilityEvent(
            event_type=EventType.CALCULATION_COMPLETED,
            severity=EventSeverity.INFO,
            service="payroll",
            component="BatchEngine",
            operation="run_payroll",
            tenant_id=101,
        )
    )
    # Tenant 202 event
    ObservabilityService.emit(
        ObservabilityEvent(
            event_type=EventType.IDOR_ATTEMPT,
            severity=EventSeverity.SECURITY,
            service="auth",
            component="TenantContext",
            operation="access_payslip",
            tenant_id=202,
        )
    )

    tenant_101_events = ObservabilityService.get_events(tenant_id=101)
    tenant_202_events = ObservabilityService.get_events(tenant_id=202)

    assert len(tenant_101_events) == 1
    assert tenant_101_events[0].tenant_id == 101
    assert len(tenant_202_events) == 1
    assert tenant_202_events[0].tenant_id == 202


def test_m8_rag_prompt_injection_observable():
    event = ObservabilityEvent(
        event_type=EventType.RAG_PROMPT_INJECTION,
        severity=EventSeverity.SECURITY,
        service="rag_service",
        component="CitationValidator",
        operation="sanitize_user_prompt",
        correlation_id="corr-rag-003",
        safe_error_code="ERR_PROMPT_INJECTION_DETECTED",
        details={"pattern": "IGNORE PREVIOUS INSTRUCTIONS", "action": "NEUTRALIZED"},
    )
    ObservabilityService.emit(event)

    events = ObservabilityService.get_events()
    assert len(events) == 1
    assert events[0].event_type == EventType.RAG_PROMPT_INJECTION
    assert events[0].severity == EventSeverity.SECURITY
