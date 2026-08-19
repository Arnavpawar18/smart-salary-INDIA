"""
SmartSalary India — Compliance Rule Registry
Central registry mapping statutory domains across Income Tax, PF, ESI, PT, TDS, and GST.
Enforces multi-year support: FY 2021-22 through FY 2026-27 (Old and New Regimes).
"""
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class RuleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    HISTORICAL = "HISTORICAL"
    FUTURE_OFFICIALLY_NOTIFIED = "FUTURE_OFFICIALLY_NOTIFIED"
    PROPOSED = "PROPOSED"
    SUPERSEDED = "SUPERSEDED"
    REQUIRES_VERIFICATION = "REQUIRES_VERIFICATION"
    DRAFT = "DRAFT"


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    rule_code: str
    domain: str  # TAX, PF, ESI, PT, TDS, GST
    jurisdiction: str  # INDIA, KA, MH, DL, TN, TS, etc.
    tax_year: str  # 2026-27, 2025-26, etc.
    version: str  # v1.0
    status: RuleStatus | str  # ACTIVE, HISTORICAL, SUPERSEDED, etc.
    effective_from: date
    effective_to: date | None
    formula_expression: str
    condition_expression: str
    evidence_document_id: str
    evidence_page: int | None
    official_url: str
    verified_at: str


