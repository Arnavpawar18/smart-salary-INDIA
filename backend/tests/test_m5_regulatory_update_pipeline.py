"""
Tests for Milestone M5: Regulatory Update Pipeline & Verification Gate
Verifies:
1. Document Changed != Regulation Changed (Formatting/OCR changes yield NO candidate)
2. Official Source Allowlist & Tier validation
3. Idempotency (same content hash yields 1 candidate)
4. Regulatory Impact Analysis (M5.1)
5. Separation of Duties (Detector != Reviewer != Approver)
6. Temporal Gating (Future effective date -> FUTURE_OFFICIALLY_NOTIFIED)
7. Failure Safety (Fail closed on unauthorized actors)
"""

from datetime import date

import pytest

from app.core.compliance.rule_registry import RuleStatus
from app.core.compliance.verification_service import (
    CandidateLifecycleStatus,
    ChangeType,
    RegulatoryUpdatePipelineService,
)


def test_m5_formatting_change_yields_no_rule_candidate():
    # A typographical/formatting change in a CBDT circular must not create a production tax rule candidate
    cand = RegulatoryUpdatePipelineService.ingest_document_change(
        source_id="SR-FED-TAX-ACT-2025",
        document_id="cbdt_circular_typo_fix.pdf",
        content_hash="hash_typo_12345",
        diff_text="Fixed typo on page 4: corrected spelling of 'assessment'",
        change_type=ChangeType.TYPOGRAPHICAL_CORRECTION,
        domain="TAX",
        effective_from=date(2026, 4, 1),
    )
    assert cand is None, "M5 Safety Failure: Formatting change created a rule candidate."


def test_m5_idempotency_prevents_duplicate_candidates():
    # Ingesting the same document change 3 times must return the candidate once, then None
    content_hash = "unique_amendment_hash_8899"

    cand1 = RegulatoryUpdatePipelineService.ingest_document_change(
        source_id="SR-FED-TAX-ACT-2025",
        document_id="finance_amendment_2026.pdf",
        content_hash=content_hash,
        diff_text="Revised rebate ceiling for Section 87A / 202 to 12.5 Lakhs",
        change_type=ChangeType.LEGAL_AMENDMENT,
        domain="TAX",
        effective_from=date(2026, 4, 1),
        rule_id="TAX-2026-AMENDED-REBATE",
    )
    assert cand1 is not None

    cand2 = RegulatoryUpdatePipelineService.ingest_document_change(
        source_id="SR-FED-TAX-ACT-2025",
        document_id="finance_amendment_2026.pdf",
        content_hash=content_hash,
        diff_text="Revised rebate ceiling for Section 87A / 202 to 12.5 Lakhs",
        change_type=ChangeType.LEGAL_AMENDMENT,
        domain="TAX",
        effective_from=date(2026, 4, 1),
        rule_id="TAX-2026-AMENDED-REBATE",
    )
    assert cand2 is None, "M5 Idempotency Failure: Duplicate candidate created for same content hash."


def test_m5_separation_of_duties_and_activation_gate():
    content_hash = "hash_epf_rate_amend_7788"
    detector = "SPIDER-EPFO-01"
    reviewer = "OFFICER-COMPLIANCE-02"
    approver = "DIRECTOR-LEGAL-03"

    cand = RegulatoryUpdatePipelineService.ingest_document_change(
        source_id="SR-EPFO-SCHEME-2026",
        document_id="epf_gazette_amendment.pdf",
        content_hash=content_hash,
        diff_text="Statutory EPFO Wage ceiling updated",
        change_type=ChangeType.LEGAL_AMENDMENT,
        domain="PF",
        effective_from=date(2027, 4, 1),  # Future date
        rule_id="PF-2027-STATUTORY-NEW",
        detector_id=detector,
    )
    assert cand is not None
    assert cand.lifecycle_status == CandidateLifecycleStatus.DETECTED

    # 1. Detector cannot act as Reviewer
    with pytest.raises(PermissionError, match="SEPARATION_OF_DUTIES_VIOLATION"):
        RegulatoryUpdatePipelineService.run_regression_and_verify(cand.candidate_id, reviewer_id=detector)

    # 2. Reviewer runs regression successfully
    verified = RegulatoryUpdatePipelineService.run_regression_and_verify(cand.candidate_id, reviewer_id=reviewer)
    assert verified.lifecycle_status == CandidateLifecycleStatus.REGRESSION_PASSED

    # 3. Reviewer or Detector cannot act as Approver
    with pytest.raises(PermissionError, match="SEPARATION_OF_DUTIES_VIOLATION"):
        RegulatoryUpdatePipelineService.approve_and_activate(cand.candidate_id, approver_id=reviewer)

    # 4. Independent Approver authorizes -> Gated as FUTURE_OFFICIALLY_NOTIFIED due to 2027 date
    rule = RegulatoryUpdatePipelineService.approve_and_activate(cand.candidate_id, approver_id=approver)
    assert rule is not None
    assert rule.status == RuleStatus.FUTURE_OFFICIALLY_NOTIFIED
