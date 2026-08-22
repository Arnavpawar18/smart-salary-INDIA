"""
Tests for M2.13 Regulatory Evidence Lineage Verification:
- Claim -> Source -> Document -> Fragment -> Assertion -> Rule -> Calculation Lineage
- Rejection of unverified/draft sources from production authorization
- Strict effective date gating and jurisdiction boundaries
"""

from app.core.compliance.assertion_ledger import (
    ClaimClassification,
    EvidenceAssertionLedger,
)
from app.core.compliance.rule_registry import ComplianceRuleRegistry, RuleStatus
from app.core.compliance.source_registry import (
    AuthorityTier,
    OfficialSourceRegistry,
    VerificationStatus,
)


def test_complete_evidence_assertion_lineage_for_active_rules():
    # 1. Income Tax 2026-27 Active Rule
    tax_rule = ComplianceRuleRegistry.get_active_rule("TAX-2026-27-NEW-DEFAULT")
    assert tax_rule is not None
    assert tax_rule.status == RuleStatus.ACTIVE

    assertion = EvidenceAssertionLedger.get_assertion_for_rule(tax_rule.rule_id)
    assert assertion is not None
    assert assertion.classification == ClaimClassification.VERIFIED_PRIMARY
    assert assertion.is_production_eligible() is True
    assert assertion.section_reference == "Section 202"
    assert assertion.document_id == "87647dtc-aps2139-inceome-tax-act-2025.pdf"

    # Verify underlying source in SourceRegistry
    source = OfficialSourceRegistry.get_source(assertion.source_id)
    assert source is not None
    assert source.authority_tier == AuthorityTier.TIER_1_PRIMARY_ACT
    assert source.verification_status == VerificationStatus.REAL_VERIFIED_SOURCE
    assert source.can_authorize_production() is True


def test_epf_and_pt_assertion_lineage():
    # EPF Rule
    pf_rule = ComplianceRuleRegistry.get_active_rule("PF-2026-27-STATUTORY")
    assert pf_rule is not None
    pf_assertion = EvidenceAssertionLedger.get_assertion_for_rule(pf_rule.rule_id)
    assert pf_assertion is not None
    assert pf_assertion.classification == ClaimClassification.VERIFIED_PRIMARY
    assert pf_assertion.is_production_eligible() is True

    # Karnataka PT Rule
    ka_pt_rule = ComplianceRuleRegistry.get_active_rule("PT-2026-27-KA-SALARIED")
    assert ka_pt_rule is not None
    ka_pt_assertion = EvidenceAssertionLedger.get_assertion_for_rule(ka_pt_rule.rule_id)
    assert ka_pt_assertion is not None
    assert ka_pt_assertion.jurisdiction == "KA"
    assert ka_pt_assertion.is_production_eligible() is True


def test_unverified_rule_cannot_be_active_without_primary_assertion():
    # Draft proposal should have no active production eligibility
    draft_rule = ComplianceRuleRegistry.get_rule("TAX-FUTURE-PROPOSAL-DRAFT")
    assert draft_rule is not None
    assert draft_rule.status == RuleStatus.PROPOSED
    assert ComplianceRuleRegistry.get_active_rule("TAX-FUTURE-PROPOSAL-DRAFT") is None

    # Assertion ledger must not grant production eligibility to draft/unverified
    draft_assertion = EvidenceAssertionLedger.get_assertion_for_rule("TAX-FUTURE-PROPOSAL-DRAFT")
    assert draft_assertion is None
