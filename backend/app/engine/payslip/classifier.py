import io

from pypdf import PdfReader

from app.engine.payslip.ocr_provider import DocumentCategory, DocumentType


class PDFClassifier:
    """
    Classifies uploaded PDF documents into structural types (Digital vs Scanned)
    and business categories (Payslip vs Form 16 vs Tax Document vs Other).
    """

    PAYSLIP_KEYWORDS = {
        "payslip",
        "pay slip",
        "salary slip",
        "earnings",
        "deductions",
        "basic salary",
        "net pay",
        "provident fund",
        "epf",
        "professional tax",
        "uan",
        "pan",
        "ctc",
    }

    FORM16_KEYWORDS = {
        "form no. 16",
        "form 16",
        "certificate under section 203",
        "tax deducted at source",
        "assessment year",
        "quarter 1",
        "quarter 2",
        "quarter 3",
        "quarter 4",
    }

    @classmethod
    def classify(cls, pdf_bytes: bytes) -> tuple[DocumentType, DocumentCategory, float]:
        """
        Returns:
            (DocumentType, DocumentCategory, text_density_score)
        """
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            if len(reader.pages) == 0:
                return DocumentType.INVALID_PDF, DocumentCategory.OTHER, 0.0

            total_chars = 0
            extracted_pages_text = []

            for page in reader.pages:
                text = page.extract_text() or ""
                extracted_pages_text.append(text)
                total_chars += len(text.strip())

            full_text = " ".join(extracted_pages_text).lower()

            # 1. Determine DocumentType (Digital vs Scanned)
            # Average characters per page threshold for digital text PDF
            avg_chars = total_chars / max(len(reader.pages), 1)
            if avg_chars > 80:
                doc_type = DocumentType.DIGITAL_TEXT_PDF
                text_density = min(avg_chars / 500.0, 1.0)
            elif avg_chars > 10:
                doc_type = DocumentType.HYBRID_PDF
                text_density = avg_chars / 500.0
            else:
                doc_type = DocumentType.SCANNED_PDF
                text_density = 0.0

            # 2. Determine DocumentCategory
            payslip_hits = sum(1 for kw in cls.PAYSLIP_KEYWORDS if kw in full_text)
            form16_hits = sum(1 for kw in cls.FORM16_KEYWORDS if kw in full_text)

            if form16_hits >= 3 and form16_hits > payslip_hits:
                category = DocumentCategory.FORM_16
            elif payslip_hits >= 2:
                category = DocumentCategory.PAYSLIP
            else:
                category = DocumentCategory.OTHER

            return doc_type, category, round(text_density, 4)

        except Exception:
            return DocumentType.INVALID_PDF, DocumentCategory.OTHER, 0.0
