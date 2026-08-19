"""
SmartSalary India — Stage M2.1 Evidence Ingestion Tests
Validates cataloging, SHA-256 deduplication, authority classification, and citation resolution from docs/tax_pdf.
"""
from pathlib import Path

from app.core.compliance.document_registry import DocumentRegistry
from app.core.compliance.evidence_registry import EvidenceRegistry
from app.core.compliance.rule_registry import ComplianceRuleRegistry


def test_tax_pdf_vault_scanning():
    """Verify scanning and hashing of docs/tax_pdf documents."""
    docs_root = Path("..") / "docs" / "tax_pdf"
    catalog = DocumentRegistry.scan_tax_pdf_vault(docs_root)
    assert len(catalog) > 0, "Expected at least one document found in docs/tax_pdf"

    # Verify SHA-256 format for all cataloged documents
    for item in catalog:
        assert len(item.sha256_hash) == 64
        assert item.source_priority in [1, 2, 3, 4, 5]
        assert item.authority is not None


def test_evidence_registry_resolution():
    """Verify that statutory rules resolve to valid evidence metadata."""
    tax_rule = ComplianceRuleRegistry.get_rule("TAX-2026-27-NEW-DEFAULT")
    assert tax_rule is not None

    citation = EvidenceRegistry.resolve_citation_for_rule(tax_rule.rule_id)
    assert citation is not None
    assert citation.authority == "Ministry of Finance / CBDT"
    assert citation.document_id == "87647dtc-aps2139-inceome-tax-act-2025.pdf"
    assert citation.official_url.startswith("https://")


def test_product_faq_corpus_exists():
    """Verify that curated product knowledge documents are seeded and readable."""
    faq_path = Path("..") / "docs" / "knowledge" / "product" / "faq.md"
    assert faq_path.exists(), "Product FAQ corpus file missing"
    content = faq_path.read_text(encoding="utf-8")
    assert "SmartSalary" in content
    assert "Income-tax Act, 2025" in content
