"""
SmartSalary India — Evidence Registry
Provides multi-level legal mapping: Document -> Fragment -> Assertion -> Rule -> CalculationTrace.
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
    tier: int  # Tier 1 (Acts/Gazette), Tier 2 (CBDT Validation), Tier 3 (ICAI), Tier 4 (Secondary)
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
        "87647dtc-aps2139-inceome-tax-act-2025.pdf": EvidenceDocumentMeta(
            document_id="87647dtc-aps2139-inceome-tax-act-2025.pdf",
            title="The Income-tax Act, 2025 (Act No. XX of 2025)",
            authority="Ministry of Finance / CBDT",
            official_url="https://incometax.gov.in/iec/foportal/tax-act-2025",
            publication_date="2025-08-15",
            effective_from="2026-04-01",
            effective_to=None,
            tier=1,
            verification_status="VERIFIED",
        ),
        "smart_salary_epf_eps_edli_framework-v2.md": EvidenceDocumentMeta(
            document_id="smart_salary_epf_eps_edli_framework-v2.md",
            title="Employees' Provident Funds and Miscellaneous Provisions Scheme, 2026",
            authority="EPFO / Ministry of Labour & Employment",
            official_url="https://epfindia.gov.in/site_en/RulesRegulations.php",
            publication_date="2025-12-10",
            effective_from="2026-04-01",
            effective_to=None,
            tier=1,
            verification_status="VERIFIED",
        ),
        "smart_salary_professional_tax_states.md": EvidenceDocumentMeta(
            document_id="smart_salary_professional_tax_states.md",
            title="Karnataka Tax on Professions, Trades, Callings and Employments Act Schedule",
            authority="Government of Karnataka / Commercial Taxes Department",
            official_url="https://karnatakacommercialtax.gov.in",
            publication_date="2025-03-31",
            effective_from="2025-04-01",
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
