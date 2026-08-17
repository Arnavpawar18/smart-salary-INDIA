import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

# Password Hasher using Argon2id
password_hash = PasswordHash((Argon2Hasher(),))


class PasswordHasher:
    """Isolates password hashing and verification behind an authoritative interface."""

    @classmethod
    def hash_password(cls, password: str) -> str:
        return password_hash.hash(password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return password_hash.verify(plain_password, hashed_password)


class JWTProvider:
    """
    Authoritative JWT token generation and validation provider.
    Supports configurable algorithm (default HS256) and JTI generation.
    """

    SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "smartsalary-secret-key-change-in-production-2026")
    ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    @classmethod
    def create_access_token(
        cls,
        user_id: int,
        role: str,
        employee_id: int | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        now = datetime.now(UTC)
        expire = now + (expires_delta if expires_delta else timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES))
        payload = {
            "sub": str(user_id),
            "role": role,
            "employee_id": employee_id,
            "type": "access",
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)

    @classmethod
    def create_refresh_token(
        cls,
        user_id: int,
        expires_delta: timedelta | None = None,
    ) -> tuple[str, str, datetime]:
        """Returns (raw_refresh_token, jti, expire_datetime)."""
        now = datetime.now(UTC)
        expire = now + (expires_delta if expires_delta else timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS))
        jti = str(uuid.uuid4())
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": now,
            "exp": expire,
            "jti": jti,
        }
        raw_token = jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return raw_token, jti, expire

    @classmethod
    def decode_token(cls, token: str) -> dict[str, Any]:
        """Decodes and verifies a JWT token."""
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid or expired token: {e}") from e

    @classmethod
    def compute_token_hash(cls, token: str) -> str:
        """Computes SHA-256 hash of refresh token for database persistence."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
