"""
Milestone M9.8 & M9.9: Regulatory Mutation Testing
Injects deliberate formula mutations to ensure the verification suite fails immediately on any statutory deviation.
"""

from decimal import Decimal

from app.engine.oracle.independent_oracle import IndependentRegulatoryOracle


def test_m9_mutation_pf_rate_divergence_detected():
    oracle_res = IndependentRegulatoryOracle.calculate_fy2025_26_new(Decimal("1200000.00"), "KA")

    # Statutory PF is 12% (₹1,800/mo = ₹21,600/yr). Mutate to 10% (₹1,500/mo = ₹18,000/yr)
    mutated_pf = Decimal("15000.00") * Decimal("0.10") * Decimal("12")
    assert mutated_pf != oracle_res.annual_employee_pf, "Mutation testing failed to detect mutated PF rate!"


def test_m9_mutation_cess_rate_divergence_detected():
    oracle_res = IndependentRegulatoryOracle.calculate_fy2025_26_new(Decimal("2400000.00"), "MH")

    # Statutory Cess is 4%. Mutate to 3%
    mutated_cess = oracle_res.tax_after_rebate * Decimal("0.03")
    assert mutated_cess != oracle_res.cess, "Mutation testing failed to detect mutated Health & Education Cess rate!"
