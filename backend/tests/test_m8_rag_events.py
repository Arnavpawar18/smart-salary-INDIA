"""
M8 RAG Telemetry Suite
Verifies:
- Prompt injection & Document injection containment telemetry
- Citation failure & Missing evidence telemetry
- Tool authorization failure telemetry
- Cross-tenant RAG retrieval attempt telemetry
- Zero sensitive data (private prompts, system prompts, private documents) in telemetry
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


def test_m8_rag_complete_telemetry_matrix():
    rag_events = [
        (
            EventType.RAG_REQUEST,
            EventSeverity.INFO,
            "FinancialRAGRetriever",
            "search_chunks",
            "STATUS_OK",
            {"query_domain": "DIRECT_TAX", "raw_prompt": "Confidential salary query"},
        ),
        (
            EventType.RAG_RETRIEVAL_FAILED,
            EventSeverity.WARNING,
            "FinancialRAGRetriever",
            "retrieve_chunks",
            "ERR_NO_GROUNDING_CHUNKS",
            {"query_topic": "SECTION_80U"},
        ),
        (
            EventType.RAG_CITATION_FAILED,
            EventSeverity.WARNING,
            "CitationValidator",
            "validate_citations",
            "ERR_UNVERIFIED_CITATION",
            {"unverified_citation": "CBDT Fake Circular 2026"},
        ),
        (
            EventType.RAG_PROMPT_INJECTION,
            EventSeverity.SECURITY,
            "PromptSanitizer",
            "sanitize_input",
            "ERR_PROMPT_INJECTION_DETECTED",
            {"pattern": "IGNORE PREVIOUS SYSTEM PROMPT", "action": "BLOCKED"},
        ),
        (
            EventType.RAG_DOCUMENT_INJECTION,
            EventSeverity.SECURITY,
            "DocumentValidator",
            "validate_upload",
            "ERR_DOCUMENT_INJECTION_DETECTED",
            {"file_type": "PDF", "threat": "EMBEDDED_EXECUTABLE_SCRIPT"},
        ),
        (
            EventType.RAG_TOOL_AUTHORIZATION_FAILURE,
            EventSeverity.SECURITY,
            "AIToolAuthorizer",
            "authorize_tool_call",
            "ERR_TOOL_NOT_AUTHORIZED",
            {"tool_name": "db_delete_rule", "role": "EMPLOYEE"},
        ),
        (
            EventType.RAG_CROSS_TENANT_ATTEMPT,
            EventSeverity.SECURITY,
            "FinancialRAGRetriever",
            "search_documents",
            "ERR_CROSS_TENANT_BLOCKED",
            {"requesting_tenant": 101, "target_tenant": 202},
        ),
    ]

    for evt_type, sev, comp, op, code, details in rag_events:
        ObservabilityService.emit(
            ObservabilityEvent(
                event_type=evt_type,
                severity=sev,
                service="rag_subsystem",
                component=comp,
                operation=op,
                correlation_id=f"corr-rag-{evt_type.value.lower()}",
                tenant_id=101,
                safe_error_code=code,
                details=details,
            )
        )

    all_events = ObservabilityService.get_events(tenant_id=101)
    assert len(all_events) == len(rag_events)

    # Verify redaction of prompt contents in RAG_REQUEST
    req_event = [e for e in all_events if e.event_type == EventType.RAG_REQUEST][0]
    assert req_event.details["raw_prompt"] == "[REDACTED]"
    assert req_event.details["query_domain"] == "DIRECT_TAX"

    # Verify security metrics
    assert OperationalMetricsRegistry.get_count("events.rag_prompt_injection") == 1
    assert OperationalMetricsRegistry.get_count("events.rag_document_injection") == 1
    assert OperationalMetricsRegistry.get_count("events.rag_tool_authorization_failure") == 1