class ComplianceRuleRegistry:
    """
    In-memory and DB-backed compliance rule discovery and validation service.
    Ensures deterministic engines only execute verified statutory rules across FY 2021-22 to FY 2026-27.
    """

    _REGISTRY: dict[str, RuleDefinition] = {
        # --- Income Tax 2026-27 (Income-tax Act, 2025 / Section 202) ---
        "TAX-2026-27-NEW-DEFAULT": RuleDefinition(
            rule_id="TAX-2026-27-NEW-DEFAULT",
            rule_code="SEC_202_SLABS",
            domain="TAX",
            jurisdiction="INDIA",
            tax_year="2026-27",
            version="1.0",
            status=RuleStatus.ACTIVE,
            effective_from=date(2026, 4, 1),
            effective_to=date(2027, 3, 31),
            formula_expression="standard_deduction = 75000; slabs = [(0,4L,0%), (4L,8L,5%), (8L,12L,10%), (12L,16L,15%), (16L,20L,20%), (20L,24L,25%), (>24L,30%)]",
            condition_expression="regime == 'NEW'",
            evidence_document_id="87647dtc-aps2139-inceome-tax-act-2025.pdf",
            evidence_page=124,
            official_url="https://incometax.gov.in/iec/foportal/tax-act-2025",
            verified_at="2026-08-18",
        ),
        # --- Income Tax 2025-26 (Finance Act 2024 / Section 115BAC) ---
        "TAX-2025-26-NEW": RuleDefinition(
            rule_id="TAX-2025-26-NEW",
            rule_code="SEC_115BAC_FA2024",
            domain="TAX",
            jurisdiction="INDIA",
            tax_year="2025-26",
            version="1.0",
            status=RuleStatus.ACTIVE,
            effective_from=date(2024, 4, 1),
            effective_to=date(2026, 3, 31),
            formula_expression="standard_deduction = 75000; slabs = [(0,3L,0%), (3L,7L,5%), (7L,10L,10%), (10L,12L,15%), (12L,15L,20%), (>15L,30%)]",
            condition_expression="regime == 'NEW'",
            evidence_document_id="finance_act_2024_tax_slabs.md",
            evidence_page=15,
            official_url="https://incometax.gov.in",
            verified_at="2025-07-23",
        ),
        # --- Income Tax Old Regime (Section 115BAC Opt-Out) ---
        "TAX-OLD-REGIME-STANDARD": RuleDefinition(
            rule_id="TAX-OLD-REGIME-STANDARD",
            rule_code="SEC_115BAC_OPTOUT_OLD",
            domain="TAX",
            jurisdiction="INDIA",
            tax_year="ALL",
            version="1.0",
            status=RuleStatus.ACTIVE,
            effective_from=date(2020, 4, 1),
            effective_to=None,
            formula_expression="standard_deduction = 50000; slabs = [(0,2.5L,0%), (2.5L,5L,5%), (5L,10L,20%), (>10L,30%)]",
            condition_expression="regime == 'OLD'",
            evidence_document_id="finance_act_old_regime_framework.md",
            evidence_page=42,
            official_url="https://incometax.gov.in",
            verified_at="2025-04-01",
        ),
        # --- EPF / EPS / EDLI (Code on Social Security 2020 / Scheme 2026) ---
        "PF-2026-27-STATUTORY": RuleDefinition(
            rule_id="PF-2026-27-STATUTORY",
            rule_code="EPF_12_PERCENT",
            domain="PF",
            jurisdiction="INDIA",
            tax_year="2026-27",
            version="1.0",
            status=RuleStatus.ACTIVE,
            effective_from=date(2026, 4, 1),
            effective_to=date(2027, 3, 31),
            formula_expression="employee_pf = min(basic_da, 15000) * 0.12; employer_pf = min(basic_da, 15000) * 0.0367; employer_eps = min(basic_da, 15000) * 0.0833; edli = min(basic_da, 15000) * 0.005",
            condition_expression="basic_da > 0",
            evidence_document_id="smart_salary_epf_eps_edli_framework-v2.md",
            evidence_page=1,
            official_url="https://epfindia.gov.in/site_en/RulesRegulations.php",
            verified_at="2026-08-18",
        ),
        # --- Professional Tax Karnataka (Karnataka Tax on Professions Act) ---
        "PT-2026-27-KA-SALARIED": RuleDefinition(
            rule_id="PT-2026-27-KA-SALARIED",
            rule_code="KA_PT_SLAB",
            domain="PT",
            jurisdiction="KA",
            tax_year="2026-27",
            version="1.0",
            status=RuleStatus.ACTIVE,
            effective_from=date(2026, 4, 1),
            effective_to=date(2027, 3, 31),
            formula_expression="pt = 200 if gross_salary >= 15000 else 0",
            condition_expression="state == 'Karnataka'",
            evidence_document_id="smart_salary_professional_tax_states.md",
            evidence_page=4,
            official_url="https://karnatakacommercialtax.gov.in",
            verified_at="2026-08-18",
        ),
        # --- Professional Tax Maharashtra ---
        "PT-2026-27-MH-SALARIED": RuleDefinition(
            rule_id="PT-2026-27-MH-SALARIED",
            rule_code="MH_PT_SLAB",
            domain="PT",
            jurisdiction="MH",
            tax_year="2026-27",
            version="1.0",
            status=RuleStatus.ACTIVE,
            effective_from=date(2026, 4, 1),
            effective_to=date(2027, 3, 31),
            formula_expression="pt = 200 (₹300 in Feb) if gross_salary > 10000 (men) or > 25000 (women) else 0",
            condition_expression="state == 'Maharashtra'",
            evidence_document_id="smart_salary_professional_tax_states.md",
            evidence_page=8,
            official_url="https://mahagst.gov.in",
            verified_at="2026-08-18",
        ),
        # --- Future Officially Notified / Proposed Gate Test Fixture ---
        "TAX-FUTURE-PROPOSAL-DRAFT": RuleDefinition(
            rule_id="TAX-FUTURE-PROPOSAL-DRAFT",
            rule_code="PROPOSED_TAX_CODE_2028",
            domain="TAX",
            jurisdiction="INDIA",
            tax_year="2028-29",
            version="0.1-draft",
            status=RuleStatus.PROPOSED,
            effective_from=date(2028, 4, 1),
            effective_to=None,
            formula_expression="tax = 0.15 * gross",
            condition_expression="is_draft == True",
            evidence_document_id="draft_policy_whitepaper.md",
            evidence_page=1,
            official_url="https://finmin.nic.in/draft",
            verified_at="2026-08-18",
        ),
    }

    @classmethod
    def get_rule(cls, rule_id: str) -> RuleDefinition | None:
        return cls._REGISTRY.get(rule_id)

    @classmethod
    def get_active_rule(cls, rule_id: str) -> RuleDefinition | None:
        rule = cls.get_rule(rule_id)
        if not rule or rule.status not in (RuleStatus.ACTIVE, "ACTIVE"):
            return None
        return rule

    @classmethod
    def list_rules_for_domain(cls, domain: str, jurisdiction: str = "INDIA") -> list[RuleDefinition]:
        return [
            r
            for r in cls._REGISTRY.values()
            if r.domain == domain and (r.jurisdiction == jurisdiction or r.jurisdiction == "INDIA")
        ]
