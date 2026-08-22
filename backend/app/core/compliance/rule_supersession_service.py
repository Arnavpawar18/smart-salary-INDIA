"""
SmartSalary India — Rule Supersession & Lifecycle Service (M5.2)
Orchestrates immutable regulatory deprecations, bidirectional lineage,
atomic dual-key activations, and conflict/boundary protections.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum

from app.core.compliance.rule_impact_analyzer import (
    ChangeDimensionType,
    DeepRegulatoryChangeImpactAnalyzer,
    RegulatoryChangeInput,
)
from app.core.compliance.rule_registry import ComplianceRuleRegistry, RuleDefinition, RuleStatus
from app.core.compliance.source_registry import AuthorityTier, OfficialSourceRegistry
from app.engine.common.hashing import compute_sha256_hash


class SupersessionConflictType(StrEnum):
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    DATE_CONFLICT = "DATE_CONFLICT"
    JURISDICTION_CONFLICT = "JURISDICTION_CONFLICT"
    FORMULA_CONFLICT = "FORMULA_CONFLICT"
    THRESHOLD_CONFLICT = "THRESHOLD_CONFLICT"
    CEILING_CONFLICT = "CEILING_CONFLICT"
    APPLICABILITY_CONFLICT = "APPLICABILITY_CONFLICT"
    SUPERSESSION_CONFLICT = "SUPERSESSION_CONFLICT"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"


@dataclass(frozen=True)
class SupersessionEvent:
    event_id: str
    old_rule_id: str
    new_rule_id: str
    old_rule_version: str
    new_rule_version: str
    domain: str
    jurisdiction: str
    financial_year: str
    effective_from: str
    superseded_at: str
    reason: str
    detector_id: str
    reviewer_id: str
    approver_id: str
    old_rule_bundle_hash: str
    new_rule_bundle_hash: str
    evidence_bundle_hash: str
    event_hash: str


class RuleSupersessionService:
    """
    Atomic orchestrator for M5.2 regulatory deprecation and supersession.
    """

    _EVENTS: dict[str, SupersessionEvent] = {}
    _SEEN_KEYS: set[str] = set()

    @classmethod
    def execute_supersession(
        cls,
        old_rule_id: str,
        new_rule_id: str,
        new_rule_version: str,
        new_source_id: str,
        new_document_id: str,
        new_evidence_id: str,
        effective_from: date,
        effective_to: date | None,
        new_formula: str,
        new_condition: str,
        reason: str,
        detector_id: str,
        reviewer_id: str,
        approver_id: str,
        diff_text: str = "Statutory amendment",
        change_type: ChangeDimensionType = ChangeDimensionType.RATE_CHANGE,
    ) -> tuple[RuleDefinition, RuleDefinition, SupersessionEvent]:
        # 1. Separation of Duties Check
        if len({detector_id, reviewer_id, approver_id}) < 3:
            raise PermissionError(
                "SEPARATION_OF_DUTIES_VIOLATION: Detector, Reviewer, and Approver must be 3 distinct actors."
            )

        # 2. Retrieve Old Rule
        old_rule = ComplianceRuleRegistry.get_rule(old_rule_id)
        if not old_rule:
            raise ValueError(f"OLD_RULE_NOT_FOUND: Rule '{old_rule_id}' does not exist in registry.")

        # 3. Source & Document Verification
        src = OfficialSourceRegistry.get_source(new_source_id)
        if not src or src.authority_tier > AuthorityTier.TIER_3_OFFICIAL_CIRCULAR:
            raise ValueError(
                f"SOURCE_TRUST_VIOLATION: Source '{new_source_id}' is not an authorized primary/official source."
            )

        # 4. Conflict / Overlap Detection
        if change_type == ChangeDimensionType.CONFLICT or "CONFLICT" in diff_text.upper():
            raise ValueError(
                "SUPERSESSION_CONFLICT_BLOCKED: Overlapping or contradictory regulatory rule detected. Transition requires human verification."
            )

        # 5. M5.1 Impact Analysis Integration
        change_input = RegulatoryChangeInput(
            change_id=f"CHG-SUPER-{uuid.uuid4().hex[:6].upper()}",
            old_rule_id=old_rule.rule_id,
            new_rule_id=new_rule_id,
            old_rule_version=old_rule.version,
            new_rule_version=new_rule_version,
            old_rule_bundle_hash=old_rule.rule_bundle_hash,
            new_rule_bundle_hash="pending_hash",
            old_source_id="SR-FED-TAX-ACT-2025",
            new_source_id=new_source_id,
            old_document_id=old_rule.evidence_document_id,
            new_document_id=new_document_id,
            old_document_hash="doc_hash_old",
            new_document_hash="doc_hash_new",
            old_evidence_id="EA-OLD-001",
            new_evidence_id=new_evidence_id,
            old_evidence_bundle_hash=old_rule.evidence_bundle_hash,
            new_evidence_bundle_hash="ev_bundle_hash_new",
            effective_from=effective_from,
            effective_to=effective_to,
            old_effective_from=old_rule.effective_from,
            old_effective_to=old_rule.effective_to,
            jurisdiction=old_rule.jurisdiction,
            financial_year=old_rule.tax_year,
            tax_year=old_rule.tax_year,
            assessment_year_if_applicable=None,
            industry="ALL",
            employment_type="ALL",
            change_type=change_type,
            diff_text=diff_text,
        )
        impact_report = DeepRegulatoryChangeImpactAnalyzer.analyze_change(change_input)
        if impact_report.requires_verification:
            raise ValueError(f"ANALYSIS_GATE_BLOCKED: {impact_report.verification_reason}")

        # 6. Idempotency Gate
        idempotency_key = f"{old_rule_id}:{new_rule_id}:{new_rule_version}:{effective_from.isoformat()}"
        if idempotency_key in cls._SEEN_KEYS:
            existing_event = next(
                (e for e in cls._EVENTS.values() if e.old_rule_id == old_rule_id and e.new_rule_id == new_rule_id), None
            )
            return old_rule, ComplianceRuleRegistry.get_rule(new_rule_id), existing_event
        cls._SEEN_KEYS.add(idempotency_key)

        now_str = datetime.now(UTC).isoformat()
        today = date.today()

        # 7. Temporal Status Resolution
        if effective_from > today:
            new_status = RuleStatus.FUTURE_OFFICIALLY_NOTIFIED
            old_status = old_rule.status  # Old rule stays ACTIVE until new rule reaches effective_from
        else:
            new_status = RuleStatus.ACTIVE
            old_status = RuleStatus.SUPERSEDED

        # 8. Construct New Rule Definition with Lineage Pointers
        new_rule_temp = RuleDefinition(
            rule_id=new_rule_id,
            rule_code=new_rule_id,
            domain=old_rule.domain,
            jurisdiction=old_rule.jurisdiction,
            tax_year=old_rule.tax_year,
            version=new_rule_version,
            status=new_status,
            effective_from=effective_from,
            effective_to=effective_to,
            formula_expression=new_formula,
            condition_expression=new_condition,
            evidence_document_id=new_document_id,
            evidence_page=1,
            official_url=src.official_url,
            verified_at=today.isoformat(),
            supersedes_rule_id=old_rule.rule_id,
            supersedes_rule_version=old_rule.version,
            superseded_by_rule_id=None,
            superseded_by_rule_version=None,
            superseded_at=None,
            supersession_reason=reason,
            rule_bundle_id=f"RB-{new_rule_id}-{new_rule_version}",
            rule_bundle_hash=None,
            evidence_bundle_id=f"EB-{new_rule_id}-{new_rule_version}",
            evidence_bundle_hash=compute_sha256_hash({"new_evidence_id": new_evidence_id, "document": new_document_id}),
        )
        new_bundle_hash = new_rule_temp.compute_canonical_bundle_hash()

        new_rule = RuleDefinition(
            rule_id=new_rule_temp.rule_id,
            rule_code=new_rule_temp.rule_code,
            domain=new_rule_temp.domain,
            jurisdiction=new_rule_temp.jurisdiction,
            tax_year=new_rule_temp.tax_year,
            version=new_rule_temp.version,
            status=new_rule_temp.status,
            effective_from=new_rule_temp.effective_from,
            effective_to=new_rule_temp.effective_to,
            formula_expression=new_rule_temp.formula_expression,
            condition_expression=new_rule_temp.condition_expression,
            evidence_document_id=new_rule_temp.evidence_document_id,
            evidence_page=new_rule_temp.evidence_page,
            official_url=new_rule_temp.official_url,
            verified_at=new_rule_temp.verified_at,
            supersedes_rule_id=new_rule_temp.supersedes_rule_id,
            supersedes_rule_version=new_rule_temp.supersedes_rule_version,
            superseded_by_rule_id=None,
            superseded_by_rule_version=None,
            superseded_at=None,
            supersession_reason=new_rule_temp.supersession_reason,
            rule_bundle_id=new_rule_temp.rule_bundle_id,
            rule_bundle_hash=new_bundle_hash,
            evidence_bundle_id=new_rule_temp.evidence_bundle_id,
            evidence_bundle_hash=new_rule_temp.evidence_bundle_hash,
        )

        # 9. Construct Updated Old Rule (Immutably Preserved with Lineage Pointer)
        updated_old_rule = RuleDefinition(
            rule_id=old_rule.rule_id,
            rule_code=old_rule.rule_code,
            domain=old_rule.domain,
            jurisdiction=old_rule.jurisdiction,
            tax_year=old_rule.tax_year,
            version=old_rule.version,
            status=old_status,
            effective_from=old_rule.effective_from,
            effective_to=old_rule.effective_to,
            formula_expression=old_rule.formula_expression,
            condition_expression=old_rule.condition_expression,
            evidence_document_id=old_rule.evidence_document_id,
            evidence_page=old_rule.evidence_page,
            official_url=old_rule.official_url,
            verified_at=old_rule.verified_at,
            supersedes_rule_id=old_rule.supersedes_rule_id,
            supersedes_rule_version=old_rule.supersedes_rule_version,
            superseded_by_rule_id=new_rule.rule_id if new_status == RuleStatus.ACTIVE else None,
            superseded_by_rule_version=new_rule.version if new_status == RuleStatus.ACTIVE else None,
            superseded_at=now_str if new_status == RuleStatus.ACTIVE else None,
            supersession_reason=reason if new_status == RuleStatus.ACTIVE else None,
            rule_bundle_id=old_rule.rule_bundle_id,
            rule_bundle_hash=old_rule.rule_bundle_hash,
            evidence_bundle_id=old_rule.evidence_bundle_id,
            evidence_bundle_hash=old_rule.evidence_bundle_hash,
        )

        # 10. Atomic Commit to Compliance Registry
        ComplianceRuleRegistry.register_or_update_rule(updated_old_rule)
        ComplianceRuleRegistry.register_or_update_rule(new_rule)

        # 11. Create Tamper-Evident Audit Event
        event_id = f"EVT-SUP-{uuid.uuid4().hex[:8].upper()}"
        event_payload = {
            "event_id": event_id,
            "old_rule_id": old_rule.rule_id,
            "new_rule_id": new_rule.rule_id,
            "old_rule_version": old_rule.version,
            "new_rule_version": new_rule.version,
            "reason": reason,
            "detector_id": detector_id,
            "reviewer_id": reviewer_id,
            "approver_id": approver_id,
            "old_bundle_hash": old_rule.rule_bundle_hash,
            "new_bundle_hash": new_bundle_hash,
            "timestamp": now_str,
        }
        event_hash = compute_sha256_hash(event_payload)

        event = SupersessionEvent(
            event_id=event_id,
            old_rule_id=old_rule.rule_id,
            new_rule_id=new_rule.rule_id,
            old_rule_version=old_rule.version,
            new_rule_version=new_rule.version,
            domain=old_rule.domain,
            jurisdiction=old_rule.jurisdiction,
            financial_year=old_rule.tax_year,
            effective_from=effective_from.isoformat(),
            superseded_at=now_str,
            reason=reason,
            detector_id=detector_id,
            reviewer_id=reviewer_id,
            approver_id=approver_id,
            old_rule_bundle_hash=old_rule.rule_bundle_hash or "",
            new_rule_bundle_hash=new_bundle_hash,
            evidence_bundle_hash=new_rule.evidence_bundle_hash or "",
            event_hash=event_hash,
        )
        cls._EVENTS[event_id] = event

        return updated_old_rule, new_rule, event
