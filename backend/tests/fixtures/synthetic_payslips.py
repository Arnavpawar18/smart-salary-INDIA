def create_synthetic_payslip_pdf(
    employee_name: str = "Rahul Sharma",
    pan: str = "ABCDE1234F",
    uan: str = "100904328901",
    pay_period: str = "April 2026",
    basic: str = "40,000.00",
    hra: str = "20,000.00",
    special_allowance: str = "20,000.00",
    gross_earnings: str = "80,000.00",
    employee_epf: str = "1,800.00",
    professional_tax: str = "200.00",
    tds: str = "4,500.00",
    total_deductions: str = "6,500.00",
    net_pay: str = "73,500.00",
    employer_epf: str = "1,800.00",
) -> bytes:
    """
    Constructs a valid PDF containing text streams representing a standard synthetic corporate payslip.
    """
    text_content = f"""SMARTSALARY TECHNOLOGIES PRIVATE LIMITED
PAYSLIP FOR THE MONTH OF {pay_period.upper()}

Employee Name: {employee_name}
Employee Code: EMP-10892
PAN: {pan}
UAN: {uan}
Designation: Senior Software Engineer
Department: Engineering

EARNINGS                       AMOUNT (INR)      DEDUCTIONS                     AMOUNT (INR)
---------------------------------------------------------------------------------------------
Basic Salary                   {basic}           Provident Fund (EPF)           {employee_epf}
House Rent Allowance (HRA)     {hra}             Professional Tax (PT)          {professional_tax}
Special Allowance              {special_allowance}           Income Tax (TDS)               {tds}

GROSS EARNINGS:                {gross_earnings}           TOTAL DEDUCTIONS:              {total_deductions}

NET TAKE-HOME PAY:             {net_pay}

EMPLOYER CONTRIBUTIONS:
Employer EPF:                  {employer_epf}
"""

    stream_length = len(text_content) + 100
    pdf_template = (
        "%PDF-1.4\n"
        "1 0 obj\n"
        "<< /Type /Catalog /Pages 2 0 R >>\n"
        "endobj\n"
        "2 0 obj\n"
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        "endobj\n"
        "3 0 obj\n"
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
        "endobj\n"
        f"4 0 obj\n"
        f"<< /Length {stream_length} >>\n"
        "stream\n"
        "BT\n"
        "/F1 10 Tf\n"
        "50 800 Td\n"
        f"({text_content.replace(chr(10), '\\n')}) Tj\n"
        "ET\n"
        "endstream\n"
        "endobj\n"
        "5 0 obj\n"
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
        "endobj\n"
        "xref\n"
        "0 6\n"
        "0000000000 65535 f\n"
        "0000000009 00000 n\n"
        "0000000058 00000 n\n"
        "0000000115 00000 n\n"
        "0000000234 00000 n\n"
        "0000000400 00000 n\n"
        "trailer\n"
        "<< /Size 6 /Root 1 0 R >>\n"
        "startxref\n"
        "480\n"
        "%%EOF\n"
    )
    return pdf_template.encode("latin1")
