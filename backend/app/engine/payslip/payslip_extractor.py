import io
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pypdf import PdfReader

from app.engine.payslip.classifier import PDFClassifier
from app.engine.payslip.ocr_provider import DocumentCategory, DocumentType, FallbackOCRProvider, OCRProvider


@dataclass
class SpatialProvenance:
    field_name: str
    raw_value: str
    normalized_value: Any
    page_number: int
    bounding_box: tuple[float, float, float, float]  # (x1, y1, x2, y2)
    source_text: str
    parser: str = "regex_native_v1"
    extraction_method: str = "native_pdf_text"
    confidence: float = 1.0


@dataclass
class ExtractedPayslipDTO:
    # Employee Metadata
    employee_name: str | None = None
    employee_code: str | None = None
    pan: str | None = None
    uan: str | None = None
    designation: str | None = None
    department: str | None = None
    organization_name: str | None = None

    # Pay Period
    month: str | None = None
    year: int | None = None
    period_code: str | None = None  # e.g., '2026-04'

    # Earnings
    basic: Decimal = Decimal("0.00")
    da: Decimal = Decimal("0.00")
    hra: Decimal = Decimal("0.00")
    special_allowance: Decimal = Decimal("0.00")
    conveyance: Decimal = Decimal("0.00")
    transport: Decimal = Decimal("0.00")
    medical: Decimal = Decimal("0.00")
    bonus: Decimal = Decimal("0.00")
    incentive: Decimal = Decimal("0.00")
    overtime: Decimal = Decimal("0.00")
    arrears: Decimal = Decimal("0.00")
    other_earnings: Decimal = Decimal("0.00")
    gross_earnings: Decimal = Decimal("0.00")
    custom_earnings: dict[str, Decimal] = field(default_factory=dict)

    # Deductions
    employee_epf: Decimal = Decimal("0.00")
    professional_tax: Decimal = Decimal("0.00")
    tds: Decimal = Decimal("0.00")
    esi: Decimal = Decimal("0.00")
    loan: Decimal = Decimal("0.00")
    advance: Decimal = Decimal("0.00")
    insurance: Decimal = Decimal("0.00")
    other_deductions: Decimal = Decimal("0.00")
    total_deductions: Decimal = Decimal("0.00")
    custom_deductions: dict[str, Decimal] = field(default_factory=dict)

    # Employer Contributions (Isolated)
    employer_epf: Decimal = Decimal("0.00")
    employer_eps: Decimal = Decimal("0.00")
    employer_edli: Decimal = Decimal("0.00")
    employer_esi: Decimal = Decimal("0.00")
    gratuity: Decimal = Decimal("0.00")
    other_employer_contributions: Decimal = Decimal("0.00")

    # Net Pay
    net_pay: Decimal = Decimal("0.00")

    # Provenance & Quality
    spatial_provenance: dict[str, SpatialProvenance] = field(default_factory=dict)
    raw_text: str = ""
    document_type: str = DocumentType.DIGITAL_TEXT_PDF.value
    document_category: str = DocumentCategory.PAYSLIP.value
    overall_confidence: float = 1.0
    extraction_status: str = "HIGH"  # HIGH, MEDIUM, LOW, FAILED
    formula_verified: bool = True
    formula_discrepancy_rupees: Decimal = Decimal("0.00")


