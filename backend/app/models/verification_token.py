import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VerificationToken(Base):
    """
    Table: verification_tokens
    Stores server-side HMAC-SHA256 hashes of 6-digit OTP codes for:
      - EMAIL_VERIFICATION (New user registration activation)
      - PASSWORD_RESET (Two-stage forgot password flow)

    Security Invariants:
      - Zero plaintext OTP storage.
      - Single-use with atomic invalidation.
      - 5-minute time-to-live (TTL).
      - Maximum 5 failed verification attempts before lockout.
      - Strict purpose separation.
    """

    __tablename__ = "verification_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    verification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)  # EMAIL_VERIFICATION, PASSWORD_RESET
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )  # PENDING, VERIFIED, EXPIRED, LOCKED, CANCELLED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_resend_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="verification_tokens")

    __table_args__ = (
        Index(
            "ix_verification_tokens_pending_unique",
            "email",
            "purpose",
            unique=True,
            postgresql_where=(status == "PENDING"),
            sqlite_where=(status == "PENDING"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<VerificationToken(id={self.id}, verification_id={self.verification_id}, "
            f"email={self.email}, purpose={self.purpose}, status={self.status})>"
        )
