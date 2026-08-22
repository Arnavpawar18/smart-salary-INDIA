"""
SmartSalary India — Evidence Registry (Hydrated from Master Regulatory Vault & History)
Provides multi-level legal mapping: Document -> Fragment -> Assertion -> Rule -> CalculationTrace.
Hydrated with official statutory citations across Direct Tax, Social Security, Labour Codes, and State PT.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceDocumentMeta:
    document_id: str
    title: str
    authority: str
    official_url: str
    publication_date: str
    effective_from: str
    effective_to: str | None
    tier: int  # Tier 1 (Acts/Gazette), Tier 2 (CBDT/EPFO/ESIC Delegated Rules), Tier 3 (Official Circulars), Tier 4 (Secondary)
    verification_status: str  # VERIFIED, PENDING_REVIEW


@dataclass(frozen=True)
class EvidenceCitation:
    rule_id: str
    document_id: str
    document_title: str
    authority: str
    official_url: str
    page_number: int | None
    section_reference: str
    verified_date: str


class EvidenceRegistry:
    """
    Evidence registry resolving official document metadata and page/section citations.
    """

    _DOCUMENTS: dict[str, EvidenceDocumentMeta] = {
        # 1. Income-tax Act, 2025
        "87647dtc-aps2139-inceome-tax-act-2025.pdf": EvidenceDocumentMeta(
            document_id="87647dtc-aps2139-inceome-tax-act-2025.pdf",
            title="The Income-tax Act, 2025 (Act No. 30 of 2025)",
            authority="Ministry of Finance / CBDT",
            official_url="https://incometaxindia.gov.in/Pages/default.aspx",
            publication_date="2025-08-15",
            effective_from="2026-04-01",
            effective_to=None,
            tier=1,
            verification_status="VERIFIED",
        ),
        # 2. Income-tax Rules, 2026 (Perquisite & HRA Metro Expansion)
        "income_tax_rules_2026.md": EvidenceDocumentMeta(
            document_id="income_tax_rules_2026.md",
            title="The Income-tax Rules, 2026 (Notification No. 22/2026)",
            authority="Central Board of Direct Taxes (CBDT)",
            official_url="https://incometaxindia.gov.in/Pages/rules/index.aspx",
            publication_date="2026-02-10",
            effective_from="2026-04-01",
            effective_to=None,
            tier=2,
            verification_status="VERIFIED",
        ),
        # 3. Code on Wages, 2019 (Section 2(y) 50% Wage Code Rule)
        "code_on_wages_2019.md": EvidenceDocumentMeta(
            document_id="code_on_wages_2019.md",
            title="The Code on Wages, 2019 (Act No. 29 of 2019)",
            authority="Ministry of Labour & Employment",
            official_url="https://labour.gov.in/labour-codes",
            publication_date="2019-08-08",
            effective_from="2025-11-21",
            effective_to=None,
            tier=1,
            verification_status="VERIFIED",
        ),
        # 4. Code on Social Security, 2020 & EPF Scheme 2026
        "smart_salary_epf_eps_edli_framework-v2.md": EvidenceDocumentMeta(
            document_id="smart_salary_epf_eps_edli_framework-v2.md",
            title="Employees' Provident Funds and Miscellaneous Provisions Scheme, 2026 [Notification G.S.R. 525(E)]",
            authority="EPFO / Ministry of Labour & Employment",
            official_url="https://epfindia.gov.in/site_en/RulesRegulations.php",
            publication_date="2026-06-29",
            effective_from="2026-04-01",
            effective_to=None,
            tier=2,
            verification_status="VERIFIED",
        ),
        # 5. ESIC Central Rules 2026
        "smart_salary_esi_esic_framework-v2.md": EvidenceDocumentMeta(
            document_id="smart_salary_esi_esic_framework-v2.md",
            title="Employees' State Insurance (Central) Rules, 2026 [Notification G.S.R. 112(E)]",
            authority="ESIC / Ministry of Labour & Employment",
            official_url="https://esic.gov.in/notifications",
            publication_date="2026-02-15",
            effective_from="2026-04-01",
            effective_to=None,
            tier=2,
            verification_status="VERIFIED",
        ),
        # 6. Karnataka Professional Tax Act Schedule
        "smart_salary_professional_tax_states.md": EvidenceDocumentMeta(
            document_id="smart_salary_professional_tax_states.md",
            title="Karnataka Tax on Professions, Trades, Callings and Employments Act Schedule [Notification DPAL 08 SHASANA 2025]",
            authority="Government of Karnataka / Commercial Taxes Department",
            official_url="https://karnatakacommercialtax.gov.in",
            publication_date="2025-04-15",
            effective_from="2025-04-01",
            effective_to=None,
            tier=1,
            verification_status="VERIFIED",
        ),
        # 7. Maharashtra Professional Tax Finance Act 2023
        "maharashtra_pt_schedule_2023.md": EvidenceDocumentMeta(
            document_id="maharashtra_pt_schedule_2023.md",
            title="Maharashtra State Tax on Professions, Trades, Callings and Employments (Amendment) Act, 2023",
            authority="Department of Sales Tax, Government of Maharashtra",
            official_url="https://mahagst.gov.in/en/acts_rules/professional_tax",
            publication_date="2023-03-20",
            effective_from="2023-04-01",
            effective_to=None,
            tier=1,
            verification_status="VERIFIED",
        ),
        # 8. Fixed-Term Employment Gratuity (Code on Social Security Section 53(2))
        "smart_salary_bonus_gratuity_retirement_framework.md": EvidenceDocumentMeta(
            document_id="smart_salary_bonus_gratuity_retirement_framework.md",
            title="Code on Social Security, 2020 — Chapter V Gratuity & 1-Year FTE Pro-Rata Entitlement",
            authority="Parliament of India / Ministry of Labour & Employment",
            official_url="https://labour.gov.in/labour-codes",
            publication_date="2020-09-29",
            effective_from="2025-11-21",
            effective_to=None,
            tier=1,
            verification_status="VERIFIED",
        ),
    }

    @classmethod
    def get_document_meta(cls, document_id: str) -> EvidenceDocumentMeta | None:
        return cls._DOCUMENTS.get(document_id)

    @classmethod
    def resolve_citation_for_rule(cls, rule_id: str) -> EvidenceCitation | None:
        from app.core.compliance.rule_registry import ComplianceRuleRegistry

        rule = ComplianceRuleRegistry.get_rule(rule_id)
        if not rule:
            return None

        doc = cls.get_document_meta(rule.evidence_document_id)
        if not doc:
            return None

        return EvidenceCitation(
            rule_id=rule.rule_id,
            document_id=doc.document_id,
            document_title=doc.title,
            authority=doc.authority,
            official_url=doc.official_url,
            page_number=rule.evidence_page,
            section_reference=rule.rule_code,
            verified_date=rule.verified_at,
        )
