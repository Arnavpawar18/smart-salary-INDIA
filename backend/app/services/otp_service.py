import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limiter import InMemoryRateLimiter
from app.models.verification_token import VerificationToken

logger = logging.getLogger(__name__)


class OTPPurpose:
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    PASSWORD_RESET = "PASSWORD_RESET"


class OTPStatus:
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    EXPIRED = "EXPIRED"
    LOCKED = "LOCKED"
    CANCELLED = "CANCELLED"


class OTPService:
    """
    Authoritative OTP Generation, Hashing, Rate-Limiting, and Verification Service.

    Security & Invariant Guarantees:
      - 6-digit cryptographically secure numeric OTP (`secrets.randbelow(1_000_000)`).
      - Server-side HMAC-SHA256 storage (`HMAC(OTP_HASH_SECRET, email:purpose:otp)`).
      - Zero plaintext storage in DB or logs.
      - 5-minute TTL, max 5 verification attempts before locking.
      - 60-second resend cooldown per email & purpose.
      - Explicit invalidation (CANCELLED) of older active tokens upon new issuance.
      - Row-level atomic concurrency lock (`with_for_update`) during verification.
    """

    @classmethod
    def generate_otp(cls) -> str:
        """Generates a secure 6-digit numeric OTP (e.g. '048291')."""
        return f"{secrets.randbelow(1_000_000):06d}"

    @classmethod
    def compute_hmac(cls, email: str, purpose: str, otp: str) -> str:
        """Computes deterministic HMAC-SHA256 digest of normalized (email, purpose, otp)."""
        normalized_email = email.strip().lower()
        message = f"{normalized_email}:{purpose}:{otp}".encode()
        secret = settings.OTP_HASH_SECRET.encode()
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    @classmethod
    def get_latest_active_token(
        cls,
        db: Session,
        email: str,
        purpose: str,
    ) -> VerificationToken | None:
        """Returns the most recent valid pending token, or None if expired/used/locked."""
        normalized_email = email.strip().lower()
        now = datetime.now(UTC)
        tok = db.scalar(
            select(VerificationToken)
            .where(
                VerificationToken.email == normalized_email,
                VerificationToken.purpose == purpose,
                VerificationToken.status == OTPStatus.PENDING,
            )
            .order_by(VerificationToken.created_at.desc())
        )
        if not tok:
            return None
        exp = tok.expires_at.replace(tzinfo=UTC) if tok.expires_at.tzinfo is None else tok.expires_at
        if now > exp:
            return None
        return tok

    @classmethod
    def create_verification_token(
        cls,
        db: Session,
        email: str,
        purpose: str,
        user_id: int | None = None,
    ) -> tuple[VerificationToken, str]:
        """
        Creates a new verification token, cancels any previous pending token,
        and returns (VerificationToken, raw_otp).
        """
        normalized_email = email.strip().lower()

        # Check Resend Cooldown and Hourly Rate Limit
        rate_key = f"otp_resend:{normalized_email}:{purpose}"
        InMemoryRateLimiter.check_rate_limit(rate_key, max_requests=5, window_seconds=3600)

        # Invalidate/Cancel any existing PENDING tokens for this (email, purpose)
        stmt = select(VerificationToken).where(
            VerificationToken.email == normalized_email,
            VerificationToken.purpose == purpose,
            VerificationToken.status == OTPStatus.PENDING,
        )
        if db.bind and db.bind.dialect.name != "sqlite":
            stmt = stmt.with_for_update()

        existing_tokens = db.execute(stmt).scalars().all()

        now = datetime.now(UTC)
        for tok in existing_tokens:
            last_activity = tok.last_resend_at or tok.created_at
            if last_activity:
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=UTC)
                if (now - last_activity) < timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS):
                    remaining = int(settings.OTP_RESEND_COOLDOWN_SECONDS - (now - last_activity).total_seconds())
                    raise HTTPException(
                        status_code=429,
                        detail=f"Please wait {remaining} seconds before requesting another verification code.",
                    )
            tok.status = OTPStatus.CANCELLED

        if existing_tokens:
            db.flush()

        # Generate fresh 6-digit OTP and HMAC
        raw_otp = cls.generate_otp()
        token_hash = cls.compute_hmac(normalized_email, purpose, raw_otp)
        expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        token = VerificationToken(
            verification_id=uuid.uuid4(),
            user_id=user_id,
            email=normalized_email,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=expires_at,
            attempt_count=0,
            status=OTPStatus.PENDING,
            created_at=now,
            last_resend_at=now,
        )
        db.add(token)
        db.commit()
        db.refresh(token)

        logger.info(
            "Issued OTP token verification_id=%s for email=%s purpose=%s expires_at=%s",
            token.verification_id,
            normalized_email,
            purpose,
            expires_at,
        )
        return token, raw_otp

    @classmethod
    def verify_otp(
        cls,
        db: Session,
        verification_id: uuid.UUID,
        raw_otp: str,
        expected_purpose: str,
    ) -> tuple[bool, str, VerificationToken | None]:
        """
        Verifies a user-submitted OTP against verification_id and purpose with atomic row lock.

        Returns:
            tuple[success: bool, error_or_success_message: str, token: VerificationToken | None]
        """
        stmt = select(VerificationToken).where(VerificationToken.verification_id == verification_id)
        if db.bind and db.bind.dialect.name != "sqlite":
            stmt = stmt.with_for_update()
        token = db.scalar(stmt)

        if not token:
            return False, "Invalid verification request or token not found.", None

        # Check Purpose Separation
        if token.purpose != expected_purpose:
            return False, "Invalid verification purpose for this token.", token

        # Check Status & Invariants
        if token.status == OTPStatus.VERIFIED:
            return False, "This verification code has already been used.", token
        if token.status == OTPStatus.LOCKED:
            return False, "Verification locked due to too many failed attempts. Please request a new code.", token
        if token.status == OTPStatus.CANCELLED:
            return False, "This verification code was superseded by a newer request. Please use the latest code.", token

        # Check Expiry
        now = datetime.now(UTC)
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if now > expires_at:
            token.status = OTPStatus.EXPIRED
            db.commit()
            return False, "Verification code has expired. Please request a new code.", token

        # Check Attempt Count before increment
        if token.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            token.status = OTPStatus.LOCKED
            db.commit()
            return False, "Maximum verification attempts exceeded. Token is now locked.", token

        # Validate HMAC digest using constant-time comparison
        computed_hash = cls.compute_hmac(token.email, token.purpose, raw_otp.strip())
        is_valid = hmac.compare_digest(token.token_hash, computed_hash)

        if not is_valid:
            token.attempt_count += 1
            if token.attempt_count >= settings.OTP_MAX_ATTEMPTS:
                token.status = OTPStatus.LOCKED
                db.commit()
                return False, "Incorrect verification code. Maximum attempts reached; token locked.", token
            db.commit()
            remaining_attempts = settings.OTP_MAX_ATTEMPTS - token.attempt_count
            return False, f"Incorrect verification code. {remaining_attempts} attempts remaining.", token

        # Valid OTP: Mark VERIFIED
        token.status = OTPStatus.VERIFIED
        token.verified_at = now
        db.commit()
        db.refresh(token)

        logger.info(
            "Successfully verified OTP token verification_id=%s for email=%s purpose=%s",
            token.verification_id,
            token.email,
            token.purpose,
        )
        return True, "Verification successful.", token
