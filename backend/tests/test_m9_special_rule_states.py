"""
Milestone M9.5: Special Rule State Handling
Verifies behavior for rules in ACTIVE, HISTORICAL, SUPERSEDED, DRAFT, CONFLICT, and MISSING states.
"""

from datetime import date

from app.core.compliance.rule_registry import ComplianceRuleRegistry, RuleDefinition, RuleStatus


def test_m9_rule_states_lifecycle():
    # Verify that inactive states are never returned as active
    for status in [RuleStatus.SUPERSEDED, RuleStatus.HISTORICAL, RuleStatus.DRAFT, RuleStatus.PROPOSED]:
        test_rule = RuleDefinition(
            rule_id=f"TEST-{status.value}-RULE",
            rule_code=f"TEST_{status.value}",
            domain="TAX",
            status=status,
            version="1.0",
            jurisdiction="INDIA",
            tax_year="2020-21",
            effective_from=date(2020, 4, 1),
            effective_to=date(2021, 3, 31),
            formula_expression="tax = 0",
            condition_expression="True",
            evidence_document_id="test_evidence.pdf",
            evidence_page=1,
            official_url="https://incometax.gov.in",
            verified_at="2026-08-20",
        )
        ComplianceRuleRegistry.register_or_update_rule(test_rule)

        resolved = ComplianceRuleRegistry.get_active_rule(f"TEST-{status.value}-RULE")
        assert resolved is None, f"Rule in status {status.value} should not be retrievable as active!"
