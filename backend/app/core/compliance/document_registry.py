"""
SmartSalary India — Document Registry
Central service for cataloging, indexing, hashing, and resolving documents from docs/tax_pdf.
"""
import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentCatalogItem:
    document_id: str
    relative_path: str
    file_size_bytes: int
    sha256_hash: str
    authority: str
    domain: str
    source_priority: int  # 1=Primary (Acts), 2=Secondary (CBDT), 3=Guidance, 4=FAQ, 5=User
    title: str
    official_url: str
    is_indexed: bool


class DocumentRegistry:
    """
    Registry for scanning and managing regulatory PDF/MD files in docs/tax_pdf.
    """

    _DOCS_ROOT = Path("docs/tax_pdf")

    @classmethod
    def compute_sha256(cls, file_path: Path) -> str:
        """Computes cryptographic SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def scan_tax_pdf_vault(cls, root_path: Path | None = None) -> list[DocumentCatalogItem]:
        """Scans and catalogs all documents within docs/tax_pdf."""
        root = root_path or cls._DOCS_ROOT
        if not root.exists():
            return []

        catalog = []
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in [".pdf", ".md", ".json", ".txt"]:
                rel_path = str(p.relative_to(root)).replace("\\", "/")
                sha = cls.compute_sha256(p)
                size = p.stat().st_size

                # Classify authority and domain
                authority = "Ministry of Finance / CBDT"
                domain = "TAX"
                priority = 1
                official_url = "https://incometax.gov.in"

                if "epf" in p.name.lower() or "mole" in p.name.lower():
                    authority = "EPFO / Ministry of Labour & Employment"
                    domain = "PF"
                    official_url = "https://epfindia.gov.in"
                elif "esic" in p.name.lower() or "esi" in p.name.lower():
                    authority = "ESIC / Ministry of Labour & Employment"
                    domain = "ESI"
                    official_url = "https://esic.gov.in"
                elif "professional_tax" in p.name.lower() or "state" in p.name.lower():
                    authority = "State Commercial Taxes Department"
                    domain = "PT"
                    official_url = "https://karnatakacommercialtax.gov.in"

                item = DocumentCatalogItem(
                    document_id=p.name,
                    relative_path=rel_path,
                    file_size_bytes=size,
                    sha256_hash=sha,
                    authority=authority,
                    domain=domain,
                    source_priority=priority,
                    title=p.stem.replace("_", " ").title(),
                    official_url=official_url,
                    is_indexed=True,
                )
                catalog.append(item)

        return catalog
