from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_middleware import CSRFProtection, get_current_user
from app.core.database import get_db
from app.core.rate_limiter import InMemoryRateLimiter
from app.models.auth import User
from app.models.chat import ChatSession
from app.services.ai_service import AIService

router = APIRouter()


class ChatInquiryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    session_id: int | None = None
    financial_year: str = "2025-26"


class ChatMessageSchema(BaseModel):
    id: int
    role: str
    content: str
    citations: dict[str, Any] = Field(default_factory=dict)
    created_at: Any = None


class ChatSessionDetailSchema(BaseModel):
    id: int
    title: str
    messages: list[ChatMessageSchema]


@router.post("/inquire", status_code=status.HTTP_200_OK)
def inquire_ai_assistant(
    req: ChatInquiryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Evidence-Grounded AI Inquiry Endpoint:
    - Sliding-window rate limited (Max 20 requests per min).
    - Validates CSRF.
    - Grounded in official statutory citations and authorized user snapshots.
    """
    client_ip = InMemoryRateLimiter.get_client_ip(request)
    InMemoryRateLimiter.check_rate_limit(f"ai_inquire_{client_ip}", max_requests=20, window_seconds=60)
    CSRFProtection.validate_request(request)

    ai_service = AIService(db)
    try:
        dto = ai_service.process_inquiry(
            user=current_user,
            query=req.query,
            session_id=req.session_id,
            financial_year=req.financial_year,
        )
        db.commit()

        return {
            "session_id": dto.session_id,
            "message_id": dto.message_id,
            "response": dto.response_text,
            "citations": dto.citations,
            "trace_metadata": dto.trace_metadata,
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/sessions")
def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists user's recent chat sessions."""
    sessions = list(
        db.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == current_user.id)
            .order_by(ChatSession.created_at.desc())
            .limit(20)
        ).all()
    )

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at,
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
def get_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetches chat session message history."""
    chat_session = db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    return {
        "id": chat_session.id,
        "title": chat_session.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "created_at": m.created_at,
            }
            for m in chat_session.messages
        ],
    }
