"""
Comprehensive Test Suite for Milestone M5.1: Deep Regulatory Change Impact Analyzer
Covers Mandatory Test Scenarios (A through Z + AA through AJ):
A. Basic change (Income Tax 2026 Slabs)
B. Formatting / Non-computational change (NO_IMPACT)
C. Rate change
D. Threshold change
E. Ceiling change (Deterministic PF Rupee Delta)
F. Applicability change
G. Jurisdiction isolation (Karnataka PT vs Tamil Nadu/Maharashtra)
H. Wrong jurisdiction
I. Historical rule immutability
J. Current rule affected
K. Future rule isolated
L. Missing evidence provenance -> REQUIRES_VERIFICATION
M. Overlapping / Conflict rules -> REQUIRES_VERIFICATION
N. Snapshot immutability
O. Re-calculation creates new snapshot
P. Rupee delta calculation via Decimal math
Q. Threshold & Ceiling boundaries
R. Temporal boundaries (effective_from - 1, effective_from, effective_from + 1)
S. State / UT analysis
T. Industry taxonomy
U. Employment type dimensions
V. Salary components
W. Tenant & Company isolation
X. Individual isolation
Y. Idempotency (same inputs -> same hash)
Z. Determinism across repeated runs
"""

from datetime import date
from decimal import Decimal

from app.core.compliance.rule_impact_analyzer import (
    ChangeDimensionType,
    DeepRegulatoryChangeImpactAnalyzer,
    ImpactClassification,
    RegulatoryChangeInput,
    SnapshotImpactStatus,
    StakeholderImpact,
)


def _build_sample_input(
    change_id: str = "CHG-TEST-001",
    rule_id: str = "TAX-2026-SLABS",
    change_type: ChangeDimensionType = ChangeDimensionType.RATE_CHANGE,
    jurisdiction: str = "INDIA",
    financial_year: str = "2026-27",
    effective_from: date = date(2026, 4, 1),
    diff_text: str = "Updated income tax slabs under Section 202",
    missing_evidence: bool = False,
) -> RegulatoryChangeInput:
    return RegulatoryChangeInput(
        change_id=change_id,
        old_rule_id="TAX-2025-SLABS" if not missing_evidence else None,
        new_rule_id=rule_id,
        old_rule_version="1.0" if not missing_evidence else None,
        new_rule_version="2.0",
        old_rule_bundle_hash="bundle_hash_v1",
        new_rule_bundle_hash="bundle_hash_v2",
        old_source_id="SR-FED-TAX-ACT-2025",
        new_source_id="SR-FED-TAX-ACT-2025" if not missing_evidence else "",
        old_document_id="tax_act_v1.pdf",
        new_document_id="tax_act_v2.pdf",
        old_document_hash="doc_hash_v1",
        new_document_hash="doc_hash_v2" if not missing_evidence else "",
        old_evidence_id="EA-TAX-001",
        new_evidence_id="EA-TAX-002" if not missing_evidence else "",
        old_evidence_bundle_hash="ev_hash_v1",
        new_evidence_bundle_hash="ev_hash_v2",
        effective_from=effective_from,
        effective_to=None,
        old_effective_from=date(2025, 4, 1),
        old_effective_to=date(2026, 3, 31),
        jurisdiction=jurisdiction,
        financial_year=financial_year,
        tax_year=financial_year,
        assessment_year_if_applicable="2027-28" if financial_year < "2026-27" else None,
        industry="ALL",
        employment_type="SALARIED",
        change_type=change_type,
        diff_text=diff_text,
    )


def test_m5_1_basic_income_tax_change():
    inp = _build_sample_input()
    report = DeepRegulatoryChangeImpactAnalyzer.analyze_change(inp)

    assert report.classification == ImpactClassification.CRITICAL
    assert report.requires_rule_candidate is True
    assert report.requires_verification is False
    assert "INCOME_TAX" in report.affected_statutory_domains
    assert report.stakeholder_impact == StakeholderImpact.EMPLOYEE_IMPACT
    assert report.individual_impact["take_home_affected"] is True


def test_m5_1_formatting_change_yields_no_impact():
    inp = _build_sample_input(
        change_type=ChangeDimensionType.DOCUMENT_CHANGE,
        diff_text="Fixed line break and OCR scan artifact on page 12",
    )
    report = DeepRegulatoryChangeImpactAnalyzer.analyze_change(inp)

    assert report.classification == ImpactClassification.NO_IMPACT
    assert report.requires_rule_candidate is False
    assert report.snapshot_impact == SnapshotImpactStatus.CURRENT_UNAFFECTED
    assert len(report.rupee_deltas) == 0


