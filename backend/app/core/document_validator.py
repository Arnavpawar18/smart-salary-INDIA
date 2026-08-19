import io
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class DocumentValidationResult:
    is_valid: bool
    mime_type: str
    file_size_bytes: int
    page_count: int
    is_encrypted: bool
    error_message: str | None = None


class DocumentValidator:
    """
    Validates uploaded document files before passing them into the extraction pipeline.
    Enforces:
    1. Size constraints (Max 10MB).
    2. Magic number verification (%PDF-).
    3. Proper PDF structure parsing via pypdf.
    4. Page count caps (Max 10 pages for payslips).
    5. Encryption detection (encrypted/password-protected PDFs rejected).
    6. Filename sanitization.
    """

    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
    MAX_PAGE_COUNT = 10
    ALLOWED_EXTENSIONS = {".pdf"}

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitizes filename removing unsafe path traversal characters."""
        base = Path(filename).name
        # Keep alphanumeric, dashes, underscores, and dots
        clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
        return clean or "payslip.pdf"

    @classmethod
    def validate_pdf(cls, file_bytes: bytes, filename: str) -> DocumentValidationResult:
        file_size = len(file_bytes)

        # 1. Size check
        if file_size == 0:
            return DocumentValidationResult(
                is_valid=False,
                mime_type="application/octet-stream",
                file_size_bytes=0,
                page_count=0,
                is_encrypted=False,
                error_message="Uploaded file is empty (0 bytes).",
            )

        if file_size > cls.MAX_FILE_SIZE_BYTES:
            return DocumentValidationResult(
                is_valid=False,
                mime_type="application/pdf",
                file_size_bytes=file_size,
                page_count=0,
                is_encrypted=False,
                error_message=f"File size ({file_size / (1024 * 1024):.2f}MB) exceeds maximum limit of 10MB.",
            )

        # 2. Extension check
        ext = Path(filename).suffix.lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            return DocumentValidationResult(
                is_valid=False,
                mime_type="application/octet-stream",
                file_size_bytes=file_size,
                page_count=0,
                is_encrypted=False,
                error_message=f"Invalid file extension '{ext}'. Only PDF files are supported.",
            )

        # 3. Magic bytes check (%PDF-)
        if not file_bytes.startswith(b"%PDF-"):
            return DocumentValidationResult(
                is_valid=False,
                mime_type="application/octet-stream",
                file_size_bytes=file_size,
                page_count=0,
                is_encrypted=False,
                error_message="Invalid file signature. File does not start with PDF magic bytes (%PDF-).",
            )

        # 4. Structural validation via pypdf
        try:
            stream = io.BytesIO(file_bytes)
            reader = PdfReader(stream)

            # Encryption check
            if reader.is_encrypted:
                return DocumentValidationResult(
                    is_valid=False,
                    mime_type="application/pdf",
                    file_size_bytes=file_size,
                    page_count=0,
                    is_encrypted=True,
                    error_message="Password-protected or encrypted PDF documents cannot be processed. Please upload an unencrypted document.",
                )

            page_count = len(reader.pages)
            if page_count == 0:
                return DocumentValidationResult(
                    is_valid=False,
                    mime_type="application/pdf",
                    file_size_bytes=file_size,
                    page_count=0,
                    is_encrypted=False,
                    error_message="PDF contains no pages.",
                )

            if page_count > cls.MAX_PAGE_COUNT:
                return DocumentValidationResult(
                    is_valid=False,
                    mime_type="application/pdf",
                    file_size_bytes=file_size,
                    page_count=page_count,
                    is_encrypted=False,
                    error_message=f"PDF page count ({page_count}) exceeds maximum allowed ({cls.MAX_PAGE_COUNT} pages).",
                )

            return DocumentValidationResult(
                is_valid=True,
                mime_type="application/pdf",
                file_size_bytes=file_size,
                page_count=page_count,
                is_encrypted=False,
                error_message=None,
            )

        except Exception as e:
            return DocumentValidationResult(
                is_valid=False,
                mime_type="application/pdf",
                file_size_bytes=file_size,
                page_count=0,
                is_encrypted=False,
                error_message=f"Malformed or corrupt PDF structure: {str(e)}",
            )
