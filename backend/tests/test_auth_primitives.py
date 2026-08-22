import uuid

import pytest

from app.core.database import SessionLocal
from app.core.security import JWTProvider, PasswordHasher
from app.models.auth import User
from app.repositories.session_repository import SessionRepository


def test_password_hasher_argon2id():
    pwd = "SuperSecretPassword123!"
    hashed = PasswordHasher.hash_password(pwd)
    assert hashed != pwd
    assert "$argon2id$" in hashed
    assert PasswordHasher.verify_password(pwd, hashed) is True
    assert PasswordHasher.verify_password("WrongPassword", hashed) is False


def test_jwt_provider_access_and_refresh_tokens():
    user_id = 42
    access_token = JWTProvider.create_access_token(user_id=user_id, role="EMPLOYEE", employee_id=101)
    payload = JWTProvider.decode_token(access_token)
    assert payload["sub"] == "42"
    assert payload["role"] == "EMPLOYEE"
    assert payload["employee_id"] == 101
    assert payload["type"] == "access"

    raw_refresh, jti, expire = JWTProvider.create_refresh_token(user_id=user_id)
    r_payload = JWTProvider.decode_token(raw_refresh)
    assert r_payload["sub"] == "42"
    assert r_payload["type"] == "refresh"
    assert r_payload["jti"] == jti

    token_hash = JWTProvider.compute_token_hash(raw_refresh)
    assert len(token_hash) == 64


def test_session_repository_lifecycle_and_reuse_defense():
    with SessionLocal() as db:
        # Create user for test
        email = f"session_test_{uuid.uuid4().hex[:8]}@smartsalary.in"
        user = User(
            email=email,
            hashed_password=PasswordHasher.hash_password("Pass123!"),
            full_name="Session Test User",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        repo = SessionRepository(db)
        raw_refresh, jti, expire = JWTProvider.create_refresh_token(user_id=user.id)
        session = repo.create_session(user_id=user.id, raw_refresh_token=raw_refresh, jti=jti, expires_at=expire)
        assert session.id is not None
        assert session.revoked_at is None

        # Rotate session
        new_raw, new_jti, new_expire = JWTProvider.create_refresh_token(user_id=user.id)
        new_session = repo.rotate_session(
            old_jti=jti, new_raw_refresh_token=new_raw, new_jti=new_jti, new_expires_at=new_expire
        )
        assert new_session.id is not None

        # Verify old session was revoked
        assert repo.get_active_session_by_jti(jti) is None
        assert repo.get_active_session_by_jti(new_jti) is not None

        # Token Reuse Test: Attempting to rotate using old_jti again must raise error and revoke all sessions
        with pytest.raises(ValueError) as exc:
            repo.rotate_session(
                old_jti=jti, new_raw_refresh_token="fake", new_jti=str(uuid.uuid4()), new_expires_at=new_expire
            )
        assert "reuse detected" in str(exc.value)

        # Active session count for user should now be 0
        active_sessions = repo.get_user_active_sessions(user.id)
        assert len(active_sessions) == 0
