"""
SmartSalary India — Structured Observability & Telemetry Framework (M8 Hardened)
Provides thread-safe structured, non-sensitive, operational event logging and error handling across:
- Application errors & Unhandled exceptions
- Calculation failures & Invariant breaches
- Regulatory resolution failures & REQUIRES_VERIFICATION & Superseded/Draft/Proposed blocks
- RAG retrieval, citation & prompt injection containment
- Security, tenant isolation, CSRF, Token Replay & IDOR containment
- Health/Readiness diagnostics
- Production-wired Operational Metrics & Latency Profiling
- Concurrency-safe, non-mutating event store with tenant authorization checks
"""

import json
import logging
import re
import threading
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("smart_salary_observability")


class EventSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    REGULATORY = "REGULATORY"
    SECURITY = "SECURITY"
    CRITICAL = "CRITICAL"


class EventType(StrEnum):
    # Application & General
    APPLICATION_ERROR = "APPLICATION_ERROR"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"
    API_FAILURE = "API_FAILURE"

    # Calculation
    CALCULATION_STARTED = "CALCULATION_STARTED"
    CALCULATION_COMPLETED = "CALCULATION_COMPLETED"
    CALCULATION_FAILED = "CALCULATION_FAILED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_APPLICABILITY = "MISSING_APPLICABILITY"

    # Regulatory
    RULE_RESOLUTION_FAILED = "RULE_RESOLUTION_FAILED"
    EVIDENCE_LOOKUP_FAILED = "EVIDENCE_LOOKUP_FAILED"
    REQUIRES_VERIFICATION = "REQUIRES_VERIFICATION"
    REGULATORY_CONFLICT = "REGULATORY_CONFLICT"
    FUTURE_RULE_BLOCKED = "FUTURE_RULE_BLOCKED"
    PROPOSED_RULE_BLOCKED = "PROPOSED_RULE_BLOCKED"
    DRAFT_RULE_BLOCKED = "DRAFT_RULE_BLOCKED"
    SUPERSEDED_RULE_BLOCKED = "SUPERSEDED_RULE_BLOCKED"
    WRONG_JURISDICTION = "WRONG_JURISDICTION"
    WRONG_FINANCIAL_YEAR = "WRONG_FINANCIAL_YEAR"

    # RAG
    RAG_REQUEST = "RAG_REQUEST"
    RAG_RETRIEVAL_FAILED = "RAG_RETRIEVAL_FAILED"
    RAG_CITATION_FAILED = "RAG_CITATION_FAILED"
    RAG_PROMPT_INJECTION = "RAG_PROMPT_INJECTION"
    RAG_DOCUMENT_INJECTION = "RAG_DOCUMENT_INJECTION"
    RAG_TOOL_AUTHORIZATION_FAILURE = "RAG_TOOL_AUTHORIZATION_FAILURE"
    RAG_CROSS_TENANT_ATTEMPT = "RAG_CROSS_TENANT_ATTEMPT"

    # Security & Tenant
    AUTH_FAILURE = "AUTH_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    IDOR_ATTEMPT = "IDOR_ATTEMPT"
    TENANT_ISOLATION_FAILURE = "TENANT_ISOLATION_FAILURE"
    TOKEN_REPLAY = "TOKEN_REPLAY"
    MALICIOUS_FILE_DETECTED = "MALICIOUS_FILE_DETECTED"
    INVALID_DOCUMENT = "INVALID_DOCUMENT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    CSRF_FAILURE = "CSRF_FAILURE"

    # Payroll & Reporting
    PAYROLL_STARTED = "PAYROLL_STARTED"
    PAYROLL_COMPLETED = "PAYROLL_COMPLETED"
    PAYROLL_FAILED = "PAYROLL_FAILED"
    REPORT_REQUEST = "REPORT_REQUEST"
    REPORT_GENERATION_FAILED = "REPORT_GENERATION_FAILED"

    # System & Database & Health
    DATABASE_FAILURE = "DATABASE_FAILURE"
    HEALTH_FAILURE = "HEALTH_FAILURE"


# List of sensitive keys to recursively sanitize
SENSITIVE_KEYS = {
    "password",
    "hashed_password",
    "token",
    "access_token",
    "refresh_token",
    "jwt",
    "secret",
    "api_key",
    "pan",
    "aadhaar",
    "bank_account",
    "ifsc",
    "salary",
    "gross_salary",
    "basic_salary",
    "annual_gross",
    "net_pay",
    "otp",
    "authorization",
    "cookie",
    "x-api-key",
    "set-cookie",
    "system_prompt",
    "raw_prompt",
    "private_evidence",
    "private_document",
    "connection_string",
    "db_password",
    "database_url",
}

# Regex patterns for string sanitization
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", re.IGNORECASE)
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*\b")
PASSWORD_IN_STR_PATTERN = re.compile(r"(password\s*[:=]\s*)([^\s,;&]+)", re.IGNORECASE)


def sanitize_string(text: str) -> str:
    """Redacts PAN, Aadhaar, JWT, and obvious password substrings in raw strings/tracebacks."""
    if not isinstance(text, str):
        return text
    text = PAN_PATTERN.sub("[REDACTED_PAN]", text)
    text = AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", text)
    text = JWT_PATTERN.sub("[REDACTED_JWT]", text)
    text = PASSWORD_IN_STR_PATTERN.sub(r"\1[REDACTED_PASSWORD]", text)
    return text


