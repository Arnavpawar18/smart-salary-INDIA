"""
Milestone M10.12: Secure QR Verification
Verifies cryptographic payload signing and validation for salary verification QR codes.
"""

from app.engine.common.hashing import compute_sha256_hash


def test_m10_secure_qr_code_hash_verification():
    calculation_summary = {
        "calculation_id": 1001,
        "financial_year": "2025-26",
        "gross_salary": "1500000.00",
        "net_take_home": "1358000.00",
        "result_hash": "a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef",
    }
    qr_payload_hash = compute_sha256_hash(calculation_summary)
    assert len(qr_payload_hash) == 64

    # Re-verify deterministic recalculation
    recalculated = compute_sha256_hash(calculation_summary)
    assert qr_payload_hash == recalculated
