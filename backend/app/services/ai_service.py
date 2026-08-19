from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.rag.ai_tools import AIToolService
from app.engine.rag.citation_validator import CitationValidator
from app.engine.rag.llm_provider import LLMMessage, LLMProvider, MockDevLLMProvider
from app.engine.rag.retriever import FinancialRAGRetriever
from app.models.auth import User
from app.models.chat import ChatMessage, ChatSession


@dataclass
class ChatInquiryResponseDTO:
    session_id: int
    message_id: int
    response_text: str
    citations: list[dict[str, Any]]
    trace_metadata: dict[str, Any]


class AIService:
    """
    Core AI Financial Assistant Service.
    Orchestrates: Intent classification -> Evidence Retrieval -> Scoped Tool Execution -> Grounded Response -> Citation Validation.
    """

    def __init__(self, db: Session, llm_provider: LLMProvider | None = None):
        self.db = db
        self.llm = llm_provider or MockDevLLMProvider()
        self.retriever = FinancialRAGRetriever(db)

    def process_inquiry(
        self,
        user: User,
        query: str,
        session_id: int | None = None,
        financial_year: str = "2025-26",
    ) -> ChatInquiryResponseDTO:
        # 1. Manage ChatSession
        if session_id:
            chat_session = self.db.scalar(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user.id,
                )
            )
            if not chat_session:
                raise ValueError("Chat session not found or unauthorized.")
        else:
            chat_session = ChatSession(
                user_id=user.id,
                title=query[:40] + ("..." if len(query) > 40 else ""),
                session_metadata={"financial_year": financial_year},
            )
            self.db.add(chat_session)
            self.db.flush()

        # 2. Persist User Message
        user_msg = ChatMessage(
            session_id=chat_session.id,
            role="USER",
            content=query,
            citations={},
            trace_metadata={},
        )
        self.db.add(user_msg)
        self.db.flush()

        # 3. Retrieve Official Statutory Evidence
        evidence_pack = self.retriever.retrieve_evidence(
            query=query,
            financial_year=financial_year,
        )

        # 4. Execute Scoped AI Tools
        tool_service = AIToolService(self.db, user)
        current_calc = tool_service.get_current_calculation()

        # 5. Build Grounded Context for LLM
        system_prompt = (
            "You are SmartSalary's Evidence-Grounded Indian Financial & Tax Assistant. "
            "You explain salary, taxes, PF, and payslip data using only authorized employee context and official statutory sources. "
            "CRITICAL: You are strictly PROHIBITED from calculating math or estimating new numbers in natural language. "
            "If the user asks what-if or simulation queries (e.g., 'What if my bonus is 50,000?' or 'What if basic is 80k?'), "
            "you MUST output a structured simulation trigger action: "
            "ACTION: TRIGGER_CALCULATION_SIMULATOR with parameter deltas, so the deterministic engine computes the verified result."
        )

        context_evidence = "AUTHORITATIVE STATUTORY EVIDENCE:\n"
        for c in evidence_pack.chunks:
            context_evidence += f"- [{c.authority}] {c.title} ({c.section_reference}): {c.content}\n"

        if current_calc.is_authorized and current_calc.data:
            context_evidence += f"\nAUTHORIZED EMPLOYEE DATA:\n{current_calc.data}\n"

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="system", content=context_evidence),
            LLMMessage(role="user", content=query),
        ]

        # 6. Generate LLM Completion
        llm_resp = self.llm.generate(messages)

        # 7. Validate Citations
        citations = CitationValidator.validate_and_extract_citations(
            ai_response_text=llm_resp.content,
            evidence_pack=evidence_pack,
        )

        citation_dicts = [
            {
                "source_title": cit.source_title,
                "authority": cit.authority,
                "section_reference": cit.section_reference,
                "is_verified": cit.is_verified,
            }
            for cit in citations
        ]

        trace_meta = {
            "model_name": llm_resp.model_name,
            "tokens_used": llm_resp.tokens_used,
            "financial_year": financial_year,
            "evidence_chunk_ids": [c.chunk_id for c in evidence_pack.chunks],
        }

        # Check for simulation handoff trigger
        simulation_action = None
        if "TRIGGER_CALCULATION_SIMULATOR" in llm_resp.content or "what if" in query.lower():
            trace_meta["action_required"] = "TRIGGER_CALCULATION_SIMULATOR"

        # 8. Persist Assistant Response
        asst_msg = ChatMessage(
            session_id=chat_session.id,
            role="ASSISTANT",
            content=llm_resp.content,
            citations={"citations": citation_dicts},
            trace_metadata=trace_meta,
        )
        self.db.add(asst_msg)
        self.db.flush()

        return ChatInquiryResponseDTO(
            session_id=chat_session.id,
            message_id=asst_msg.id,
            response_text=llm_resp.content,
            citations=citation_dicts,
            trace_metadata=trace_meta,
        )
