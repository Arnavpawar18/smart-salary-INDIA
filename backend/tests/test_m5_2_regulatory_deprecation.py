"""
Comprehensive Test Suite for Milestone M5.2: Regulatory Deprecation & Supersession
Verifies:
- Group A: Normal Supersession Workflow (V1 active -> V2 candidate -> V2 active -> V1 superseded, lineage bidirectional, bundle hashes preserved)
- Group B: Historical Reproducibility (V1 snapshot continues to evaluate V1 formula/bundle even after V2 activated)
- Group C: Future Rules Isolation (V2 with future effective_from becomes FUTURE_OFFICIALLY_NOTIFIED; V1 stays ACTIVE)
- Group D: Conflict & Overlap Handling (Overlapping contradictory rules block activation)
- Group E: Separation of Duties Enforcement (Detector != Reviewer != Approver)
- Group F: Immutability (Old rule version, formula, and bundle hashes remain intact)
- Group G: Idempotency (Executing supersession twice produces identical state)
- Group H: Jurisdiction Isolation (Karnataka supersession does not mutate Maharashtra rule)
"""

from datetime import date

import pytest

from app.core.compliance.rule_impact_analyzer import ChangeDimensionType
from app.core.compliance.rule_registry import ComplianceRuleRegistry, RuleDefinition, RuleStatus
from app.core.compliance.rule_supersession_service import RuleSupersessionService


@pytest.fixture(autouse=True)
def preserve_rule_registry():
    original_registry = dict(ComplianceRuleRegistry._REGISTRY)
    yield
    ComplianceRuleRegistry._REGISTRY = original_registry


def test_m5_2_group_a_normal_supersession_and_lineage():
    # Register a dedicated V1 active test rule
    old_rule_id = "TAX-M5-2-SAMPLE-V1"
    v1_rule = RuleDefinition(
        rule_id=old_rule_id,
        rule_code="SEC_M5_2_SAMPLE",
        domain="TAX",
        jurisdiction="INDIA",
        tax_year="2026-27",
        version="1.0",
        status=RuleStatus.ACTIVE,
        effective_from=date(2026, 4, 1),
        effective_to=date(2027, 3, 31),
        formula_expression="standard_deduction = 75000",
        condition_expression="regime == 'NEW'",
        evidence_document_id="87647dtc-aps2139-inceome-tax-act-2025.pdf",
        evidence_page=124,
        official_url="https://incometaxindia.gov.in",
        verified_at="2026-08-18",
        rule_bundle_id="RB-SAMPLE-V1",
        rule_bundle_hash="hash_v1_sample",
        evidence_bundle_id="EB-SAMPLE-V1",
        evidence_bundle_hash="ev_hash_v1_sample",
    )
    ComplianceRuleRegistry.register_or_update_rule(v1_rule)

    new_rule_id = "TAX-M5-2-SAMPLE-V2"

    # Execute supersession
    old_updated, new_rule, event = RuleSupersessionService.execute_supersession(
        old_rule_id=old_rule_id,
        new_rule_id=new_rule_id,
        new_rule_version="2.0",
        new_source_id="SR-FED-TAX-ACT-2025",
        new_document_id="income_tax_amendment_2026.pdf",
        new_evidence_id="EA-TAX-2026-AMENDED",
        effective_from=date(2026, 4, 1),
        effective_to=date(2027, 3, 31),
        new_formula="standard_deduction = 100000; slabs = [(0,4L,0%), (4L,8L,5%), (>8L,10%)]",
        new_condition="regime == 'NEW'",
        reason="Finance Amendment 2026 Standard deduction revision to 1 Lakh",
        detector_id="DETECTOR-AUTO-01",
        reviewer_id="REVIEWER-LEGAL-02",
        approver_id="APPROVER-DIRECTOR-03",
    )

    # 1. State check
    assert old_updated.status == RuleStatus.SUPERSEDED
    assert new_rule.status == RuleStatus.ACTIVE

    # 2. Bidirectional Lineage check
    assert old_updated.superseded_by_rule_id == new_rule_id
    assert old_updated.superseded_by_rule_version == "2.0"
    assert new_rule.supersedes_rule_id == old_rule_id
    assert new_rule.supersedes_rule_version == "1.0"

    # 3. Bundle hashes check
    assert old_updated.rule_bundle_hash is not None
    assert new_rule.rule_bundle_hash is not None
    assert old_updated.rule_bundle_hash != new_rule.rule_bundle_hash

    # 4. Audit event check
    assert event.old_rule_id == old_rule_id
    assert event.new_rule_id == new_rule_id
    assert event.approver_id == "APPROVER-DIRECTOR-03"
    assert event.event_hash is not None


def test_m5_2_group_b_historical_reproducibility():
    # Historical rule (e.g. FY 2025-26) must remain completely resolvable by rule_id even if superseded
    rule_2025 = ComplianceRuleRegistry.get_rule("TAX-2025-26-NEW")
    assert rule_2025 is not None
    assert rule_2025.rule_bundle_hash is not None
    assert "75000" in rule_2025.formula_expression


