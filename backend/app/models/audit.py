import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.engine.common.errors import AuditImmutabilityError
from app.models.base import Base, JSONField, TimestampMixin

if TYPE_CHECKING:
    from app.models.auth import User


class AuditLog(Base, TimestampMixin):
    """
    System-wide append-only, tamper-evident cryptographic audit ledger.
    Every event is sequentially numbered and hashed over 14 immutable fields.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer().with_variant(BigInteger, "postgresql"), primary_key=True, autoincrement=True
    )
    event_uuid: Mapped[str] = mapped_column(
        String(36), default=lambda: str(uuid.uuid4()), nullable=False, unique=True, index=True
    )
    chain_id: Mapped[str] = mapped_column(String(100), default="SYSTEM_GLOBAL", nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    actor_type: Mapped[str] = mapped_column(
        String(50), default="USER", nullable=False
    )  # USER, SYSTEM, SERVICE, API_KEY
    actor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    entity_name: Mapped[str] = mapped_column(String(100), nullable=True)  # Backward compat alias
    entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # Backward compat alias

    timestamp: Mapped[str] = mapped_column(String(50), nullable=False)  # Server UTC ISO-8601
    schema_version: Mapped[str] = mapped_column(String(20), default="v1.0.0", nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONField, nullable=True)
    payload_before: Mapped[dict[str, Any] | None] = mapped_column(JSONField, nullable=True)
    payload_after: Mapped[dict[str, Any] | None] = mapped_column(JSONField, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    previous_event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("chain_id", "sequence_number", name="uq_audit_chain_sequence"),
        UniqueConstraint("event_uuid", name="uq_audit_event_uuid"),
        Index("ix_audit_tenant_chain", "tenant_id", "chain_id"),
    )


class AuditChainHead(Base, TimestampMixin):
    """
    Durable, queryable chain-head commitment per audit chain.
    Prevents undetectable tail deletion attacks and enforces atomic concurrency locks.
    """

    __tablename__ = "audit_chain_heads"

    chain_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    last_sequence: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_event_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    last_event_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class AuditCheckpoint(Base, TimestampMixin):
    """
    Periodic immutable checkpoint for fast verification across large historical audit chains.
    """

    __tablename__ = "audit_checkpoints"

    id: Mapped[int] = mapped_column(
        Integer().with_variant(BigInteger, "postgresql"), primary_key=True, autoincrement=True
    )
    chain_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    checkpoint_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checkpoint_event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_hash: Mapped[str] = mapped_column(String(64), nullable=False)


# ==============================================================================
# DATABASE & ORM-LEVEL IMMUTABILITY ENFORCEMENT HOOKS
# ==============================================================================


@event.listens_for(AuditLog, "before_update")
def audit_log_block_update(mapper, connection, target):
    raise AuditImmutabilityError(
        f"MUTATION_PROHIBITED: AuditLog records are append-only. Event {target.event_uuid} (seq={target.sequence_number}) cannot be updated."
    )


@event.listens_for(AuditLog, "before_delete")
def audit_log_block_delete(mapper, connection, target):
    raise AuditImmutabilityError(
        f"DELETION_PROHIBITED: AuditLog records are immutable. Event {target.event_uuid} (seq={target.sequence_number}) cannot be deleted."
    )


@event.listens_for(AuditChainHead, "before_delete")
def audit_chain_head_block_delete(mapper, connection, target):
    raise AuditImmutabilityError(
        f"DELETION_PROHIBITED: AuditChainHead for chain '{target.chain_id}' is durable and cannot be deleted."
    )


@event.listens_for(AuditCheckpoint, "before_update")
def audit_checkpoint_block_update(mapper, connection, target):
    raise AuditImmutabilityError(
        f"MUTATION_PROHIBITED: AuditCheckpoint records are immutable (checkpoint seq={target.checkpoint_sequence})."
    )


@event.listens_for(AuditCheckpoint, "before_delete")
def audit_checkpoint_block_delete(mapper, connection, target):
    raise AuditImmutabilityError(
        f"DELETION_PROHIBITED: AuditCheckpoint records are immutable (checkpoint seq={target.checkpoint_sequence})."
    )
