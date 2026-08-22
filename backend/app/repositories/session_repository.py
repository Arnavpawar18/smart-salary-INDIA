import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import JWTProvider
from app.models.session import UserSession


class SessionRepository:
    """
    Manages persistent user refresh sessions in the user_sessions table.
    Enforces JTI rotation, SHA-256 token hashing, and session reuse detection.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        user_id: int,
        raw_refresh_token: str,
        jti: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        token_hash = JWTProvider.compute_token_hash(raw_refresh_token)
        session = UserSession(
            user_id=user_id,
            jti=uuid.UUID(jti),
            token_hash=token_hash,
            issued_at=datetime.now(UTC),
            expires_at=expires_at,
            last_used_at=datetime.now(UTC),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_active_session_by_jti(self, jti: str) -> UserSession | None:
        try:
            jti_uuid = uuid.UUID(jti)
        except ValueError:
            return None
        stmt = select(UserSession).where(
            UserSession.jti == jti_uuid,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(UTC),
        )
        return self.db.scalar(stmt)

    def rotate_session(
        self,
        old_jti: str,
        new_raw_refresh_token: str,
        new_jti: str,
        new_expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        """
        Rotates refresh token. Detects token reuse: if old session is already revoked,
        revokes ALL sessions for that user as an automatic security defense.
        """
        old_session = self.db.scalar(select(UserSession).where(UserSession.jti == uuid.UUID(old_jti)))
        if not old_session:
            raise ValueError("Session does not exist")

        if old_session.revoked_at is not None:
            # Token Reuse Detected! Invalidate ALL active sessions for this user.
            self.revoke_all_user_sessions(old_session.user_id)
            raise ValueError("Refresh token reuse detected. All user sessions have been terminated for security.")

        expires_at = old_session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            old_session.revoked_at = datetime.now(UTC)
            self.db.commit()
            raise ValueError("Refresh session has expired")

        # Revoke old session and link to new JTI
        new_jti_uuid = uuid.UUID(new_jti)
        old_session.revoked_at = datetime.now(UTC)
        old_session.replaced_by_jti = new_jti_uuid
        old_session.last_used_at = datetime.now(UTC)

        # Create new session
        new_session = UserSession(
            user_id=old_session.user_id,
            jti=new_jti_uuid,
            token_hash=JWTProvider.compute_token_hash(new_raw_refresh_token),
            issued_at=datetime.now(UTC),
            expires_at=new_expires_at,
            last_used_at=datetime.now(UTC),
            ip_address=ip_address or old_session.ip_address,
            user_agent=user_agent or old_session.user_agent,
        )
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        return new_session

    def revoke_session(self, jti: str) -> None:
        try:
            jti_uuid = uuid.UUID(jti)
        except ValueError:
            return
        stmt = update(UserSession).where(UserSession.jti == jti_uuid).values(revoked_at=datetime.now(UTC))
        self.db.execute(stmt)
        self.db.commit()

    def revoke_all_user_sessions(self, user_id: int) -> int:
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount

    def get_user_active_sessions(self, user_id: int) -> list[UserSession]:
        stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > datetime.now(UTC),
            )
            .order_by(UserSession.last_used_at.desc())
        )
        return list(self.db.scalars(stmt).all())
