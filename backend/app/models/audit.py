from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.auth import User


class AuditLog(Base, TimestampMixin):
    """
    System-wide immutable audit trail for actions, entity changes, and administrative events.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # CREATE, UPDATE, DELETE, CALCULATION_RUN, LOGIN
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'Employee', 'SalaryRecord'
    entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payload_before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    payload_after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[Optional["User"]] = relationship("User")
