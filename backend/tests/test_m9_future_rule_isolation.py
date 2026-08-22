"""
Milestone M9.5 / Future Rule Isolation:
Ensures that proposed or draft future rules cannot leak into active production calculations.
"""

from app.core.compliance.rule_registry import ComplianceRuleRegistry, RuleStatus


def test_m9_future_draft_rules_are_isolated_from_active_registry():
    for rule_id, rule in ComplianceRuleRegistry._REGISTRY.items():
        if "FUTURE" in rule_id or "DRAFT" in rule_id or "PROPOSAL" in rule_id:
            assert rule.status != RuleStatus.ACTIVE, (
                f"Security violation: Draft/future rule {rule_id} is marked ACTIVE!"
            )

    active_rule = ComplianceRuleRegistry.get_active_rule("TAX-FUTURE-PROPOSAL-DRAFT")
    assert active_rule is None, "Future proposal draft rule was incorrectly returned by get_active_rule!"