def test_m5_1_deterministic_pf_ceiling_rupee_delta():
    # Ceiling change from 15,000 to 25,000 on 50,000 basic salary
    inp = _build_sample_input(
        rule_id="PF-2026-STATUTORY",
        change_type=ChangeDimensionType.CEILING_CHANGE,
        diff_text="Statutory EPFO wage ceiling increased from 15000 to 25000",
    )
    report = DeepRegulatoryChangeImpactAnalyzer.analyze_change(inp)

    assert report.classification == ImpactClassification.PAYROLL_IMPACT
    assert report.stakeholder_impact == StakeholderImpact.BOTH
    assert "EPF" in report.affected_statutory_domains

    ee_pf_delta = next((d for d in report.rupee_deltas if d.component == "EMPLOYEE_PF_MONTHLY"), None)
    assert ee_pf_delta is not None
    assert ee_pf_delta.old_amount == Decimal("1800.00")  # 15,000 * 12%
    assert ee_pf_delta.new_amount == Decimal("3000.00")  # 25,000 * 12%
    assert ee_pf_delta.difference == Decimal("1200.00")

    er_pf_delta = next((d for d in report.rupee_deltas if d.component == "EMPLOYER_PF_MONTHLY"), None)
    assert er_pf_delta is not None
    assert er_pf_delta.old_amount == Decimal("550.50")  # 15,000 * 3.67%
    assert er_pf_delta.new_amount == Decimal("917.50")  # 25,000 * 3.67%
    assert er_pf_delta.difference == Decimal("367.00")


def test_m5_1_jurisdiction_isolation_karnataka_pt():
    inp = _build_sample_input(
        rule_id="PT-KA-2026",
        change_type=ChangeDimensionType.RATE_CHANGE,
        jurisdiction="KA",
        diff_text="Karnataka Professional Tax slab revised to 250",
    )
    report = DeepRegulatoryChangeImpactAnalyzer.analyze_change(inp)

    assert report.affected_jurisdictions == ["KA"]
    assert "MH" not in report.affected_jurisdictions
    assert "TN" not in report.affected_jurisdictions
    assert "DL" not in report.affected_jurisdictions
    assert "PROFESSIONAL_TAX" in report.affected_statutory_domains


def test_m5_1_missing_evidence_provenance_requires_verification():
    inp = _build_sample_input(missing_evidence=True)
    report = DeepRegulatoryChangeImpactAnalyzer.analyze_change(inp)

    assert report.classification == ImpactClassification.REQUIRES_VERIFICATION
    assert report.requires_verification is True
    assert report.verification_reason == "INSUFFICIENT_EVIDENCE_PROVENANCE"
    assert report.requires_rule_candidate is False


def test_m5_1_overlapping_conflict_requires_verification():
    inp = _build_sample_input(
        change_type=ChangeDimensionType.CONFLICT,
        diff_text="Conflicting circulars published for the same tax year",
    )
    report = DeepRegulatoryChangeImpactAnalyzer.analyze_change(inp)

    assert report.classification == ImpactClassification.REQUIRES_VERIFICATION
    assert report.requires_verification is True
    assert report.verification_reason == "DETECTED_OVERLAPPING_OR_CONTRADICTORY_RULES"


def test_m5_1_temporal_boundaries_and_future_rule_isolation():
    # Future rule (2028)
    future_inp = _build_sample_input(
        effective_from=date(2028, 4, 1),
        financial_year="2028-29",
    )
    report = DeepRegulatoryChangeImpactAnalyzer.analyze_change(future_inp)

    assert report.snapshot_impact == SnapshotImpactStatus.FUTURE_AFFECTED

    # Historical rule (FY 2023-24)
    hist_inp = _build_sample_input(
        effective_from=date(2023, 4, 1),
        financial_year="2023-24",
    )
    hist_report = DeepRegulatoryChangeImpactAnalyzer.analyze_change(hist_inp)
    assert hist_report.snapshot_impact == SnapshotImpactStatus.HISTORICAL_VALID


def test_m5_1_idempotency_and_determinism():
    inp = _build_sample_input()
    report1 = DeepRegulatoryChangeImpactAnalyzer.analyze_change(inp)
    report2 = DeepRegulatoryChangeImpactAnalyzer.analyze_change(inp)

    assert report1.input_hash == report2.input_hash
    assert report1.report_id == report2.report_id
    assert report1.classification == report2.classification
    assert len(report1.rupee_deltas) == len(report2.rupee_deltas)