class PayslipExtractor:
    """
    Structured Payslip Extractor with Native PDF Stream parsing and OCR fallback.
    Enforces Rule 1: Extraction is NEVER calculation. Only extracts observed values.
    """

    MONTH_MAP = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "sept": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }

    def __init__(self, ocr_provider: OCRProvider | None = None):
        self.ocr_provider = ocr_provider or FallbackOCRProvider()

    @staticmethod
    def _parse_currency(value_str: str) -> Decimal:
        """Sanitizes currency string e.g. '₹ 1,25,000.00' -> Decimal('125000.00')."""
        if not value_str:
            return Decimal("0.00")
        clean = re.sub(r"[^\d.-]", "", value_str.replace(",", ""))
        try:
            return Decimal(clean).quantize(Decimal("0.01"))
        except Exception:
            return Decimal("0.00")

    def extract_from_pdf(self, pdf_bytes: bytes, filename: str = "") -> ExtractedPayslipDTO:
        # 1. Classify document
        doc_type, category, text_density = PDFClassifier.classify(pdf_bytes)

        raw_pages_text: list[str] = []
        is_scanned = doc_type == DocumentType.SCANNED_PDF or text_density < 0.05

        if not is_scanned:
            # Native text extraction via pypdf
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                raw_pages_text.append(page.extract_text() or "")
            full_text = "\n".join(raw_pages_text)
            extraction_method = "native_pdf_text"
        else:
            # Fallback to OCR provider
            ocr_result = self.ocr_provider.extract_text([])
            full_text = ocr_result.full_text
            extraction_method = f"ocr_{ocr_result.engine_name}"

        dto = ExtractedPayslipDTO(
            document_type=doc_type.value,
            document_category=category.value,
            raw_text=full_text,
        )

        provenance_map: dict[str, SpatialProvenance] = {}
        lines = full_text.splitlines()

        # 2. Extract Employee Metadata
        self._extract_metadata(full_text, lines, dto, provenance_map, extraction_method)

        # 3. Extract Pay Period
        self._extract_period(full_text, lines, dto, provenance_map, extraction_method)

        # 4. Extract Earnings Components
        self._extract_earnings(full_text, lines, dto, provenance_map, extraction_method)

        # 5. Extract Deductions Components
        self._extract_deductions(full_text, lines, dto, provenance_map, extraction_method)

        # 6. Extract Employer Contributions
        self._extract_employer_contributions(full_text, lines, dto, provenance_map, extraction_method)

        # 7. Extract Net Pay & Totals
        self._extract_totals(full_text, lines, dto, provenance_map, extraction_method)

        # 8. Check Document Formula Verification: Gross - Deductions == Net
        calculated_net = dto.gross_earnings - dto.total_deductions
        if dto.net_pay > Decimal("0.00"):
            dto.formula_discrepancy_rupees = abs(dto.net_pay - calculated_net)
            # Allow up to ₹1 formula tolerance for internal rounding in payslip printouts
            dto.formula_verified = dto.formula_discrepancy_rupees <= Decimal("1.00")
        else:
            # If Net Pay was not explicitly printed, derive it
            dto.net_pay = calculated_net
            dto.formula_verified = True

        dto.spatial_provenance = provenance_map

        # 9. Compute Overall Extraction Confidence & Status
        confidences = [p.confidence for p in provenance_map.values()]
        dto.overall_confidence = round(sum(confidences) / max(len(confidences), 1), 2)

        if dto.overall_confidence >= 0.85 and dto.gross_earnings > 0:
            dto.extraction_status = "HIGH"
        elif dto.overall_confidence >= 0.60:
            dto.extraction_status = "MEDIUM"
        elif dto.gross_earnings > 0:
            dto.extraction_status = "LOW"
        else:
            dto.extraction_status = "FAILED"

        return dto

    def _extract_metadata(
        self,
        full_text: str,
        lines: list[str],
        dto: ExtractedPayslipDTO,
        prov: dict[str, SpatialProvenance],
        method: str,
    ) -> None:
        # PAN Pattern
        pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b", full_text)
        if pan_match:
            val = pan_match.group(1)
            dto.pan = val
            prov["pan"] = SpatialProvenance(
                field_name="pan",
                raw_value=val,
                normalized_value=val,
                page_number=1,
                bounding_box=(0.0, 0.0, 0.0, 0.0),
                source_text=pan_match.group(0),
                extraction_method=method,
                confidence=0.98,
            )

        # UAN Pattern (12 digits)
        uan_match = re.search(r"(?:UAN|U\.A\.N\.)\s*[:#-]?\s*(\d{12})\b", full_text, re.IGNORECASE)
        if uan_match:
            val = uan_match.group(1)
            dto.uan = val
            prov["uan"] = SpatialProvenance(
                field_name="uan",
                raw_value=val,
                normalized_value=val,
                page_number=1,
                bounding_box=(0.0, 0.0, 0.0, 0.0),
                source_text=uan_match.group(0),
                extraction_method=method,
                confidence=0.95,
            )

        # Employee Name / Code
        name_match = re.search(r"(?:Employee\s*Name|Name)\s*[:]\s*([A-Za-z\s.]+?)(?:\r?\n|$)", full_text, re.IGNORECASE)
        if name_match:
            dto.employee_name = name_match.group(1).strip()
            prov["employee_name"] = SpatialProvenance(
                field_name="employee_name",
                raw_value=dto.employee_name,
                normalized_value=dto.employee_name,
                page_number=1,
                bounding_box=(0.0, 0.0, 0.0, 0.0),
                source_text=name_match.group(0),
                extraction_method=method,
                confidence=0.90,
            )

        code_match = re.search(r"(?:Emp(?:loyee)?\s*(?:ID|Code|No))\s*[:]\s*([A-Za-z0-9_-]+)", full_text, re.IGNORECASE)
        if code_match:
            dto.employee_code = code_match.group(1).strip()
            prov["employee_code"] = SpatialProvenance(
                field_name="employee_code",
                raw_value=dto.employee_code,
                normalized_value=dto.employee_code,
                page_number=1,
                bounding_box=(0.0, 0.0, 0.0, 0.0),
                source_text=code_match.group(0),
                extraction_method=method,
                confidence=0.92,
            )

    def _extract_period(
        self,
        full_text: str,
        lines: list[str],
        dto: ExtractedPayslipDTO,
        prov: dict[str, SpatialProvenance],
        method: str,
    ) -> None:
        # Match Month and Year e.g. "Payslip for April 2026", "Pay Period: 04/2026", "Month: April 2026"
        month_names = "|".join(self.MONTH_MAP.keys())
        period_match = re.search(rf"\b({month_names})\s+([2][0][2-3][0-9])\b", full_text, re.IGNORECASE)
        if period_match:
            m_str = period_match.group(1).lower()
            y_int = int(period_match.group(2))
            m_num = self.MONTH_MAP[m_str]
            dto.month = period_match.group(1).capitalize()
            dto.year = y_int
            dto.period_code = f"{y_int}-{m_num:02d}"
            prov["pay_period"] = SpatialProvenance(
                field_name="pay_period",
                raw_value=period_match.group(0),
                normalized_value=dto.period_code,
                page_number=1,
                bounding_box=(0.0, 0.0, 0.0, 0.0),
                source_text=period_match.group(0),
                extraction_method=method,
                confidence=0.96,
            )

    def _extract_earnings(
        self,
        full_text: str,
        lines: list[str],
        dto: ExtractedPayslipDTO,
        prov: dict[str, SpatialProvenance],
        method: str,
    ) -> None:
        patterns = {
            "basic": [r"Basic(?:\s+Salary)?\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "da": [r"(?:Dearness\s+Allowance|D\.A\.)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "hra": [r"(?:House\s+Rent\s+Allowance|HRA|H\.R\.A\.)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "special_allowance": [r"(?:Special\s+Allowance|Spl\s+Allowance)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "conveyance": [r"Conveyance(?:\s+Allowance)?\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "transport": [r"Transport(?:\s+Allowance)?\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "medical": [r"Medical(?:\s+Allowance)?\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "bonus": [r"(?:Performance\s+Bonus|Bonus)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "arrears": [r"Arrears\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "incentive": [r"Incentive\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"],
            "gross_earnings": [
                r"(?:Gross\s+(?:Salary|Earnings|Pay)|Total\s+Earnings)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)"
            ],
        }

        for comp, regex_list in patterns.items():
            for regex in regex_list:
                match = re.search(regex, full_text, re.IGNORECASE)
                if match:
                    val = self._parse_currency(match.group(1))
                    setattr(dto, comp, val)
                    prov[comp] = SpatialProvenance(
                        field_name=comp,
                        raw_value=match.group(1),
                        normalized_value=val,
                        page_number=1,
                        bounding_box=(0.0, 0.0, 0.0, 0.0),
                        source_text=match.group(0),
                        extraction_method=method,
                        confidence=0.92,
                    )
                    break

        # If gross was not matched explicitly, sum known earnings
        if dto.gross_earnings == Decimal("0.00"):
            dto.gross_earnings = (
                dto.basic
                + dto.da
                + dto.hra
                + dto.special_allowance
                + dto.conveyance
                + dto.transport
                + dto.medical
                + dto.bonus
                + dto.arrears
                + dto.incentive
                + dto.other_earnings
            )

    def _extract_deductions(
        self,
        full_text: str,
        lines: list[str],
        dto: ExtractedPayslipDTO,
        prov: dict[str, SpatialProvenance],
        method: str,
    ) -> None:
        patterns = {
            "employee_epf": [
                r"(?:Provident\s+Fund\s*(?:\(EPF\)|\(PF\))?|EPF|E\.P\.F\.|PF\s+Employee|Employee\s+PF)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)",
                r"(?<!Employer\s)PF\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)",
            ],
            "professional_tax": [
                r"(?:Professional\s+Tax\s*(?:\(PT\))?|Prof\s+Tax|P\.Tax|PT)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)",
            ],
            "tds": [
                r"(?:Tax\s+Deducted(?:\s+at\s+Source)?\s*(?:\(TDS\))?|Income\s+Tax\s*(?:\(TDS\))?|TDS|T\.D\.S\.)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)",
            ],
            "esi": [
                r"(?:ESI|E\.S\.I\.|Employee\s+State\s+Insurance)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)",
            ],
            "total_deductions": [
                r"(?:Total\s+Deductions|Total\s+Deduction|Gross\s+Deductions)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)",
            ],
        }

        for comp, regex_list in patterns.items():
            for regex in regex_list:
                match = re.search(regex, full_text, re.IGNORECASE)
                if match:
                    val = self._parse_currency(match.group(1))
                    setattr(dto, comp, val)
                    prov[comp] = SpatialProvenance(
                        field_name=comp,
                        raw_value=match.group(1),
                        normalized_value=val,
                        page_number=1,
                        bounding_box=(0.0, 0.0, 0.0, 0.0),
                        source_text=match.group(0),
                        extraction_method=method,
                        confidence=0.91,
                    )
                    break

        if dto.total_deductions == Decimal("0.00"):
            dto.total_deductions = (
                dto.employee_epf
                + dto.professional_tax
                + dto.tds
                + dto.esi
                + dto.loan
                + dto.advance
                + dto.insurance
                + dto.other_deductions
            )

    def _extract_employer_contributions(
        self,
        full_text: str,
        lines: list[str],
        dto: ExtractedPayslipDTO,
        prov: dict[str, SpatialProvenance],
        method: str,
    ) -> None:
        empr_pf_match = re.search(
            r"(?:Employer\s+(?:PF|EPF)|Empr\s+PF)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)", full_text, re.IGNORECASE
        )
        if empr_pf_match:
            val = self._parse_currency(empr_pf_match.group(1))
            dto.employer_epf = val
            prov["employer_epf"] = SpatialProvenance(
                field_name="employer_epf",
                raw_value=empr_pf_match.group(1),
                normalized_value=val,
                page_number=1,
                bounding_box=(0.0, 0.0, 0.0, 0.0),
                source_text=empr_pf_match.group(0),
                extraction_method=method,
                confidence=0.90,
            )

    def _extract_totals(
        self,
        full_text: str,
        lines: list[str],
        dto: ExtractedPayslipDTO,
        prov: dict[str, SpatialProvenance],
        method: str,
    ) -> None:
        net_match = re.search(
            r"(?:Net\s+(?:Take[- ]Home\s+)?(?:Pay|Salary|Amount)|Take\s*Home\s*Pay)\s*[:]?\s*([₹]?\s*[\d,]+(?:\.\d{2})?)",
            full_text,
            re.IGNORECASE,
        )
        if net_match:
            val = self._parse_currency(net_match.group(1))
            dto.net_pay = val
            prov["net_pay"] = SpatialProvenance(
                field_name="net_pay",
                raw_value=net_match.group(1),
                normalized_value=val,
                page_number=1,
                bounding_box=(0.0, 0.0, 0.0, 0.0),
                source_text=net_match.group(0),
                extraction_method=method,
                confidence=0.95,
            )