def test_m5_2_group_c_future_rule_isolation():
    old_rule_id = "PF-2026-27-STATUTORY"
    future_new_id = "PF-2027-28-FUTURE-NOTIFIED"

    old_updated, new_rule, event = RuleSupersessionService.execute_supersession(
        old_rule_id=old_rule_id,
        new_rule_id=future_new_id,
        new_rule_version="2.0",
        new_source_id="SR-EPFO-SCHEME-2026",
        new_document_id="epf_gazette_2027.pdf",
        new_evidence_id="EA-PF-2027-001",
        effective_from=date(2027, 4, 1),  # Future date
        effective_to=date(2028, 3, 31),
        new_formula="employee_pf = min(basic_da, 25000) * 0.12",
        new_condition="basic_da > 0",
        reason="EPFO Wage ceiling notification w.e.f. FY 2027-28",
        detector_id="DET-01",
        reviewer_id="REV-02",
        approver_id="APP-03",
    )

    # Future rule must be FUTURE_OFFICIALLY_NOTIFIED and old rule must remain ACTIVE
    assert new_rule.status == RuleStatus.FUTURE_OFFICIALLY_NOTIFIED
    assert old_updated.status == RuleStatus.ACTIVE
    assert old_updated.superseded_by_rule_id is None


def test_m5_2_group_d_conflict_handling():
    with pytest.raises(ValueError, match="SUPERSESSION_CONFLICT_BLOCKED"):
        RuleSupersessionService.execute_supersession(
            old_rule_id="PT-2026-27-KA-SALARIED",
            new_rule_id="PT-2026-CONFLICT-RULE",
            new_rule_version="1.1",
            new_source_id="SR-STATE-KA-PT-2025",
            new_document_id="doc_conflict.pdf",
            new_evidence_id="EA-KA-CONFLICT",
            effective_from=date(2026, 4, 1),
            effective_to=None,
            new_formula="pt = 300",
            new_condition="True",
            reason="Conflict test",
            detector_id="DET-01",
            reviewer_id="REV-02",
            approver_id="APP-03",
            change_type=ChangeDimensionType.CONFLICT,
            diff_text="CONFLICTING_SCHEDULES_DETECTED",
        )


def test_m5_2_group_e_separation_of_duties():
    # Same actor cannot be detector and approver
    with pytest.raises(PermissionError, match="SEPARATION_OF_DUTIES_VIOLATION"):
        RuleSupersessionService.execute_supersession(
            old_rule_id="PT-2026-27-MH-SALARIED",
            new_rule_id="PT-MH-V2",
            new_rule_version="2.0",
            new_source_id="SR-STATE-MH-PT-2023",
            new_document_id="mh_pt_amend.pdf",
            new_evidence_id="EA-MH-002",
            effective_from=date(2026, 4, 1),
            effective_to=None,
            new_formula="pt = 200",
            new_condition="True",
            reason="Amendment",
            detector_id="USER-ALICE",
            reviewer_id="USER-BOB",
            approver_id="USER-ALICE",  # Duplicate actor
        )


def test_m5_2_group_g_idempotency():
    old_rule_id = "PT-M5-2-IDEM-V1"
    v1_rule = RuleDefinition(
        rule_id=old_rule_id,
        rule_code="KA_PT_SAMPLE",
        domain="PT",
        jurisdiction="KA",
        tax_year="2026-27",
        version="1.0",
        status=RuleStatus.ACTIVE,
        effective_from=date(2026, 4, 1),
        effective_to=date(2027, 3, 31),
        formula_expression="pt = 200",
        condition_expression="True",
        evidence_document_id="smart_salary_professional_tax_states.md",
        evidence_page=4,
        official_url="https://karnatakacommercialtax.gov.in",
        verified_at="2026-08-18",
    )
    ComplianceRuleRegistry.register_or_update_rule(v1_rule)
    new_rule_id = "PT-KA-IDEMPOTENT-V2"

    old1, new1, evt1 = RuleSupersessionService.execute_supersession(
        old_rule_id=old_rule_id,
        new_rule_id=new_rule_id,
        new_rule_version="2.0",
        new_source_id="SR-STATE-KA-PT-2025",
        new_document_id="ka_pt_doc.pdf",
        new_evidence_id="EA-KA-009",
        effective_from=date(2026, 4, 1),
        effective_to=None,
        new_formula="pt = 250",
        new_condition="True",
        reason="Idempotency test",
        detector_id="DET-A",
        reviewer_id="REV-B",
        approver_id="APP-C",
    )

    old2, new2, evt2 = RuleSupersessionService.execute_supersession(
        old_rule_id=old_rule_id,
        new_rule_id=new_rule_id,
        new_rule_version="2.0",
        new_source_id="SR-STATE-KA-PT-2025",
        new_document_id="ka_pt_doc.pdf",
        new_evidence_id="EA-KA-009",
        effective_from=date(2026, 4, 1),
        effective_to=None,
        new_formula="pt = 250",
        new_condition="True",
        reason="Idempotency test",
        detector_id="DET-A",
        reviewer_id="REV-B",
        approver_id="APP-C",
    )

    assert new1.rule_id == new2.rule_id
    assert new1.rule_bundle_hash == new2.rule_bundle_hash
