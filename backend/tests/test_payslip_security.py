from app.core.document_validator import DocumentValidator
from app.core.malware_scanner import DevPassThroughScanner
from app.core.storage import LocalDocumentStorage
from tests.fixtures.synthetic_payslips import create_synthetic_payslip_pdf


def test_document_validator_valid_pdf():
    pdf_bytes = create_synthetic_payslip_pdf()
    res = DocumentValidator.validate_pdf(pdf_bytes, "april_payslip.pdf")
    assert res.is_valid is True
    assert res.mime_type == "application/pdf"
    assert res.file_size_bytes > 0


def test_document_validator_reject_non_pdf():
    non_pdf = b"Hello, this is just plain text, not a PDF."
    res = DocumentValidator.validate_pdf(non_pdf, "fake.pdf")
    assert res.is_valid is False
    assert "magic bytes" in res.error_message.lower()


def test_document_validator_reject_empty_file():
    res = DocumentValidator.validate_pdf(b"", "empty.pdf")
    assert res.is_valid is False
    assert "empty" in res.error_message.lower()


def test_document_validator_reject_wrong_extension():
    pdf_bytes = create_synthetic_payslip_pdf()
    res = DocumentValidator.validate_pdf(pdf_bytes, "payslip.exe")
    assert res.is_valid is False
    assert "extension" in res.error_message.lower()


def test_malware_scanner_eicar_and_suspicious_pdf():
    scanner = DevPassThroughScanner()
    clean_bytes = create_synthetic_payslip_pdf()
    assert scanner.scan(clean_bytes).is_safe is True

    # EICAR payload
    eicar_bytes = b"%PDF-1.4\n" + DevPassThroughScanner.EICAR_SIG
    scan_eicar = scanner.scan(eicar_bytes)
    assert scan_eicar.is_safe is False
    assert scan_eicar.threat_name == "EICAR_TEST_FILE"


def test_local_document_storage_lifecycle(tmp_path):
    storage = LocalDocumentStorage(base_dir=tmp_path)
    data = b"%PDF-1.4 TEST PAYSLIP DATA"
    key = "emp_101_april2026.pdf"

    storage.store(key, data)
    assert storage.exists(key) is True
    assert storage.retrieve(key) == data

    # Delete
    assert storage.delete(key) is True
    assert storage.exists(key) is False
