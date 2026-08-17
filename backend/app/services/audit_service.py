from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditEvent:
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    LOGOUT_ALL = "LOGOUT_ALL"
    REFRESH = "REFRESH"
    REFRESH_REUSE_DETECTED = "REFRESH_REUSE_DETECTED"
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_REVOKED = "SESSION_REVOKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    CALCULATION_SAVED = "CALCULATION_SAVED"


class AuditService:
    """
    Records sensitive security and workflow events into the audit_logs table.
    CRITICAL SECURITY RULE: Never log raw passwords, raw JWTs, raw refresh tokens, or secrets.
    """

    @classmethod
    def log_event(
        cls,
        db: Session,
        action: str,
        entity_name: str,
        user_id: int | None = None,
        entity_id: int | None = None,
        old_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            payload_before=old_state,
            payload_after=new_state,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        db.commit()
        return log
