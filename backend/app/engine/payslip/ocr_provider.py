from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class DocumentType(StrEnum):
    DIGITAL_TEXT_PDF = "DIGITAL_TEXT_PDF"
    SCANNED_PDF = "SCANNED_PDF"
    HYBRID_PDF = "HYBRID_PDF"
    INVALID_PDF = "INVALID_PDF"


class DocumentCategory(StrEnum):
    PAYSLIP = "PAYSLIP"
    FORM_16 = "FORM_16"
    TAX_DOCUMENT = "TAX_DOCUMENT"
    OTHER = "OTHER"


@dataclass
class PageImage:
    page_number: int
    image_bytes: bytes
    width: int
    height: int


@dataclass
class OCRWord:
    text: str
    confidence: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2


@dataclass
class OCRPageResult:
    page_number: int
    text: str
    words: list[OCRWord] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class OCRResult:
    engine_name: str
    pages: list[OCRPageResult] = field(default_factory=list)
    full_text: str = ""
    average_confidence: float = 1.0


class OCRProvider(Protocol):
    """Abstract OCR Provider interface for scanned documents."""

    def extract_text(self, pages: list[PageImage]) -> OCRResult:
        """Performs optical character recognition on page images."""
        ...


class FallbackOCRProvider:
    """
    Fallback OCR implementation when specialized optical engine is not configured.
    Provides structured fallback responses for scanned documents.
    """

    def extract_text(self, pages: list[PageImage]) -> OCRResult:
        results: list[OCRPageResult] = []
        for p in pages:
            results.append(
                OCRPageResult(
                    page_number=p.page_number,
                    text="",
                    confidence=0.5,
                )
            )
        return OCRResult(
            engine_name="FALLBACK_MOCK_OCR",
            pages=results,
            full_text="",
            average_confidence=0.5,
        )
