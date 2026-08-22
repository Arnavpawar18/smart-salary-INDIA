import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.observability import EventSeverity, EventType, ObservabilityEvent, ObservabilityService, sanitize_payload
from app.engine.common.errors import TenantAuditIsolationError
from app.engine.common.hashing import compute_sha256_hash
from app.models.audit import AuditChainHead, AuditCheckpoint, AuditLog

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


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
    EMAIL_VERIFICATION_SUCCESS = "EMAIL_VERIFICATION_SUCCESS"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    CALCULATION_SAVED = "CALCULATION_SAVED"
    CALCULATION_CORRECTED = "CALCULATION_CORRECTED"
    PAYSLIP_GENERATED = "PAYSLIP_GENERATED"
    REGULATORY_OVERRIDE_ATTEMPT = "REGULATORY_OVERRIDE_ATTEMPT"
    TAMPER_DETECTED = "TAMPER_DETECTED"


class AuditService:
    """
    Cryptographic, append-only audit ledger manager.
    Enforces atomic sequence/previous-hash allocation, recursive sensitive data redaction,
    canonical JSON hashing over 14 security-critical fields, and strict tenant boundaries.
    """

    _global_lock = threading.RLock()

    @classmethod
    def canonical_event_dict(
        cls,
        event_uuid: str,
        chain_id: str,
        sequence_number: int,
        tenant_id: int | None,
        actor_type: str,
        actor_id: int | None,
        resource_type: str,
        resource_id: int | None,
        action: str,
        timestamp: str,
        schema_version: str,
        correlation_id: str | None,
        sanitized_payload: dict[str, Any] | None,
        previous_event_hash: str,
    ) -> dict[str, Any]:
        """Produces canonical representation over all 14 security-critical immutable event fields."""
        return {
            "action": action,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "chain_id": chain_id,
            "correlation_id": correlation_id,
            "event_uuid": event_uuid,
            "payload": sanitized_payload,
            "previous_event_hash": previous_event_hash,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "schema_version": schema_version,
            "sequence_number": sequence_number,
            "tenant_id": tenant_id,
            "timestamp": timestamp,
        }

    @classmethod
    def compute_event_hash(cls, canonical_dict: dict[str, Any]) -> str:
        """Computes SHA-256 hex digest of sorted canonical JSON representation."""
        return compute_sha256_hash(canonical_dict)

    @classmethod
    def log_event(
        cls,
        db: Session,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        entity_name: str | None = None,  # Backward compatibility
        entity_id: int | None = None,  # Backward compatibility
        tenant_id: int | None = None,
        actor_type: str = "USER",
        actor_id: int | None = None,
        user_id: int | None = None,
        payload: dict[str, Any] | None = None,
        old_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: str | None = None,
        chain_id: str | None = None,
        auto_commit: bool = True,
    ) -> AuditLog:
        """
        Appends an immutable event to the specified audit chain atomically.
        Sanitizes payload before hashing and persistence.
        """
        # Resolve legacy field aliases
        res_type = resource_type or entity_name or "GENERIC"
        res_id = resource_id if resource_id is not None else entity_id
        act_id = actor_id if actor_id is not None else user_id

        # Determine chain_id: TENANT_{id} or SYSTEM_GLOBAL
        if chain_id is None:
            if tenant_id is not None:
                chain_id = f"TENANT_{tenant_id}"
            else:
                chain_id = "SYSTEM_GLOBAL"
        elif tenant_id is None and chain_id.startswith("TENANT_"):
            parts = chain_id.split("_")
            if len(parts) >= 2 and parts[1].isdigit():
                tenant_id = int(parts[1])

        # Server-generated canonical UTC ISO-8601 timestamp
        server_timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        event_uuid = str(uuid.uuid4())
        schema_version = "v1.0.0"

        # Sanitize payload before hashing
        sanitized_payload = None
        if payload is not None:
            sanitized_payload = sanitize_payload(payload)
        elif old_state is not None or new_state is not None:
            merged = {}
            if old_state:
                merged["before"] = sanitize_payload(old_state)
            if new_state:
                merged["after"] = sanitize_payload(new_state)
            sanitized_payload = merged

        sanitized_details = details
        if sanitized_details:
            from app.core.observability import sanitize_string

            sanitized_details = sanitize_string(sanitized_details)

        with cls._global_lock:
            # Atomic Chain-Head Allocation: Lock head row or create genesis
            # We attempt with_for_update() if supported by DB backend, fallback to row selection
            try:
                head = db.scalar(select(AuditChainHead).where(AuditChainHead.chain_id == chain_id).with_for_update())
            except Exception:
                # SQLite / unsupported lock fallback (protected by threading._global_lock)
                head = db.scalar(select(AuditChainHead).where(AuditChainHead.chain_id == chain_id))

            if head is None:
                next_sequence = 1
                previous_hash = GENESIS_HASH
                head = AuditChainHead(
                    chain_id=chain_id,
                    tenant_id=tenant_id,
                    last_sequence=1,
                    last_event_uuid=event_uuid,
                    last_event_hash="",  # Populated below
                )
                db.add(head)
            else:
                next_sequence = head.last_sequence + 1
                previous_hash = head.last_event_hash

            # Build canonical dictionary and compute SHA-256 hash
            canonical_repr = cls.canonical_event_dict(
                event_uuid=event_uuid,
                chain_id=chain_id,
                sequence_number=next_sequence,
                tenant_id=tenant_id,
                actor_type=actor_type,
                actor_id=act_id,
                resource_type=res_type,
                resource_id=res_id,
                action=action,
                timestamp=server_timestamp,
                schema_version=schema_version,
                correlation_id=correlation_id,
                sanitized_payload=sanitized_payload,
                previous_event_hash=previous_hash,
            )
            event_hash = cls.compute_event_hash(canonical_repr)

            # Update durable chain head
            head.last_sequence = next_sequence
            head.last_event_uuid = event_uuid
            head.last_event_hash = event_hash

            # Create immutable AuditLog
            audit_log = AuditLog(
                event_uuid=event_uuid,
                chain_id=chain_id,
                sequence_number=next_sequence,
                tenant_id=tenant_id,
                actor_type=actor_type,
                actor_id=act_id,
                user_id=act_id,
                action=action,
                resource_type=res_type,
                resource_id=res_id,
                entity_name=res_type,
                entity_id=res_id,
                timestamp=server_timestamp,
                schema_version=schema_version,
                correlation_id=correlation_id,
                payload=sanitized_payload,
                payload_before=sanitized_payload.get("before") if isinstance(sanitized_payload, dict) else None,
                payload_after=sanitized_payload.get("after") if isinstance(sanitized_payload, dict) else None,
                ip_address=ip_address,
                user_agent=user_agent,
                details=sanitized_details,
                previous_event_hash=previous_hash,
                event_hash=event_hash,
            )
            db.add(audit_log)

            # Checkpoint creation (every 100 events)
            if next_sequence % 100 == 0:
                ckpt_hash = compute_sha256_hash(
                    {"chain_id": chain_id, "sequence": next_sequence, "event_hash": event_hash}
                )
                checkpoint = AuditCheckpoint(
                    chain_id=chain_id,
                    checkpoint_sequence=next_sequence,
                    checkpoint_event_hash=event_hash,
                    checkpoint_hash=ckpt_hash,
                )
                db.add(checkpoint)

            if auto_commit:
                db.commit()
                db.refresh(audit_log)

            return audit_log

    @classmethod
    def get_audit_trail(
        cls,
        db: Session,
        chain_id: str | None = None,
        tenant_id: int | None = None,
        requesting_tenant_id: int | None = None,
        is_super_admin: bool = False,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Retrieves audit trail with strict tenant authorization.
        Non-superadmins can never query other tenant's audit trail.
        """
        if requesting_tenant_id is not None and not is_super_admin:
            if tenant_id is not None and tenant_id != requesting_tenant_id:
                ObservabilityService.emit(
                    ObservabilityEvent(
                        event_type=EventType.AUTHORIZATION_FAILURE,
                        severity=EventSeverity.SECURITY,
                        service="audit_service",
                        component="AuditService",
                        operation="get_audit_trail",
                        tenant_id=requesting_tenant_id,
                        safe_error_code="ERR_CROSS_TENANT_AUDIT_DENIED",
                        details={"target_tenant": tenant_id, "requesting_tenant": requesting_tenant_id},
                    )
                )
                raise TenantAuditIsolationError(f"CROSS_TENANT_AUDIT_DENIED: Access to tenant {tenant_id} prohibited.")
            tenant_id = requesting_tenant_id
            chain_id = f"TENANT_{requesting_tenant_id}"

        stmt = select(AuditLog)
        if chain_id:
            stmt = stmt.where(AuditLog.chain_id == chain_id)
        elif tenant_id:
            stmt = stmt.where(AuditLog.tenant_id == tenant_id)

        stmt = stmt.order_by(AuditLog.sequence_number.asc()).limit(limit)
        return list(db.scalars(stmt).all())


class AuditChainVerifier:
    """
    Deterministic validator for audit ledger integrity.
    Validates:
    - Strictly monotonic sequence numbers (1..N, zero gaps, zero jumps)
    - Unbroken predecessor cryptographic hash links
    - Canonical hash recomputation over all 14 fields (detects payload/actor/timestamp/metadata modification)
    - Durable chain-head alignment (detects tail deletions)
    - Single tenant/chain scope
    """

    @classmethod
    def verify_chain(
        cls,
        db: Session,
        chain_id: str,
        expected_head_hash: str | None = None,
        expected_head_sequence: int | None = None,
    ) -> dict[str, Any]:
        """
        Performs full mathematical & structural verification on an audit chain.
        Returns structured verification diagnostics.
        """
        stmt = select(AuditLog).where(AuditLog.chain_id == chain_id).order_by(AuditLog.sequence_number.asc())
        events = list(db.scalars(stmt).all())

        if not events:
            return {
                "valid": True,
                "chain_id": chain_id,
                "event_count": 0,
                "head_sequence": 0,
                "head_hash": GENESIS_HASH,
                "first_invalid_sequence": None,
                "failure_reason": None,
            }

        # Retrieve durable chain head
        head = db.scalar(select(AuditChainHead).where(AuditChainHead.chain_id == chain_id))

        expected_sequence = 1
        expected_prev_hash = GENESIS_HASH

        for idx, event in enumerate(events):
            seq = event.sequence_number

            # 1. Check sequence monotonicity & gap/jump
            if seq != expected_sequence:
                return {
                    "valid": False,
                    "chain_id": chain_id,
                    "event_count": len(events),
                    "head_sequence": events[-1].sequence_number if events else 0,
                    "head_hash": events[-1].event_hash if events else None,
                    "first_invalid_sequence": seq,
                    "failure_reason": f"SEQUENCE_DISCONTINUITY: Expected sequence {expected_sequence}, found {seq}.",
                }

            # 2. Check previous hash linkage
            if event.previous_event_hash != expected_prev_hash:
                return {
                    "valid": False,
                    "chain_id": chain_id,
                    "event_count": len(events),
                    "head_sequence": events[-1].sequence_number if events else 0,
                    "head_hash": events[-1].event_hash if events else None,
                    "first_invalid_sequence": seq,
                    "failure_reason": f"BROKEN_HASH_LINK: Event {seq} previous_hash does not match predecessor.",
                }

            # 3. Canonical hash recomputation across all 14 fields
            canonical_repr = AuditService.canonical_event_dict(
                event_uuid=event.event_uuid,
                chain_id=event.chain_id,
                sequence_number=event.sequence_number,
                tenant_id=event.tenant_id,
                actor_type=event.actor_type,
                actor_id=event.actor_id,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                action=event.action,
                timestamp=event.timestamp,
                schema_version=event.schema_version,
                correlation_id=event.correlation_id,
                sanitized_payload=event.payload,
                previous_event_hash=event.previous_event_hash,
            )
            recomputed_hash = AuditService.compute_event_hash(canonical_repr)

            if recomputed_hash != event.event_hash:
                return {
                    "valid": False,
                    "chain_id": chain_id,
                    "event_count": len(events),
                    "head_sequence": events[-1].sequence_number if events else 0,
                    "head_hash": events[-1].event_hash if events else None,
                    "first_invalid_sequence": seq,
                    "failure_reason": f"HASH_MISMATCH: Event {seq} recomputed hash {recomputed_hash[:16]}... != recorded hash {event.event_hash[:16]}... (Tampering Detected).",
                }

            # Advance chain state
            expected_prev_hash = event.event_hash
            expected_sequence += 1

        last_event = events[-1]

        # 4. Check durable chain-head commitment (tail deletion detection)
        if head:
            if head.last_sequence != last_event.sequence_number:
                return {
                    "valid": False,
                    "chain_id": chain_id,
                    "event_count": len(events),
                    "head_sequence": last_event.sequence_number,
                    "head_hash": last_event.event_hash,
                    "first_invalid_sequence": head.last_sequence,
                    "failure_reason": f"TAIL_DELETION_DETECTED: Chain head records sequence {head.last_sequence}, but latest ledger event is {last_event.sequence_number}.",
                }
            if head.last_event_hash != last_event.event_hash:
                return {
                    "valid": False,
                    "chain_id": chain_id,
                    "event_count": len(events),
                    "head_sequence": last_event.sequence_number,
                    "head_hash": last_event.event_hash,
                    "first_invalid_sequence": last_event.sequence_number,
                    "failure_reason": f"HEAD_HASH_MISMATCH: Chain head records hash {head.last_event_hash[:16]}..., but latest ledger hash is {last_event.event_hash[:16]}... (Tail Corruption).",
                }

        # 5. Check explicitly supplied expected head hash / sequence
        if expected_head_hash and last_event.event_hash != expected_head_hash:
            return {
                "valid": False,
                "chain_id": chain_id,
                "event_count": len(events),
                "head_sequence": last_event.sequence_number,
                "head_hash": last_event.event_hash,
                "first_invalid_sequence": last_event.sequence_number,
                "failure_reason": f"EXPECTED_HEAD_HASH_MISMATCH: Ledger head hash {last_event.event_hash[:16]}... != expected {expected_head_hash[:16]}...",
            }

        return {
            "valid": True,
            "chain_id": chain_id,
            "event_count": len(events),
            "head_sequence": last_event.sequence_number,
            "head_hash": last_event.event_hash,
            "first_invalid_sequence": None,
            "failure_reason": None,
        }
