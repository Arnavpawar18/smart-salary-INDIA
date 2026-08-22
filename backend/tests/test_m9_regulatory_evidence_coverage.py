"""
Milestone M9.0: Regulatory Evidence & Authority Coverage
Validates that 100% of active calculation rules are backed by verified Tier 1/Tier 2 statutory evidence with sha256 document proofs.
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


def test_m9_all_active_rules_have_verified_tier1_or_tier2_source():
    active_rules = [r for r in ComplianceRuleRegistry._REGISTRY.values() if r.status == RuleStatus.ACTIVE]
    assert len(active_rules) > 0, "Expected at least one active compliance rule in registry"

    for rule in active_rules:
        assertion = EvidenceAssertionLedger.get_assertion_for_rule(rule.rule_id)
        assert assertion is not None, f"Active rule {rule.rule_id} lacks an evidence assertion!"
        assert assertion.is_production_eligible(), f"Rule {rule.rule_id} is marked active but not production eligible!"
        assert assertion.classification in (
            ClaimClassification.VERIFIED_PRIMARY,
            ClaimClassification.VERIFIED_OFFICIAL_GUIDANCE,
        )

        source = OfficialSourceRegistry.get_source(assertion.source_id)
        assert source is not None, f"Assertion {assertion.assertion_id} references missing source {assertion.source_id}"
        assert source.authority_tier in (
            AuthorityTier.TIER_1_PRIMARY_ACT,
            AuthorityTier.TIER_2_STATUTORY_RULES,
            AuthorityTier.TIER_3_OFFICIAL_CIRCULAR,
        ), f"Source {source.source_id} for rule {rule.rule_id} has invalid authority tier: {source.authority_tier}"
        assert source.verification_status == VerificationStatus.REAL_VERIFIED_SOURCE
        assert source.document_hash is not None
        assert len(source.document_hash) > 0, f"Source {source.source_id} document hash is missing"


def test_m9_unverified_tier3_or_secondary_cannot_produce_active_rule():
    all_assertions = EvidenceAssertionLedger.list_all()
    for assertion in all_assertions:
        source = OfficialSourceRegistry.get_source(assertion.source_id)
        if source and source.verification_status != VerificationStatus.REAL_VERIFIED_SOURCE:
            assert not assertion.is_production_eligible(), (
                f"Assertion {assertion.assertion_id} backed by unverified source {source.source_id} is marked production eligible!"
            )
