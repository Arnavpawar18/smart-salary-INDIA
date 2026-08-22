"""
SmartSalary India — Master Evidence Assertion Ledger (M2.13 Verification)
Tracks every verified statutory claim extracted from primary documents and research vault:
Claim -> Source -> Document -> Fragment -> Assertion -> Rule Mapping -> Verification Status.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ClaimClassification(StrEnum):
    VERIFIED_PRIMARY = "VERIFIED_PRIMARY"
    VERIFIED_OFFICIAL_GUIDANCE = "VERIFIED_OFFICIAL_GUIDANCE"
    SECONDARY = "SECONDARY"
    UNVERIFIED = "UNVERIFIED"
    CONFLICT = "CONFLICT"
    OUTDATED = "OUTDATED"
    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True)
class EvidenceAssertion:
    assertion_id: str
    claim_id: str
    domain: str
    rule_id: str | None
    source_id: str
    document_id: str
    page: int | None
    section_reference: str
    clause_paragraph: str | None
    classification: ClaimClassification
    assertion_text: str
    evidence_fragment_text: str
    effective_from: str
    effective_to: str | None
    jurisdiction: str
    financial_year: str
    verification_date: str

    def is_production_eligible(self) -> bool:
        """Only VERIFIED_PRIMARY and VERIFIED_OFFICIAL_GUIDANCE can authorize active production rules."""
        return self.classification in (
            ClaimClassification.VERIFIED_PRIMARY,
            ClaimClassification.VERIFIED_OFFICIAL_GUIDANCE,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "claim_id": self.claim_id,
            "domain": self.domain,
            "rule_id": self.rule_id,
            "source_id": self.source_id,
            "document_id": self.document_id,
            "page": self.page,
            "section_reference": self.section_reference,
            "clause_paragraph": self.clause_paragraph,
            "classification": self.classification.value,
            "assertion_text": self.assertion_text,
            "evidence_fragment_text": self.evidence_fragment_text,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "jurisdiction": self.jurisdiction,
            "financial_year": self.financial_year,
            "verification_date": self.verification_date,
            "is_production_eligible": self.is_production_eligible(),
        }


class EvidenceAssertionLedger:
    """
    Central verified assertion catalog mapping every active production rule to exact statutory fragments.
    """

    _ASSERTIONS: dict[str, EvidenceAssertion] = {
        # 1. Income Tax 2026-27 Slabs & Standard Default Regime
        "EA-TAX-2026-001": EvidenceAssertion(
            assertion_id="EA-TAX-2026-001",
            claim_id="CLM-TAX-SEC202-DEFAULT",
            domain="TAX",
            rule_id="TAX-2026-27-NEW-DEFAULT",
            source_id="SR-FED-TAX-ACT-2025",
            document_id="87647dtc-aps2139-inceome-tax-act-2025.pdf",
            page=124,
            section_reference="Section 202",
            clause_paragraph="Sub-section (1)",
            classification=ClaimClassification.VERIFIED_PRIMARY,
            assertion_text="The New Tax Regime is the default statutory regime for individuals starting Tax Year 2026-27.",
            evidence_fragment_text="Income-tax payable in respect of total income of a person, being an individual, HUF... shall be computed under the default tax regime.",
            effective_from="2026-04-01",
            effective_to=None,
            jurisdiction="INDIA",
            financial_year="2026-27",
            verification_date="2026-08-18",
        ),
        # 2. Income Tax 2025-26 Section 115BAC Slabs
        "EA-TAX-2025-001": EvidenceAssertion(
            assertion_id="EA-TAX-2025-001",
            claim_id="CLM-TAX-SEC115BAC-FA2024",
            domain="TAX",
            rule_id="TAX-2025-26-NEW",
            source_id="SR-FED-TAX-ACT-1961",
            document_id="finance_act_2024_tax_slabs.md",
            page=15,
            section_reference="Section 115BAC",
            clause_paragraph="Sub-section (1A) as amended by Finance (No. 2) Act, 2024",
            classification=ClaimClassification.VERIFIED_PRIMARY,
            assertion_text="Slabs under Finance Act 2024 for FY 2024-25 and FY 2025-26 (0-3L Nil, 3-7L 5%, 7-10L 10%, 10-12L 15%, 12-15L 20%, >15L 30%).",
            evidence_fragment_text="Tax rates under sub-section (1A) of section 115BAC for the financial year commencing on 1st April 2024.",
            effective_from="2024-04-01",
            effective_to="2026-03-31",
            jurisdiction="INDIA",
            financial_year="2025-26",
            verification_date="2025-07-23",
        ),
        # 3. EPF Statutory Wage Ceiling & 12% Contribution
        "EA-PF-2026-001": EvidenceAssertion(
            assertion_id="EA-PF-2026-001",
            claim_id="CLM-EPF-12PCT-15K-CEILING",
            domain="PF",
            rule_id="PF-2026-27-STATUTORY",
            source_id="SR-EPFO-SCHEME-2026",
            document_id="smart_salary_epf_eps_edli_framework-v2.md",
            page=1,
            section_reference="Para 26 & Notification S.O. 2701(E)",
            clause_paragraph="Paragraph 29(1)",
            classification=ClaimClassification.VERIFIED_PRIMARY,
            assertion_text="Employee contribution is 12% of basic+DA, capped at the statutory wage ceiling of ₹15,000 per month for mandatory cover.",
            evidence_fragment_text="The contribution payable by the employer shall be at the rate of twelve per cent... on the statutory wage ceiling of fifteen thousand rupees.",
            effective_from="2026-04-01",
            effective_to="2027-03-31",
            jurisdiction="INDIA",
            financial_year="2026-27",
            verification_date="2026-08-18",
        ),
        # 4. Karnataka Professional Tax ₹200 with February ₹300 Spike
        "EA-PT-KA-2025-001": EvidenceAssertion(
            assertion_id="EA-PT-KA-2025-001",
            claim_id="CLM-PT-KA-SLAB-SPIKE",
            domain="PT",
            rule_id="PT-2026-27-KA-SALARIED",
            source_id="SR-STATE-KA-PT-2025",
            document_id="smart_salary_professional_tax_states.md",
            page=4,
            section_reference="Schedule I, Entry 1",
            clause_paragraph="Notification No. DPAL 08 SHASANA 2025",
            classification=ClaimClassification.VERIFIED_PRIMARY,
            assertion_text="Karnataka PT is ₹200/month for salary >= ₹15,000, with ₹300 collected in February to equal ₹2,500 annual limit.",
            evidence_fragment_text="Salary or wage earners drawing not less than fifteen thousand rupees per month: Rs. 200 per month (Rs. 300 in February).",
            effective_from="2025-04-01",
            effective_to=None,
            jurisdiction="KA",
            financial_year="2026-27",
            verification_date="2026-08-18",
        ),
        # 5. Maharashtra Professional Tax Female ₹25k Exemption
        "EA-PT-MH-2023-001": EvidenceAssertion(
            assertion_id="EA-PT-MH-2023-001",
            claim_id="CLM-PT-MH-FEMALE-EXEMPT",
            domain="PT",
            rule_id="PT-2026-27-MH-SALARIED",
            source_id="SR-STATE-MH-PT-2023",
            document_id="maharashtra_pt_schedule_2023.md",
            page=8,
            section_reference="Schedule I, Sl. No. 1",
            clause_paragraph="Maharashtra Finance Act, 2023",
            classification=ClaimClassification.VERIFIED_PRIMARY,
            assertion_text="Maharashtra PT exempts women earning up to ₹25,000/month; men pay ₹200/month for salary > ₹10,000 (₹300 in Feb).",
            evidence_fragment_text="Provided that, women employees whose monthly salary does not exceed twenty-five thousand rupees shall be exempt from tax.",
            effective_from="2023-04-01",
            effective_to=None,
            jurisdiction="MH",
            financial_year="2026-27",
            verification_date="2026-08-18",
        ),
        # 6. Fixed-Term Employment Gratuity (1-Year Pro-rata)
        "EA-GRATUITY-FTE-001": EvidenceAssertion(
            assertion_id="EA-GRATUITY-FTE-001",
            claim_id="CLM-SOCSEC-FTE-GRATUITY",
            domain="GRATUITY",
            rule_id=None,
            source_id="SR-FED-LAB-SOCSEC-2020",
            document_id="smart_salary_bonus_gratuity_retirement_framework.md",
            page=5,
            section_reference="Section 53(2)",
            clause_paragraph="Code on Social Security, 2020 Chapter V",
            classification=ClaimClassification.VERIFIED_PRIMARY,
            assertion_text="Fixed-term employees are entitled to pro-rata gratuity on completion of 1 year of continuous service.",
            evidence_fragment_text="The continuous service of five years shall not be necessary where the termination of employment of any fixed-term employee... on completion of one year.",
            effective_from="2025-11-21",
            effective_to=None,
            jurisdiction="INDIA",
            financial_year="2026-27",
            verification_date="2026-08-18",
        ),
        # 8. Income Tax Old Regime Slabs & Section 80C Deductions
        "EA-TAX-OLD-001": EvidenceAssertion(
            assertion_id="EA-TAX-OLD-001",
            claim_id="CLM-TAX-SEC115BAC-OPTOUT",
            domain="TAX",
            rule_id="TAX-OLD-REGIME-STANDARD",
            source_id="SR-FED-TAX-ACT-1961",
            document_id="finance_act_old_regime_framework.md",
            page=42,
            section_reference="Section 115BAC(6)",
            clause_paragraph="First Schedule, Part I",
            classification=ClaimClassification.VERIFIED_PRIMARY,
            assertion_text="Individuals opting out of default New Regime are taxed per standard historical slabs with 80C/80D/24b deductions.",
            evidence_fragment_text="Where an individual exercises the option to opt out of sub-section (1A), the rates of income-tax shall be those specified in the First Schedule.",
            effective_from="2020-04-01",
            effective_to=None,
            jurisdiction="INDIA",
            financial_year="ALL",
            verification_date="2025-04-01",
        ),
    }

    @classmethod
    def get_assertion(cls, assertion_id: str) -> EvidenceAssertion | None:
        return cls._ASSERTIONS.get(assertion_id)

    @classmethod
    def get_assertion_for_rule(cls, rule_id: str) -> EvidenceAssertion | None:
        for a in cls._ASSERTIONS.values():
            if a.rule_id == rule_id:
                return a
        return None

    @classmethod
    def list_all(cls) -> list[EvidenceAssertion]:
        return list(cls._ASSERTIONS.values())
