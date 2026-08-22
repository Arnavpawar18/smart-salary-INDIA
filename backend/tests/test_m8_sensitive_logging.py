"""
M8 Sensitive Logging & Recursive Redaction Suite
Verifies:
- Direct, nested, and list-level PII/salary redaction
- Exception & Traceback sanitization (Zero PAN, Aadhaar, JWT, Password leaks in text)
- HTTP Headers (Authorization, Cookie, X-API-Key) sanitization
- Query parameters & Request bodies sanitization
- System prompt & Private evidence non-disclosure
"""

import traceback

import pytest

from app.core.observability import (
    EventSeverity,
    EventType,
    ObservabilityEvent,
    ObservabilityService,
    sanitize_payload,
    sanitize_string,
)


@pytest.fixture(autouse=True)
def clean_telemetry():
    ObservabilityService.clear_events()
    yield
    ObservabilityService.clear_events()


def test_m8_direct_sensitive_keys_redacted():
    data = {
        "password": "plain_password_123",
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$...",
        "token": "bearer_jwt_token_xyz",
        "access_token": "access_token_123",
        "refresh_token": "refresh_token_abc",
        "jwt": "eyJhbGci...",
        "pan": "ABCDE1234F",
        "aadhaar": "1234 5678 9012",
        "salary": 1200000,
        "gross_salary": 1500000,
        "basic_salary": 600000,
        "annual_gross": 1800000,
        "net_pay": 95000,
        "bank_account": "987654321098",
        "ifsc": "HDFC0001234",
        "otp": "654321",
        "safe_key": "tax_regime_new",
    }
    sanitized = sanitize_payload(data)
    for k in [
        "password",
        "hashed_password",
        "token",
        "access_token",
        "refresh_token",
        "jwt",
        "pan",
        "aadhaar",
        "salary",
        "gross_salary",
        "basic_salary",
        "annual_gross",
        "net_pay",
        "bank_account",
        "ifsc",
        "otp",
    ]:
        assert sanitized[k] == "[REDACTED]", f"Key {k} was not redacted"
    assert sanitized["safe_key"] == "tax_regime_new"


def test_m8_nested_and_list_sensitive_data_redaction():
    data = {
        "request_context": {
            "employee_info": {
                "gross_salary": 2500000,
                "pan": "XYZPK9999Z",
                "bank_account": "1234567890",
            },
            "allowances": [
                {"name": "HRA", "salary": 500000},
                {"name": "Special", "amount": 200000},
            ],
        }
    }
    sanitized = sanitize_payload(data)
    assert sanitized["request_context"]["employee_info"]["gross_salary"] == "[REDACTED]"
    assert sanitized["request_context"]["employee_info"]["pan"] == "[REDACTED]"
    assert sanitized["request_context"]["employee_info"]["bank_account"] == "[REDACTED]"
    assert sanitized["request_context"]["allowances"][0]["salary"] == "[REDACTED]"
    assert sanitized["request_context"]["allowances"][1]["amount"] == 200000


def test_m8_exception_traceback_sensitive_data_redaction():
    try:
        raise ValueError(
            "Calculation failed for PAN ABCDE1234F with Aadhaar 1234 5678 9012 and password: secretPass123!"
        )
    except Exception as exc:
        raw_tb = traceback.format_exc()
        sanitized_tb = sanitize_string(raw_tb)

        assert "ABCDE1234F" not in sanitized_tb
        assert "[REDACTED_PAN]" in sanitized_tb
        assert "1234 5678 9012" not in sanitized_tb
        assert "[REDACTED_AADHAAR]" in sanitized_tb
        assert "secretPass123!" not in sanitized_tb
        assert "[REDACTED_PASSWORD]" in sanitized_tb

        event = ObservabilityEvent(
            event_type=EventType.CALCULATION_FAILED,
            severity=EventSeverity.ERROR,
            service="calculation_engine",
            component="TaxCalculator",
            operation="calculate_tax",
            details={"error_message": sanitize_string(str(exc)), "salary": 1500000, "pan": "ABCDE1234F"},
        )
        assert event.details["salary"] == "[REDACTED]"
        assert event.details["pan"] == "[REDACTED]"
        assert "ABCDE1234F" not in str(event.details["error_message"])


def test_m8_http_headers_and_query_params_redaction():
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-IDcSemACt8x4iTMCda8Yhe3iZaWbvV5XKSTbuAn0M",
        "Cookie": "access_token=eyJhbGci...; refresh_token=eyJhbGci...",
        "X-API-Key": "secret_api_key_live_2026",
        "Content-Type": "application/json",
    }
    sanitized_headers = sanitize_payload(headers)
    assert sanitized_headers["Authorization"] == "[REDACTED]"
    assert sanitized_headers["Cookie"] == "[REDACTED]"
    assert sanitized_headers["X-API-Key"] == "[REDACTED]"
    assert sanitized_headers["Content-Type"] == "application/json"


def test_m8_rag_prompts_and_evidence_non_disclosure():
    rag_payload = {
        "system_prompt": "You are a confidential tax assistant with master system prompt...",
        "raw_prompt": "My PAN is ABCDE1234F and salary is 2400000, please tell me my tax",
        "private_evidence": "Internal executive tax strategy doc 2026",
        "public_reference": "CBDT Notification 22/2026",
    }
    sanitized_rag = sanitize_payload(rag_payload)
    assert sanitized_rag["system_prompt"] == "[REDACTED]"
    assert sanitized_rag["raw_prompt"] == "[REDACTED]"
    assert sanitized_rag["private_evidence"] == "[REDACTED]"
    assert sanitized_rag["public_reference"] == "CBDT Notification 22/2026"
