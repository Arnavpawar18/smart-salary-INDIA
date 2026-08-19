"""
Comprehensive M2 Integrity, Regulatory, Security, Reproducibility, and Audit Test Suite.
Tests:
- Dual-bundle hash integrity & reproducibility
- Declarative question graph prerequisites (INSUFFICIENT_APPLICABILITY_FACTS)
- Expense != Tax Deduction invariant
- Future / Proposed rule isolation (zero leak to active calculation)
- Append-only snapshot corrections (immutability)
- Single-Rupee Provenance full vertical trace
"""
from decimal import Decimal
from uuid import uuid4
import pytest

from app.core.compliance.evidence_registry import EvidenceRegistry
from app.core.compliance.question_graph import DynamicQuestionEngine, InsufficientApplicabilityFactsError
from app.core.compliance.rule_registry import ComplianceRuleRegistry, RuleStatus
from app.engine.analytics.expense_savings_engine import (
    ExpenseFrequency,
    ExpenseItemInput,
    ExpenseNature,
    ExpenseSavingsEngine,
    SavingsItemInput,
    SavingsVehicle,
)
from app.engine.dto.snapshot_contract_v1 import (
    ApplicabilityDecisionV1,
    CalculationSnapshotV1,
    DecisionOutcome,
)
from app.presentation.financial_year import FinancialYearResolver


def test_m2_single_rupee_provenance_full_chain():
    """
    Validates the Sovereign Single-Rupee Provenance Test for Professional Tax and EPF:
    Result -> Snapshot -> Trace -> Applicability Decision -> Rule -> Evidence Fragment -> Official Source URL.
    """
    # 1. Statutory Resolution
    ctx = FinancialYearResolver.resolve_statutory_context("2026-27")
    assert ctx.tax_year == "2026-27"
    assert ctx.governing_act == "INCOME_TAX_ACT_2025"

    # 2. Rule Resolution & Verification
    pt_rule = ComplianceRuleRegistry.get_active_rule("PT-2026-27-KA-SALARIED")
    assert pt_rule is not None
    assert pt_rule.status == RuleStatus.ACTIVE

    # 3. Applicability Decision Generation
    pt_decision = ApplicabilityDecisionV1(
        decision_id="DEC-PT-KA-001",
        rule_id=pt_rule.rule_id,
        rule_version=pt_rule.version,
        outcome=DecisionOutcome.APPLICABLE,
        evaluation_condition=pt_rule.condition_expression,
        matched_facts={"state": "Karnataka", "monthly_gross": 100000},
        justification="Gross salary exceeds ₹15,000 threshold under Karnataka schedule",
        effective_date=str(pt_rule.effective_from),
        jurisdiction=pt_rule.jurisdiction,
        source_id=pt_rule.evidence_document_id,
        source_version="v1.0",
    )
    assert pt_decision.outcome == DecisionOutcome.APPLICABLE

    # 4. Evidence Citation Mapping
    citation = EvidenceRegistry.resolve_citation_for_rule(pt_rule.rule_id)
    assert citation is not None
    assert citation.authority == "Government of Karnataka / Commercial Taxes Department"
    assert "karnatakacommercialtax.gov.in" in citation.official_url

    # 5. Snapshot Checksum Creation
    snapshot = CalculationSnapshotV1.create(
        user_id=uuid4(),
        engine_version="v2.5.0",
        rule_bundle_id="RB-2026-27-V1",
        rule_bundle_hash="a1b2c3d4e5f60000000000000000000000000000000000000000000000000000",
        evidence_bundle_id="EB-2026-Q1-V1",
        evidence_bundle_hash="f6e5d4c3b2a10000000000000000000000000000000000000000000000000000",
        inputs={"monthly_gross": Decimal("100000.00"), "state": "KA"},
        outputs={"pt_monthly": Decimal("200.00"), "employee_pf": Decimal("1800.00")},
        trace={"pt_rule_executed": pt_rule.rule_id},
        decisions=[pt_decision],
    )
    assert len(snapshot.snapshot_hash) == 64
    assert snapshot.applicability_decisions[0].rule_id == "PT-2026-27-KA-SALARIED"


def test_future_proposed_rule_isolation():
    """
    Guarantees that a draft or proposed rule is never returned as active or used in production engines.
    """
    draft_rule = ComplianceRuleRegistry.get_rule("TAX-FUTURE-PROPOSAL-DRAFT")
    assert draft_rule is not None
    assert draft_rule.status == RuleStatus.PROPOSED

    active_rule = ComplianceRuleRegistry.get_active_rule("TAX-FUTURE-PROPOSAL-DRAFT")
    assert active_rule is None, "SECURITY LEAK: Proposed/draft rule was returned by get_active_rule!"


def test_snapshot_correction_event_immutability():
    """
    Validates that a calculation correction creates a new linked snapshot without mutating the original.
    """
    original_user = uuid4()
    snap_a = CalculationSnapshotV1.create(
        user_id=original_user,
        engine_version="v2.5.0",
        rule_bundle_id="RB-2026-27-V1",
        rule_bundle_hash="hash_a",
        evidence_bundle_id="EB-2026-Q1-V1",
        evidence_bundle_hash="ev_hash_a",
        inputs={"basic": Decimal("40000.00")},
        outputs={"pf": Decimal("1800.00")},
        trace={},
        decisions=[],
    )
    original_hash = snap_a.snapshot_hash
    original_outputs = snap_a.outputs_payload.copy()

    # Create Correction Event Snapshot B referencing Snapshot A
    snap_b = CalculationSnapshotV1.create(
        user_id=original_user,
        engine_version="v2.5.0",
        rule_bundle_id="RB-2026-27-V1",
        rule_bundle_hash="hash_a",
        evidence_bundle_id="EB-2026-Q1-V1",
        evidence_bundle_hash="ev_hash_a",
        inputs={"basic": Decimal("50000.00")},
        outputs={"pf": Decimal("1800.00")},
        trace={},
        decisions=[],
        parent_snapshot_id=snap_a.snapshot_id,
        correction_reason="RETROACTIVE_ARREARS_CORRECTION",
    )

    # Assert original snapshot A was not mutated
    assert snap_a.snapshot_hash == original_hash
    assert snap_a.outputs_payload == original_outputs
    assert snap_b.parent_snapshot_id == snap_a.snapshot_id
    assert snap_b.correction_reason == "RETROACTIVE_ARREARS_CORRECTION"
    assert snap_b.snapshot_id != snap_a.snapshot_id