def sanitize_payload(obj: Any) -> Any:
    """Recursively redacts sensitive PII, credentials, salary amounts, and strings in nested structures."""
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            key_str = str(k).lower().strip()
            if key_str in SENSITIVE_KEYS:
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(obj, (list, tuple, set)):
        return [sanitize_payload(x) for x in obj]
    elif isinstance(obj, str):
        return sanitize_string(obj)
    elif isinstance(obj, Exception):
        return sanitize_string(str(obj))
    return obj


@dataclass
class ObservabilityEvent:
    event_type: EventType
    severity: EventSeverity
    service: str
    component: str
    operation: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    environment: str = "production"
    request_id: str | None = None
    correlation_id: str | None = None
    tenant_id: int | None = None
    user_id: int | None = None
    calculation_id: int | None = None
    snapshot_id: str | None = None
    rule_id: str | None = None
    rule_version: str | None = None
    rule_bundle_id: str | None = None
    rule_bundle_hash: str | None = None
    evidence_bundle_id: str | None = None
    evidence_bundle_hash: str | None = None
    engine_version: str | None = "2026.1"
    schema_version: str | None = "1.0"
    financial_year: str | None = None
    jurisdiction: str | None = None
    failure_type: str | None = None
    safe_error_code: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.details = sanitize_payload(self.details)
        if self.safe_error_code:
            self.safe_error_code = sanitize_string(self.safe_error_code)

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["event_type"] = self.event_type.value
        raw["severity"] = self.severity.value
        return raw

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class OperationalMetricsRegistry:
    """
    Central, thread-safe operational metrics collector wired to production execution paths.
    """

    _lock = threading.Lock()
    _counters: dict[str, int] = defaultdict(int)
    _latencies: dict[str, list[float]] = defaultdict(list)

    @classmethod
    def increment(cls, metric_name: str, amount: int = 1) -> None:
        with cls._lock:
            cls._counters[metric_name] += amount

    @classmethod
    def record_latency(cls, metric_name: str, duration_ms: float) -> None:
        with cls._lock:
            cls._latencies[metric_name].append(duration_ms)

    @classmethod
    def get_count(cls, metric_name: str) -> int:
        with cls._lock:
            return cls._counters[metric_name]

    @classmethod
    def get_latencies(cls, metric_name: str) -> list[float]:
        with cls._lock:
            return list(cls._latencies[metric_name])

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._counters.clear()
            cls._latencies.clear()


class ObservabilityService:
    """
    Central operational telemetry bus.
    Guarantees zero-mutation on calculation/rule/audit state and strictly emits sanitized operational events.
    Enforces thread-safety, tenant-level authorization filtering, and operational metric recording.
    """

    _lock = threading.Lock()
    _EVENT_STORE: list[ObservabilityEvent] = []

    @classmethod
    def emit(cls, event: ObservabilityEvent) -> None:
        with cls._lock:
            cls._EVENT_STORE.append(event)
            # Automatic metric recording for event types
            OperationalMetricsRegistry.increment(f"events.{event.event_type.value.lower()}")
            OperationalMetricsRegistry.increment(f"severity.{event.severity.value.lower()}")

        log_str = event.to_json()
        if event.severity in (
            EventSeverity.CRITICAL,
            EventSeverity.SECURITY,
            EventSeverity.ERROR,
            EventSeverity.REGULATORY,
        ):
            logger.error(f"[OBSERVABILITY] {log_str}")
        elif event.severity == EventSeverity.WARNING:
            logger.warning(f"[OBSERVABILITY] {log_str}")
        else:
            logger.info(f"[OBSERVABILITY] {log_str}")

    @classmethod
    def get_events(
        cls,
        tenant_id: int | None = None,
        requesting_tenant_id: int | None = None,
        is_super_admin: bool = False,
    ) -> list[ObservabilityEvent]:
        """
        Retrieves events with strict tenant authorization boundary.
        Non-superadmins can NEVER query other tenant's events.
        """
        if requesting_tenant_id is not None and not is_super_admin:
            if tenant_id is not None and tenant_id != requesting_tenant_id:
                cls.emit(
                    ObservabilityEvent(
                        event_type=EventType.AUTHORIZATION_FAILURE,
                        severity=EventSeverity.SECURITY,
                        service="observability_service",
                        component="ObservabilityService",
                        operation="get_events",
                        tenant_id=requesting_tenant_id,
                        safe_error_code="ERR_CROSS_TENANT_TELEMETRY_DENIED",
                        details={"target_tenant": tenant_id, "requesting_tenant": requesting_tenant_id},
                    )
                )
                raise PermissionError("CROSS_TENANT_TELEMETRY_ACCESS_DENIED: Tenant boundary breach blocked.")
            # Default to requesting tenant
            tenant_id = requesting_tenant_id

        with cls._lock:
            if tenant_id is not None:
                return [e for e in cls._EVENT_STORE if e.tenant_id == tenant_id]
            return list(cls._EVENT_STORE)

    @classmethod
    def clear_events(cls) -> None:
        with cls._lock:
            cls._EVENT_STORE.clear()
            OperationalMetricsRegistry.reset()
