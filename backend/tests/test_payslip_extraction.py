from decimal import Decimal

from app.engine.payslip.payslip_extractor import PayslipExtractor


def test_payslip_extractor_regex_parsing():
    sample_text = """
    TECH CORP INDIA PRIVATE LIMITED
    Salary Slip for the month of April 2026

    Employee Name: Vikram Mehta
    Employee ID: TC-84920
    PAN: ABCDE1234F
    UAN: 100904328901
    Designation: Principal Engineer

    Earnings                Amount          Deductions              Amount
    Basic Salary            50,000.00       Provident Fund (EPF)    1,800.00
    House Rent Allowance    25,000.00       Professional Tax        200.00
    Special Allowance       25,000.00       Income Tax (TDS)        8,500.00

    Gross Earnings:         1,00,000.00     Total Deductions:       10,500.00
    Net Take-Home Pay:      89,500.00
    """

    extractor = PayslipExtractor()
    dto = extractor.extract_from_pdf(b"%PDF-1.4 mock", "test.pdf")

    # Manually pass text through internal extractor methods for precision unit testing
    prov = {}
    lines = sample_text.splitlines()
    extractor._extract_metadata(sample_text, lines, dto, prov, "native_test")
    extractor._extract_period(sample_text, lines, dto, prov, "native_test")
    extractor._extract_earnings(sample_text, lines, dto, prov, "native_test")
    extractor._extract_deductions(sample_text, lines, dto, prov, "native_test")
    extractor._extract_totals(sample_text, lines, dto, prov, "native_test")

    assert dto.employee_name == "Vikram Mehta"
    assert dto.pan == "ABCDE1234F"
    assert dto.uan == "100904328901"
    assert dto.month == "April"
    assert dto.year == 2026
    assert dto.period_code == "2026-04"

    assert dto.basic == Decimal("50000.00")
    assert dto.hra == Decimal("25000.00")
    assert dto.special_allowance == Decimal("25000.00")
    assert dto.gross_earnings == Decimal("100000.00")

    assert dto.employee_epf == Decimal("1800.00")
    assert dto.professional_tax == Decimal("200.00")
    assert dto.tds == Decimal("8500.00")
    assert dto.total_deductions == Decimal("10500.00")
    assert dto.net_pay == Decimal("89500.00")
    assert dto.gross_earnings - dto.total_deductions == dto.net_pay
