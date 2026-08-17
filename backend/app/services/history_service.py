import secrets
from typing import Any


class HistoryService:
    """
    Manages lightweight guest session history using opaque non-sequential tokens.
    Prevents IDOR vulnerabilities without prematurely building enterprise auth in Phase 3.
    """

    @classmethod
    def generate_guest_session_token(cls) -> str:
        return secrets.token_urlsafe(24)

    @classmethod
    def append_calculation_to_guest_history(
        cls,
        session_history: list[dict[str, Any]] | None,
        calculation_summary: dict[str, Any],
        max_items: int = 5,
    ) -> list[dict[str, Any]]:
        history = list(session_history) if session_history else []
        history.insert(0, calculation_summary)
        return history[:max_items]
