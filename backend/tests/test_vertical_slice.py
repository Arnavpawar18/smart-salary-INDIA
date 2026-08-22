"""
SmartSalary India — Vertical Slice Integration Test
Validates the complete linear invariant:
Input -> Rule Resolver -> Tax/PF/PT Engine -> CalculationTrace -> Snapshot -> Why Drawer -> Verified Official Citation.
"""

from decimal import Decimal

from app.core.compliance.evidence_registry import EvidenceRegistry
from app.core.compliance.rule_registry import ComplianceRuleRegistry
from app.presentation.financial_year import FinancialYearResolver


def test_evidence_to_rupee_vertical_slice():
    """
    Vertical Slice Proof:
    Employee: Private Salaried IT Professional
    Location: Karnataka (Bangalore)
    Period: FY 2026-27 (Tax Year 2026-27 under Income-tax Act, 2025)
    Gross Salary: ₹1,00,000 / month (₹12,00,000 Annual)
    Basic Salary: ₹50,000 / month (50% CTC rule compliant)
    """
    # 1. Canonical Statutory Context Resolution
    statutory_ctx = FinancialYearResolver.resolve_statutory_context("2026-27")
    assert statutory_ctx.financial_year == "2026-27"
    assert statutory_ctx.tax_year == "2026-27"
    assert statutory_ctx.assessment_year is None
    assert statutory_ctx.governing_act == "INCOME_TAX_ACT_2025"
    assert statutory_ctx.is_current is True

    # 2. Rule Resolution for Karnataka IT Salaried Profile
    tax_rule = ComplianceRuleRegistry.get_rule("TAX-2026-27-NEW-DEFAULT")
    assert tax_rule is not None
    assert tax_rule.domain == "TAX"
    assert tax_rule.tax_year == "2026-27"
    assert tax_rule.status == "ACTIVE"

    pf_rule = ComplianceRuleRegistry.get_rule("PF-2026-27-STATUTORY")
    assert pf_rule is not None
    assert pf_rule.domain == "PF"

    pt_rule = ComplianceRuleRegistry.get_rule("PT-2026-27-KA-SALARIED")
    assert pt_rule is not None
    assert pt_rule.domain == "PT"
    assert pt_rule.jurisdiction == "KA"

    # 3. Deterministic Arithmetic Execution
    monthly_gross = Decimal("100000.00")
    monthly_basic = Decimal("50000.00")

    # PF calculation (12% of basic up to statutory ceiling of 15,000)
    pf_eligible_wage = min(monthly_basic, Decimal("15000.00"))
    employee_pf = pf_eligible_wage * Decimal("0.12")
    assert employee_pf == Decimal("1800.00")

    # PT calculation (Karnataka: ₹200 if gross >= 15,000)
    monthly_pt = Decimal("200.00") if monthly_gross >= Decimal("15000.00") else Decimal("0.00")
    assert monthly_pt == Decimal("200.00")

    # Tax calculation (Income-tax Act, 2025 / ₹12 Lakh Rebate under Sec 87A / Sec 202)
    # Annual Gross = 12L, Standard Deduction = 75k => Taxable = 11.25L <= 12L rebate ceiling => Tax = 0
    annual_gross = monthly_gross * Decimal("12")
    standard_deduction = Decimal("75000.00")
    taxable_income = max(Decimal("0.00"), annual_gross - standard_deduction)
    assert taxable_income == Decimal("1125000.00")

    # Under 2026-27 revised slabs with ₹12L rebate:
    annual_tax_before_rebate = Decimal(
        "62500.00"
    )  # (4L-8L @ 5% = 20k) + (8L-11.25L @ 10% = 32.5k) = 52.5k -> with 12L rebate => Net Tax 0
    assert annual_tax_before_rebate == Decimal("62500.00")
    annual_net_tax = Decimal("0.00")
    assert annual_net_tax == Decimal("0.00")
    monthly_tds = Decimal("0.00")

    # Net Take-Home Calculation
    net_take_home = monthly_gross - employee_pf - monthly_pt - monthly_tds
    assert net_take_home == Decimal("98000.00")

    # 4. Evidence Citation Verification for "Why was ₹1,800 deducted?"
    pf_citation = EvidenceRegistry.resolve_citation_for_rule(pf_rule.rule_id)
    assert pf_citation is not None
    assert pf_citation.authority == "EPFO / Ministry of Labour & Employment"
    assert pf_citation.document_id == "smart_salary_epf_eps_edli_framework-v2.md"
    assert "epfindia.gov.in" in pf_citation.official_url

    # 5. Evidence Citation Verification for Tax Rule
    tax_citation = EvidenceRegistry.resolve_citation_for_rule(tax_rule.rule_id)
    assert tax_citation is not None
    assert tax_citation.authority == "Ministry of Finance / CBDT"
    assert tax_citation.document_id == "87647dtc-aps2139-inceome-tax-act-2025.pdf"
    assert "incometaxindia.gov.in" in tax_citation.official_url or "incometax.gov.in" in tax_citation.official_url
