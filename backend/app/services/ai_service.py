from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.rag.citation_validator import CitationValidator
from app.engine.rag.llm_provider import LLMMessage, LLMProvider, MockDevLLMProvider
from app.engine.rag.retriever import FinancialRAGRetriever
from app.engine.rag.source_display_service import RAGSourceDisplayService
from app.models.auth import User
from app.models.calculation import CalculationRun
from app.models.chat import ChatMessage, ChatSession
from app.models.employee import Employee
from app.services.calculation_context_service import CalculationContext, resolve_owned_calculation


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

    def process_chat_inquiry(
        self,
        user: User,
        query: str,
        session_id: int | None = None,
        snapshot_id: int | None = None,
        financial_year: str = "2025-26",
    ) -> ChatInquiryResponseDTO:
        # 1. Resolve or Create Chat Session
        chat_session = None
        if session_id:
            chat_session = self.db.scalar(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user.id,
                )
            )

        if not chat_session:
            chat_session = ChatSession(
                user_id=user.id,
                title=query[:60],
            )
            self.db.add(chat_session)
            self.db.flush()

        # 2. Persist User Message
        user_msg = ChatMessage(
            session_id=chat_session.id,
            role="USER",
            content=query,
        )
        self.db.add(user_msg)
        self.db.flush()

        # 3. Retrieve Grounded Evidence
        evidence_pack = FinancialRAGRetriever(self.db).retrieve_evidence(
            query=query,
            financial_year=financial_year,
        )

        # 4. Intent Classification & Calculation Context Binding
        clean_q = query.strip().lower()

        # Check for explicit "Sources?" inquiry
        if clean_q in ("sources", "sources?", "what are the sources?", "show sources", "view sources"):
            cards = RAGSourceDisplayService.get_source_evidence_cards()
            card_dicts = [c.to_dict() for c in cards]

            resp_lines = ["### Official Statutory Evidence Sources\n"]
            for c in cards:
                resp_lines.append(
                    f"- **{c.document_title}** ({c.authority})\n"
                    f"  - **Section/Rule:** `{c.section_reference}` | **Jurisdiction:** `{c.jurisdiction}`\n"
                    f"  - **Effective:** {c.effective_from} to {c.effective_to or 'Indefinite'} (FY {c.financial_year})\n"
                    f"  - **Evidence Assertion:** {c.assertion_text}\n"
                    f"  - **Official Link:** [{c.authority}]({c.official_url})\n"
                )

            evidence_text = "\n".join(resp_lines)
            asst_msg = ChatMessage(
                session_id=chat_session.id,
                role="ASSISTANT",
                content=evidence_text,
                citations={"citations": card_dicts},
                trace_metadata={"intent": "EVIDENCE_REQUEST", "state": "ANSWER", "is_source_display": True},
            )
            self.db.add(asst_msg)
            self.db.flush()

            return ChatInquiryResponseDTO(
                session_id=chat_session.id,
                message_id=asst_msg.id,
                response_text=evidence_text,
                citations=card_dicts,
                trace_metadata={"intent": "EVIDENCE_REQUEST", "state": "ANSWER", "is_source_display": True},
            )

        # Classify Intent
        is_calc_query = any(k in clean_q for k in ("tax", "salary", "take home", "deduction", "why", "how", "pf", "pt", "slab", "rebate", "87a", "in hand", "pay"))

        # Resolve Active Calculation Context if snapshot_id provided or query is calculation-specific
        calc_context: CalculationContext | None = None
        if snapshot_id:
            try:
                calc_context = resolve_owned_calculation(self.db, calculation_id=snapshot_id, user=user)
            except Exception:
                calc_context = None

        if not calc_context and is_calc_query:
            # Check user's latest calculation run
            emp = self.db.scalar(select(Employee).where(Employee.user_id == user.id))
            if emp:
                latest_run = self.db.scalar(
                    select(CalculationRun)
                    .where(CalculationRun.employee_id == emp.id)
                    .order_by(CalculationRun.id.desc())
                )
                if latest_run:
                    calc_context = resolve_owned_calculation(self.db, calculation_id=latest_run.id, user=user)

        # 3-State Firewall Gate: If required evidence cannot be verified -> ABSTAIN
        if not evidence_pack.chunks and not calc_context:
            abstain_text = (
                "### Short Answer\n"
                "I cannot verify this query from the available official statutory evidence.\n\n"
                "### What This Means For You\n"
                "Please run a verified salary calculation or inspect our official regulatory sources in Evidence & Status."
            )
            asst_msg = ChatMessage(
                session_id=chat_session.id,
                role="ASSISTANT",
                content=abstain_text,
                citations={},
                trace_metadata={"intent": "UNKNOWN", "state": "ABSTAIN"},
            )
            self.db.add(asst_msg)
            self.db.flush()
            return ChatInquiryResponseDTO(
                session_id=chat_session.id,
                message_id=asst_msg.id,
                response_text=abstain_text,
                citations=[],
                trace_metadata={"intent": "UNKNOWN", "state": "ABSTAIN"},
            )

        # 5. Build Grounded Context for LLM
        system_prompt = (
            "You are SmartSalary's Evidence-Grounded Indian Financial & Tax Assistant.\n"
            "You explain salary, taxes, PF, and statutory deductions using ONLY the provided calculation snapshot and verified official statutory evidence.\n"
            "CRITICAL CONSTRAINTS:\n"
            "1. You are strictly PROHIBITED from inventing tax numbers, calculating math independently, or hallucinating citations.\n"
            "2. Structure calculation explanations with exact markdown headers:\n"
            "### Short Answer\n"
            "### Your Calculation\n"
            "### Why\n"
            "### Applicable Rule\n"
            "### Official Source\n"
            "### What This Means For You\n"
            "3. If the user asks simulation/what-if questions, output: ACTION: TRIGGER_CALCULATION_SIMULATOR."
        )

        context_evidence = "AUTHORITATIVE STATUTORY EVIDENCE:\n"
        for c in evidence_pack.chunks:
            context_evidence += f"- [{c.authority}] {c.title} ({c.section_reference}): {c.content}\n"

        if calc_context:
            res_data = calc_context.output_snapshot
            context_evidence += (
                f"\nACTIVE IMMUTABLE CALCULATION CONTEXT (ID #{calc_context.calculation_id}):\n"
                f"- Financial Year: {calc_context.financial_year} | Regime: {calc_context.regime} | State: {calc_context.state}\n"
                f"- Annual Gross CTC: {res_data.get('annual_gross_salary')}\n"
                f"- Net Taxable Income: {res_data.get('taxable_income')}\n"
                f"- Total Annual Tax: {res_data.get('total_annual_tax_liability')}\n"
                f"- Section 87A Rebate: {res_data.get('section_87a_rebate')}\n"
                f"- Annual EPF: {res_data.get('annual_employee_pf')}\n"
                f"- Annual Professional Tax: {res_data.get('annual_professional_tax')}\n"
                f"- Annual Take-Home: {res_data.get('estimated_annual_take_home')}\n"
                f"- Monthly Take-Home: {res_data.get('estimated_monthly_take_home')}\n"
            )

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
            "intent": "CURRENT_CALCULATION" if calc_context else "GENERAL_TAX",
            "state": "ANSWER",
            "calculation_id": calc_context.calculation_id if calc_context else None,
            "evidence_chunk_ids": [c.chunk_id for c in evidence_pack.chunks],
        }

        # Check for simulation handoff trigger
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

    process_inquiry = process_chat_inquiry
