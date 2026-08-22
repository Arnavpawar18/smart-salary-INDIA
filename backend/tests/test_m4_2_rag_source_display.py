"""
Tests for Milestone M4.2: RAG Source Display Gate
Validates that querying 'Sources?' returns full Evidence Cards containing:
- Official Source
- Issuing Authority
- Document & Document Number
- Section & Page Number
- Publication & Effective Dates
- Jurisdiction & Financial Year
- Rule Version & Evidence Assertion
"""

from app.engine.rag.source_display_service import (
    RAGSourceDisplayService,
)


def test_m4_2_rag_source_display_card_fields():
    # 1. Retrieve all statutory evidence cards
    cards = RAGSourceDisplayService.get_source_evidence_cards()
    assert len(cards) > 0, "M4.2 Failure: No evidence cards returned for source inquiry."

    # 2. Inspect Income Tax 2026-27 Card
    tax_card = next((c for c in cards if c.rule_id == "TAX-2026-27-NEW-DEFAULT"), None)
    assert tax_card is not None
    assert tax_card.source_id == "SR-FED-TAX-ACT-2025"
    assert tax_card.authority == "Parliament of India / Ministry of Law and Justice"
    assert "Income-tax Act, 2025" in tax_card.document_title
    assert tax_card.section_reference == "Section 202"
    assert tax_card.page_number == 124
    assert tax_card.effective_from == "2026-04-01"
    assert tax_card.jurisdiction == "INDIA"
    assert tax_card.financial_year == "2026-27"
    assert tax_card.rule_version == "1.0"
    assert tax_card.evidence_id == "EA-TAX-2026-001"
    assert tax_card.verification_status == "REAL_VERIFIED_SOURCE"
    assert "incometaxindia.gov.in" in tax_card.official_url

    # 3. Inspect Karnataka PT Card
    ka_card = next((c for c in cards if c.rule_id == "PT-2026-27-KA-SALARIED"), None)
    assert ka_card is not None
    assert ka_card.jurisdiction == "KA"
    assert ka_card.page_number == 4
    assert "karnatakacommercialtax.gov.in" in ka_card.official_url or "karnatakataxes.gov.in" in ka_card.official_url


def test_m4_2_rag_source_display_domain_filtering():
    # Filter only TAX cards
    tax_cards = RAGSourceDisplayService.get_source_evidence_cards(domain="TAX")
    assert len(tax_cards) > 0
    assert all(c.section_reference.startswith("Section") for c in tax_cards)

    # Filter only PT cards
    pt_cards = RAGSourceDisplayService.get_source_evidence_cards(domain="PT")
    assert len(pt_cards) > 0
    assert all(c.jurisdiction in ("KA", "MH", "DL") for c in pt_cards)
