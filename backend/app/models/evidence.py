"""
SmartSalary India — Evidence Models
Implements the Multi-Tier Relational Evidence Repository:
Document -> Page -> Fragment -> Assertion -> Rule -> Citation.
"""
from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utc_now


class EvidenceDocument(Base, TimestampMixin):
    """
    Authoritative regulatory or legal document in docs/tax_pdf.
    """
    __tablename__ = "evidence_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    authority: Mapped[str] = mapped_column(String(100), nullable=False)  # CBDT, EPFO, ESIC, State Government
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ACT, GAZETTE, CIRCULAR, NOTIFICATION, RULE, FAQ
    official_url: Mapped[str] = mapped_column(String(500), nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    financial_year: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tax_year: Mapped[str | None] = mapped_column(String(10), nullable=True)
    assessment_year: Mapped[str | None] = mapped_column(String(10), nullable=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)  # TAX, TDS, PF, ESI, PT, GST, LABOUR
    jurisdiction: Mapped[str] = mapped_column(String(50), default="INDIA", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="EN", nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=Primary, 2=Secondary, etc.
    verification_status: Mapped[str] = mapped_column(String(32), default="VERIFIED", nullable=False)  # VERIFIED, UNVERIFIED
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    superseded_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("evidence_documents.id", ondelete="SET NULL"), nullable=True)

    fragments: Mapped[list["EvidenceFragment"]] = relationship("EvidenceFragment", back_populates="document", cascade="all, delete-orphan")


class EvidenceFragment(Base, TimestampMixin):
    """
    Extracted textual page/section fragment with bounding box and integrity hash.
    """
    __tablename__ = "evidence_fragments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("evidence_documents.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fragment_text: Mapped[str] = mapped_column(Text, nullable=False)
    fragment_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of text
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    document: Mapped["EvidenceDocument"] = relationship("EvidenceDocument", back_populates="fragments")
    assertions: Mapped[list["EvidenceAssertion"]] = relationship("EvidenceAssertion", back_populates="fragment", cascade="all, delete-orphan")


class EvidenceAssertion(Base, TimestampMixin):
    """
    Discrete statutory assertion linked directly to rules, official URLs, and specific legal paragraphs.
    """
    __tablename__ = "evidence_assertions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fragment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("evidence_fragments.id", ondelete="CASCADE"), nullable=False)
    assertion_text: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    financial_year: Mapped[str] = mapped_column(String(10), nullable=False)
    state_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rule_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    official_url: Mapped[str] = mapped_column(String(500), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="HIGH", nullable=False)  # HIGH, MEDIUM, LOW

    fragment: Mapped["EvidenceFragment"] = relationship("EvidenceFragment", back_populates="assertions")
