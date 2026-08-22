"""
SmartSalary India — Calculation Contracts & Persisted Applicability Decision
Freezes CalculationInput v1, CalculationSnapshot v1, and ApplicabilityDecision v1.
Enforces dual-bundle hashing: rule_bundle_hash and evidence_bundle_hash.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from app.engine.common.hashing import compute_sha256_hash


class DecisionOutcome(StrEnum):
    APPLICABLE = "APPLICABLE"
    EXEMPT = "EXEMPT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REQUIRES_VERIFICATION = "REQUIRES_VERIFICATION"


@dataclass(frozen=True)
class ApplicabilityDecisionV1:
    """Persisted record of why a specific statutory rule applied or was bypassed."""

    decision_id: str
    rule_id: str
    rule_version: str
    outcome: DecisionOutcome
    evaluation_condition: str
    matched_facts: dict[str, Any]
    justification: str
    effective_date: str
    jurisdiction: str
    evidence_assertion_id: str | None = None
    evidence_fragment_id: str | None = None
    source_id: str | None = None
    source_version: str | None = None

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "outcome": self.outcome.value,
            "evaluation_condition": self.evaluation_condition,
            "matched_facts": self.matched_facts,
            "justification": self.justification,
            "effective_date": self.effective_date,
            "jurisdiction": self.jurisdiction,
            "evidence_assertion_id": self.evidence_assertion_id,
            "evidence_fragment_id": self.evidence_fragment_id,
            "source_id": self.source_id,
            "source_version": self.source_version,
        }


@dataclass(frozen=True)
class CalculationSnapshotV1:
    """
    Frozen V1 Immutable Calculation Snapshot Contract.
    Contains dual-bundle hashes, schema version, and append-only correction lineage.
    """

    snapshot_id: UUID
    user_id: UUID | None
    created_at: str
    engine_version: str
    schema_version: str = "v1.0.0"

    # Dual-Bundle Provenance
    rule_bundle_id: str = "RB-AY-2026-27-CENTRAL-V1"
    rule_bundle_hash: str = ""
    evidence_bundle_id: str = "EB-STATUTORY-IN-2026-Q1"
    evidence_bundle_hash: str = ""

    # Lineage / Correction
    parent_snapshot_id: UUID | None = None
    superseded_by: UUID | None = None
    correction_reason: str | None = None

    # Payloads
    inputs_payload: dict[str, Any] = field(default_factory=dict)
    outputs_payload: dict[str, Any] = field(default_factory=dict)
    trace_payload: dict[str, Any] = field(default_factory=dict)
    applicability_decisions: list[ApplicabilityDecisionV1] = field(default_factory=list)

    # Master Checksum
    snapshot_hash: str = ""

    @classmethod
    def create(
        cls,
        user_id: UUID | None,
        engine_version: str,
        rule_bundle_id: str,
        rule_bundle_hash: str,
        evidence_bundle_id: str,
        evidence_bundle_hash: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        trace: dict[str, Any],
        decisions: list[ApplicabilityDecisionV1],
        parent_snapshot_id: UUID | None = None,
        correction_reason: str | None = None,
    ) -> "CalculationSnapshotV1":
        snap_id = uuid4()
        now_str = datetime.now(UTC).isoformat()
        schema_v = "v1.0.0"

        # Canonical hash computation across the 5 pillars:
        # INPUTS + OUTPUTS + RULE_BUNDLE_HASH + EVIDENCE_BUNDLE_HASH + ENGINE_VERSION + SCHEMA_VERSION
        hash_payload = {
            "inputs": inputs,
            "outputs": outputs,
            "rule_bundle_hash": rule_bundle_hash,
            "evidence_bundle_hash": evidence_bundle_hash,
            "engine_version": engine_version,
            "schema_version": schema_v,
        }
        master_hash = compute_sha256_hash(hash_payload)

        return cls(
            snapshot_id=snap_id,
            user_id=user_id,
            created_at=now_str,
            engine_version=engine_version,
            schema_version=schema_v,
            rule_bundle_id=rule_bundle_id,
            rule_bundle_hash=rule_bundle_hash,
            evidence_bundle_id=evidence_bundle_id,
            evidence_bundle_hash=evidence_bundle_hash,
            parent_snapshot_id=parent_snapshot_id,
            correction_reason=correction_reason,
            inputs_payload=inputs,
            outputs_payload=outputs,
            trace_payload=trace,
            applicability_decisions=decisions,
            snapshot_hash=master_hash,
        )

    def to_dict(self) -> dict:
        return {
            "snapshot_id": str(self.snapshot_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "created_at": self.created_at,
            "engine_version": self.engine_version,
            "schema_version": self.schema_version,
            "rule_bundle_id": self.rule_bundle_id,
            "rule_bundle_hash": self.rule_bundle_hash,
            "evidence_bundle_id": self.evidence_bundle_id,
            "evidence_bundle_hash": self.evidence_bundle_hash,
            "parent_snapshot_id": str(self.parent_snapshot_id) if self.parent_snapshot_id else None,
            "superseded_by": str(self.superseded_by) if self.superseded_by else None,
            "correction_reason": self.correction_reason,
            "inputs_payload": self.inputs_payload,
            "outputs_payload": self.outputs_payload,
            "trace_payload": self.trace_payload,
            "applicability_decisions": [d.to_dict() for d in self.applicability_decisions],
            "snapshot_hash": self.snapshot_hash,
        }
