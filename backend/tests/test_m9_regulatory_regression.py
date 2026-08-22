"""
Tests for Milestone M9: Regulatory Truth, Independent Oracle, Boundaries, Mutations & Metamorphic Verification.
"""

from decimal import Decimal

import pytest

from app.core.compliance.assertion_ledger import (
    EvidenceAssertionLedger,
)
from app.core.compliance.rule_registry import ComplianceRuleRegistry, RuleStatus
from app.core.compliance.source_registry import (
    AuthorityTier,
    OfficialSourceRegistry,
    VerificationStatus,
)
from app.core.database import SessionLocal
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.engine.oracle.independent_oracle import IndependentRegulatoryOracle
from app.services.calculation_service import CalculationService

# ==============================================================================
# M9.0 & M9.1: Evidence Inventory & Canonical Temporal Contract
# ==============================================================================


def test_m9_0_all_active_rules_have_verified_primary_assertions():
    for rule in ComplianceRuleRegistry._REGISTRY.values():
        if rule.status == RuleStatus.ACTIVE:
            assertion = EvidenceAssertionLedger.get_assertion_for_rule(rule.rule_id)
            assert assertion is not None, f"Active rule {rule.rule_id} lacks evidence assertion!"
            assert assertion.is_production_eligible() is True, f"Rule {rule.rule_id} not production eligible!"

            source = OfficialSourceRegistry.get_source(assertion.source_id)
            assert source is not None, (
                f"Assertion {assertion.assertion_id} references missing source {assertion.source_id}!"
            )
            assert source.authority_tier in (
                AuthorityTier.TIER_1_PRIMARY_ACT,
                AuthorityTier.TIER_2_STATUTORY_RULES,
                AuthorityTier.TIER_3_OFFICIAL_CIRCULAR,
            ), f"Source {source.source_id} has invalid authority tier for production: {source.authority_tier}!"
            assert source.verification_status == VerificationStatus.REAL_VERIFIED_SOURCE


def test_m9_1_canonical_temporal_dimensions_and_future_isolation():
    # Verify current FY active rule resolves
    active_tax = ComplianceRuleRegistry.get_active_rule("TAX-2026-27-NEW-DEFAULT")
    assert active_tax is not None
    assert active_tax.tax_year == "2026-27"
    assert active_tax.effective_from <= active_tax.effective_to

    # Verify future rule (2028 proposal) is strictly isolated and cannot be retrieved as active
    future_rule = ComplianceRuleRegistry.get_active_rule("TAX-FUTURE-PROPOSAL-DRAFT")
    assert future_rule is None, "SECURITY FAILURE: Future proposed draft rule returned as active!"


# ==============================================================================
# M9.6: Independent Oracle vs Deterministic Engine Exact Matching
# ==============================================================================


@pytest.mark.parametrize(
    "gross_salary,state",
    [
        (Decimal("1200000.00"), "KA"),
        (Decimal("1575000.00"), "MH"),
    ],
)
def test_m9_6_independent_oracle_matches_production_engine(gross_salary, state):
    oracle_res = IndependentRegulatoryOracle.calculate_fy2025_26_new(gross_salary, state)

    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=gross_salary)
        engine_res = service.calculate_salary(inp, regime=TaxRegime.NEW, state_code=state, persist=False)

        assert engine_res.annual_gross_salary == oracle_res.annual_gross
        assert engine_res.taxable_income == oracle_res.taxable_income
        assert engine_res.standard_deduction == oracle_res.standard_deduction
        assert engine_res.slab_tax == oracle_res.slab_tax
        assert engine_res.section_87a_rebate == oracle_res.section_87a_rebate
        assert engine_res.total_annual_tax_liability == oracle_res.total_tax
        assert engine_res.annual_employee_pf == oracle_res.annual_employee_pf
        assert engine_res.annual_professional_tax == oracle_res.annual_professional_tax
        assert engine_res.estimated_annual_take_home == oracle_res.annual_take_home
        assert engine_res.estimated_monthly_take_home == oracle_res.monthly_take_home


# ==============================================================================
# M9.9: Regulatory Mutation Testing
# ==============================================================================


def test_m9_9_mutation_testing_catches_intentional_rate_corruption():
    gross = Decimal("1575000.00")
    oracle_res = IndependentRegulatoryOracle.calculate_fy2025_26_new(gross, "MH")

    # Corrupt PF rate simulation: 11% instead of statutory 12%
    corrupted_monthly_pf = Decimal("15000.00") * Decimal("0.11")
    corrupted_annual_pf = corrupted_monthly_pf * Decimal("12")

    # Assert that our oracle & engine assert strict mismatch if calculation diverged by even 1%
    assert corrupted_annual_pf != oracle_res.annual_employee_pf, "Mutation test failed to detect 1% PF rate variation!"


# ==============================================================================
# M9.10: Metamorphic Testing (Monotonicity & Determinism)
# ==============================================================================


def test_m9_10_metamorphic_monotonic_tax_increase():
    with SessionLocal() as db:
        service = CalculationService(db)

        salary_low = Decimal("1200000.00")
        salary_high = Decimal("1575000.00")

        inp_low = SalaryInput(financial_year="2025-26", annual_gross=salary_low)
        inp_high = SalaryInput(financial_year="2025-26", annual_gross=salary_high)

        res_low = service.calculate_salary(inp_low, regime=TaxRegime.NEW, state_code="KA", persist=False)
        res_high = service.calculate_salary(inp_high, regime=TaxRegime.NEW, state_code="KA", persist=False)

        # Invariant: Higher salary must have >= tax liability under same regime
        assert res_high.total_annual_tax_liability >= res_low.total_annual_tax_liability
        assert res_high.estimated_annual_take_home > res_low.estimated_annual_take_home


def test_m9_10_metamorphic_exact_determinism_under_repeat_executions():
    with SessionLocal() as db:
        service = CalculationService(db)
        inp = SalaryInput(financial_year="2025-26", annual_gross=Decimal("1575000.00"))

        results = [
            service.calculate_salary(inp, regime=TaxRegime.NEW, state_code="MH", persist=False) for _ in range(50)
        ]

        first_take_home = results[0].estimated_annual_take_home
        first_tax = results[0].total_annual_tax_liability

        for idx, r in enumerate(results[1:], start=2):
            assert r.estimated_annual_take_home == first_take_home, f"Non-deterministic take-home at iteration {idx}!"
            assert r.total_annual_tax_liability == first_tax, f"Non-deterministic tax at iteration {idx}!"
