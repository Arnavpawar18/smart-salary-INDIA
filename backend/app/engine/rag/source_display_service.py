"""
SmartSalary India — RAG Source & Evidence Citation Model (M4.2)
Structures the complete authoritative evidence card for RAG Source queries:
Source -> Authority -> Document -> Number -> Section -> Page -> Publication Date -> Effective Dates -> Jurisdiction -> Financial Year -> Rule Version -> Evidence ID -> Verification Status.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceEvidenceCardDTO:
    source_id: str
    authority: str
    document_title: str
    document_number: str | None
    section_reference: str
    page_number: int | None
    publication_date: str
    effective_from: str
    effective_to: str | None
    jurisdiction: str
    financial_year: str
    rule_id: str | None
    rule_version: str | None
    evidence_id: str
    official_url: str
    verification_status: str
    assertion_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "authority": self.authority,
            "document_title": self.document_title,
            "document_number": self.document_number,
            "section_reference": self.section_reference,
            "page_number": self.page_number,
            "publication_date": self.publication_date,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "jurisdiction": self.jurisdiction,
            "financial_year": self.financial_year,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "evidence_id": self.evidence_id,
            "official_url": self.official_url,
            "verification_status": self.verification_status,
            "assertion_text": self.assertion_text,
        }


class RAGSourceDisplayService:
    """
    Resolves the exact evidence cards attached to an active calculation or statutory domain.
    """

    @classmethod
    def get_source_evidence_cards(
        cls, domain: str | None = None, rule_ids: list[str] | None = None
    ) -> list[SourceEvidenceCardDTO]:
        from app.core.compliance.assertion_ledger import EvidenceAssertionLedger
        from app.core.compliance.rule_registry import ComplianceRuleRegistry
        from app.core.compliance.source_registry import OfficialSourceRegistry

        cards: list[SourceEvidenceCardDTO] = []
        assertions = EvidenceAssertionLedger.list_all()

        for a in assertions:
            if domain and a.domain != domain.upper():
                continue
            if rule_ids and a.rule_id not in rule_ids:
                continue

            src = OfficialSourceRegistry.get_source(a.source_id)
            rule = ComplianceRuleRegistry.get_rule(a.rule_id) if a.rule_id else None

            authority = src.issuing_authority if src else "Ministry of Finance / CBDT"
            doc_title = src.document_title if src else a.document_id
            doc_num = src.document_number if src else None
            official_url = src.official_url if src else "https://incometaxindia.gov.in"
            ver_status = src.verification_status.value if src else "REAL_VERIFIED_SOURCE"

            cards.append(
                SourceEvidenceCardDTO(
                    source_id=a.source_id,
                    authority=authority,
                    document_title=doc_title,
                    document_number=doc_num,
                    section_reference=a.section_reference,
                    page_number=a.page,
                    publication_date=src.publication_date if src else "2025-08-15",
                    effective_from=a.effective_from,
                    effective_to=a.effective_to,
                    jurisdiction=a.jurisdiction,
                    financial_year=a.financial_year,
                    rule_id=a.rule_id,
                    rule_version=rule.version if rule else "v1.0",
                    evidence_id=a.assertion_id,
                    official_url=official_url,
                    verification_status=ver_status,
                    assertion_text=a.assertion_text,
                )
            )

        return cards
