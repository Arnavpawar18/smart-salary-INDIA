"""
Tests for Question Graph Declarative Dependency Engine and Snapshot Contract V1
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.compliance.question_graph import (
    DynamicQuestionEngine,
    InsufficientApplicabilityFactsError,
)
from app.engine.dto.snapshot_contract_v1 import (
    ApplicabilityDecisionV1,
    CalculationSnapshotV1,
    DecisionOutcome,
)


def test_question_graph_applicability_and_mandatory_validation():
    # Scenario 1: New Regime - Old regime questions should NOT be applicable
    new_regime_facts = {
        "tax_regime": "NEW",
        "hra_received": 200000,
        "basic_salary_monthly": 40000,
    }
    questions_new = DynamicQuestionEngine.get_applicable_questions(new_regime_facts)
    question_ids_new = [q.question_id for q in questions_new]
    assert "Q_RENT_PAID_ANNUAL" not in question_ids_new
    assert "Q_HRA_METRO_CITY" not in question_ids_new
    assert "Q_PF_OPT_IN_HIGHER_WAGE" in question_ids_new

    # Should pass validation with no missing facts
    DynamicQuestionEngine.validate_facts_sufficiency(new_regime_facts)

    # Scenario 2: Old Regime with HRA received - rent_paid_annual is mandatory
    old_regime_facts = {
        "tax_regime": "OLD",
        "hra_received": 150000,
    }
    questions_old = DynamicQuestionEngine.get_applicable_questions(old_regime_facts)
    question_ids_old = [q.question_id for q in questions_old]
    assert "Q_RENT_PAID_ANNUAL" in question_ids_old

    # Must raise InsufficientApplicabilityFactsError when rent_paid_annual is missing
    with pytest.raises(InsufficientApplicabilityFactsError) as exc_info:
        DynamicQuestionEngine.validate_facts_sufficiency(old_regime_facts)
    assert "Q_RENT_PAID_ANNUAL" in exc_info.value.missing_question_ids

    # Provide the mandatory fact and assert it now satisfies prerequisites
    old_regime_facts["rent_paid_annual"] = 180000
    questions_after_rent = DynamicQuestionEngine.get_applicable_questions(old_regime_facts)
    assert "Q_HRA_METRO_CITY" in [q.question_id for q in questions_after_rent]


def test_snapshot_contract_v1_dual_bundle_hash_and_immutability():
    user_id = uuid4()
    decision = ApplicabilityDecisionV1(
        decision_id="DEC-PT-KA-001",
        rule_id="PT-2026-27-KA-SALARIED",
        rule_version="v1.0",
        outcome=DecisionOutcome.APPLICABLE,
        evaluation_condition="state == 'Karnataka' and gross >= 15000",
        matched_facts={"state": "Karnataka", "gross": 100000},
        justification="Gross salary exceeds Karnataka statutory PT threshold of ₹15,000",
        effective_date="2026-04-01",
        jurisdiction="KA",
        source_id="smart_salary_professional_tax_states.md",
        source_version="v2.0",
    )

    snapshot = CalculationSnapshotV1.create(
        user_id=user_id,
        engine_version="v2.5.0",
        rule_bundle_id="RB-AY-2026-27-CENTRAL-V1",
        rule_bundle_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        evidence_bundle_id="EB-STATUTORY-IN-2026-Q1",
        evidence_bundle_hash="5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
        inputs={"basic": Decimal("50000.00"), "regime": "NEW"},
        outputs={"net_take_home": Decimal("98000.00"), "pt": Decimal("200.00")},
        trace={"steps": 4},
        decisions=[decision],
    )

    assert snapshot.schema_version == "v1.0.0"
    assert len(snapshot.snapshot_hash) == 64
    assert snapshot.rule_bundle_id == "RB-AY-2026-27-CENTRAL-V1"
    assert snapshot.evidence_bundle_id == "EB-STATUTORY-IN-2026-Q1"
    assert len(snapshot.applicability_decisions) == 1
    assert snapshot.applicability_decisions[0].outcome == DecisionOutcome.APPLICABLE

    # Verify dictionary serialization preserves canonical types
    snap_dict = snapshot.to_dict()
    assert snap_dict["snapshot_hash"] == snapshot.snapshot_hash
    assert snap_dict["applicability_decisions"][0]["decision_id"] == "DEC-PT-KA-001"
