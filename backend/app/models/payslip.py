from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class PayslipDocument(Base, TimestampMixin):
    __tablename__ = "payslip_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    status: Mapped[str] = mapped_column(
        String(50), default="UPLOADED", nullable=False
    )  # UPLOADED, PARSED, VALIDATED, FAILED

    employee: Mapped["Employee"] = relationship("Employee")
    extractions: Mapped[list["PayslipExtraction"]] = relationship(
        "PayslipExtraction", back_populates="document", cascade="all, delete-orphan"
    )
    validations: Mapped[list["PayslipValidation"]] = relationship(
        "PayslipValidation", back_populates="document", cascade="all, delete-orphan"
    )


class PayslipExtraction(Base, TimestampMixin):
    __tablename__ = "payslip_extractions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("payslip_documents.id", ondelete="CASCADE"), nullable=False
    )
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("1.0000"), nullable=False)
    ocr_engine_used: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., 'TESSERACT', 'NATIVE_PDF'
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["PayslipDocument"] = relationship("PayslipDocument", back_populates="extractions")


class PayslipValidation(Base, TimestampMixin):
    __tablename__ = "payslip_validations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("payslip_documents.id", ondelete="CASCADE"), nullable=False
    )
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False)  # PASSED, FAILED, WARNING
    discrepancy_flags: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    reconciliation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["PayslipDocument"] = relationship("PayslipDocument", back_populates="validations")
