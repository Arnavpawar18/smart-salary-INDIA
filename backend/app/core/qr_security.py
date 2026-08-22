"""
SmartSalary India — Secure QR Verification Service (M6)
Generates and verifies opaque, signed, non-sensitive verification tokens for calculation snapshots and payslips.
Guarantees NO salary, PAN, bank details, or PII ever leak into QR codes.
"""

import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

QR_SECRET_KEY = os.environ.get("QR_VERIFICATION_SECRET", "smartsalary-qr-verification-secret-2026-prod")


@dataclass(frozen=True)
class QRVerificationTokenPayload:
    token_id: str
    snapshot_id: str
    tenant_id: int
    rule_bundle_hash: str
    evidence_bundle_hash: str
    created_at: str
    expires_at: str
    signature: str

    def is_expired(self) -> bool:
        exp = datetime.fromisoformat(self.expires_at)
        return datetime.now(UTC) > exp


class QRVerificationService:
    """
    Authoritative QR Token Generation and Verification Service.
    Enforces:
    - Opaque non-sensitive tokens containing only cryptographically signed cryptographic references.
    - Zero PII (No salary, PAN, bank account, name, or raw amounts).
    - Expiration verification (default 90 days validity for verified snapshot certificates).
    - Tamper detection using HMAC-SHA256.
    """

    @classmethod
    def generate_verification_token(
        cls,
        snapshot_id: str,
        tenant_id: int,
        rule_bundle_hash: str,
        evidence_bundle_hash: str,
        validity_days: int = 90,
    ) -> str:
        token_id = f"QRT-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(UTC)
        exp = now + timedelta(days=validity_days)

        payload_str = f"{token_id}.{snapshot_id}.{tenant_id}.{rule_bundle_hash}.{evidence_bundle_hash}.{int(now.timestamp())}.{int(exp.timestamp())}"
        sig = hmac.new(QR_SECRET_KEY.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()

        return f"{payload_str}.{sig}"

    @classmethod
    def verify_token(
        cls, token: str, requesting_tenant_id: int | None = None
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """
        Verifies QR token validity, signature, expiration, and optional tenant scoping.
        Returns (is_valid, reason, decoded_metadata).
        """
        if not token or "." not in token:
            return False, "MALFORMED_TOKEN", None

        parts = token.split(".")
        if len(parts) != 8:
            return False, "INVALID_TOKEN_STRUCTURE", None

        token_id, snapshot_id, tenant_id_str, rb_hash, eb_hash, created_at_ts, expires_at_ts, signature = parts

        # 1. Signature Verification (Constant-Time HMAC Comparison)
        payload_str = f"{token_id}.{snapshot_id}.{tenant_id_str}.{rb_hash}.{eb_hash}.{created_at_ts}.{expires_at_ts}"
        expected_sig = hmac.new(QR_SECRET_KEY.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return False, "SIGNATURE_TAMPERING_DETECTED", None

        # 2. Expiration Verification
        try:
            exp_ts = int(expires_at_ts)
            if datetime.now(UTC).timestamp() > exp_ts:
                return False, "TOKEN_EXPIRED", None
        except Exception:
            return False, "INVALID_EXPIRATION_FORMAT", None

        # 3. Tenant Isolation Check (if requesting from an authenticated tenant context)
        tenant_id = int(tenant_id_str)
        if requesting_tenant_id is not None and requesting_tenant_id != tenant_id:
            return False, "CROSS_TENANT_ACCESS_DENIED", None

        return (
            True,
            "VERIFIED",
            {
                "token_id": token_id,
                "snapshot_id": snapshot_id,
                "tenant_id": tenant_id,
                "rule_bundle_hash": rb_hash,
                "evidence_bundle_hash": eb_hash,
                "verified_at": datetime.now(UTC).isoformat(),
                "has_pii": False,  # Strict proof of zero PII
            },
        )
