import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.rate_limiter import InMemoryRateLimiter
from app.core.security import PasswordHasher
from app.main import app
from app.models.auth import Role, User
from app.models.verification_token import VerificationToken
from app.services.email_service import TestEmailInbox


@pytest.fixture
def db_session():
    """Provides a fresh database session for test verification."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def setup_test_env(db_session):
    """Enable test email capture and reset rate limiters before each test."""
    TestEmailInbox.enable_capture()
    InMemoryRateLimiter._requests.clear()

    # Ensure EMPLOYEE role exists
    emp_role = db_session.scalar(select(Role).where(Role.name == "EMPLOYEE"))
    if not emp_role:
        emp_role = Role(name="EMPLOYEE", description="Default employee role")
        db_session.add(emp_role)
        db_session.commit()

    yield
    TestEmailInbox.disable_capture()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_registration_creates_inactive_user_and_sends_email_otp(client, db_session):
    """Registration creates is_active=False user, issues token, and dispatches email OTP."""
    payload = {
        "email": "test_register@smartsalary.in",
        "password": "SecurePassword123!",
        "full_name": "Test Engineer",
        "phone": "9999888877",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "OTP_REQUIRED"
    assert "verification_id" in data

    # Verify user in database is inactive
    user = db_session.scalar(select(User).where(User.email == "test_register@smartsalary.in"))
    assert user is not None
    assert user.is_active is False
    assert PasswordHasher.verify_password("SecurePassword123!", user.hashed_password)

    # Verify email was captured in TestEmailInbox
    last_email = TestEmailInbox.get_last_email()
    assert last_email is not None
    assert last_email["to_email"] == "test_register@smartsalary.in"
    assert len(last_email["otp"]) == 6


def test_unverified_user_cannot_login_and_gets_403(client, db_session):
    """Unverified account receives 403 Forbidden on login attempts."""
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "unverified@smartsalary.in",
            "password": "SecurePassword123!",
            "full_name": "Unverified User",
        },
    )

    # Attempt login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "unverified@smartsalary.in", "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 403
    assert "Email not verified" in login_res.json()["detail"]


def test_valid_email_otp_activates_user_and_allows_login(client, db_session):
    """Submitting valid OTP activates user and subsequent login succeeds."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "activate_me@smartsalary.in",
            "password": "SecurePassword123!",
            "full_name": "Active User",
        },
    )
    v_id = reg_res.json()["verification_id"]
    otp = TestEmailInbox.get_last_email()["otp"]

    # Verify OTP
    verify_res = client.post(
        "/api/v1/auth/verify-email-otp",
        json={"verification_id": v_id, "otp": otp},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "VERIFIED"

    # Verify user state in DB
    user = db_session.scalar(select(User).where(User.email == "activate_me@smartsalary.in"))
    assert user.is_active is True

    # Login now succeeds
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "activate_me@smartsalary.in", "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["message"] == "Login successful"


def test_invalid_email_otp_increments_attempts_and_locks_at_5(client, db_session):
    """Invalid OTP decrements remaining attempts and locks the token on 5th failure."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "brute_force@smartsalary.in",
            "password": "SecurePassword123!",
            "full_name": "Attacker",
        },
    )
    v_id = reg_res.json()["verification_id"]

    for attempt in range(1, 5):
        res = client.post("/api/v1/auth/verify-email-otp", json={"verification_id": v_id, "otp": "000000"})
        assert res.status_code == 400
        assert f"{5 - attempt} attempts remaining" in res.json()["detail"]

    # 5th attempt locks
    res5 = client.post("/api/v1/auth/verify-email-otp", json={"verification_id": v_id, "otp": "000000"})
    assert res5.status_code == 400
    assert "locked" in res5.json()["detail"].lower()

    # Even right OTP will now fail because token is locked
    correct_otp = TestEmailInbox.get_last_email()["otp"]
    res_locked = client.post("/api/v1/auth/verify-email-otp", json={"verification_id": v_id, "otp": correct_otp})
    assert res_locked.status_code == 400
    assert "locked" in res_locked.json()["detail"].lower()


def test_expired_email_otp_rejected(client, db_session):
    """Expired OTP tokens are rejected."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "expired@smartsalary.in",
            "password": "SecurePassword123!",
            "full_name": "Expired User",
        },
    )
    v_id = reg_res.json()["verification_id"]
    otp = TestEmailInbox.get_last_email()["otp"]

    # Manually backdate expiration in DB
    tok = db_session.scalar(select(VerificationToken).where(VerificationToken.verification_id == uuid.UUID(v_id)))
    tok.expires_at = datetime.now(UTC) - timedelta(minutes=10)
    db_session.commit()

    verify_res = client.post("/api/v1/auth/verify-email-otp", json={"verification_id": v_id, "otp": otp})
    assert verify_res.status_code == 400
    assert "expired" in verify_res.json()["detail"].lower()


def test_resend_invalidates_old_otp_and_enforces_cooldown(client, db_session):
    """Resend invalidates previous token and enforces 60-second cooldown."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "resend_test@smartsalary.in",
            "password": "SecurePassword123!",
            "full_name": "Resend User",
        },
    )
    v_id = reg_res.json()["verification_id"]
    old_otp = TestEmailInbox.get_last_email()["otp"]

    # Immediate resend should trigger 429 Cooldown
    resend_fail = client.post("/api/v1/auth/resend-otp", json={"verification_id": v_id})
    assert resend_fail.status_code == 429
    assert "Please wait" in resend_fail.json()["detail"]

    # Simulate passing 65 seconds
    tok = db_session.scalar(select(VerificationToken).where(VerificationToken.verification_id == uuid.UUID(v_id)))
    tok.last_resend_at = datetime.now(UTC) - timedelta(seconds=65)
    db_session.commit()

    resend_ok = client.post("/api/v1/auth/resend-otp", json={"verification_id": v_id})
    assert resend_ok.status_code == 200
    new_v_id = resend_ok.json()["verification_id"]
    new_otp = TestEmailInbox.get_last_email()["otp"]

    # Old OTP fails
    old_verify = client.post("/api/v1/auth/verify-email-otp", json={"verification_id": v_id, "otp": old_otp})
    assert old_verify.status_code == 400

    # New OTP succeeds
    new_verify = client.post("/api/v1/auth/verify-email-otp", json={"verification_id": new_v_id, "otp": new_otp})
    assert new_verify.status_code == 200


def test_two_stage_password_reset_flow(client, db_session):
    """Complete two-stage forgot password flow."""
    # 1. Create active user
    hashed = PasswordHasher.hash_password("OldPassword123!")
    user = User(
        email="reset_target@smartsalary.in",
        hashed_password=hashed,
        full_name="Target User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2. Request password reset
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": "reset_target@smartsalary.in"})
    assert forgot_res.status_code == 200
    v_id = forgot_res.json()["verification_id"]
    assert v_id is not None
    otp = TestEmailInbox.get_last_email()["otp"]

    # 3. Stage 1: Verify OTP and get reset_token
    verify_res = client.post(
        "/api/v1/auth/verify-password-reset-otp",
        json={"verification_id": v_id, "otp": otp},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "OTP_VERIFIED"
    reset_token = verify_res.json()["reset_token"]
    assert reset_token is not None

    # 4. Stage 2: Reset password
    reset_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_token": reset_token,
            "new_password": "NewSuperSecret456!",
            "confirm_password": "NewSuperSecret456!",
        },
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "PASSWORD_RESET_SUCCESS"

    # 5. Verify old password fails and new password succeeds
    login_old = client.post(
        "/api/v1/auth/login",
        json={"email": "reset_target@smartsalary.in", "password": "OldPassword123!"},
    )
    assert login_old.status_code == 401

    login_new = client.post(
        "/api/v1/auth/login",
        json={"email": "reset_target@smartsalary.in", "password": "NewSuperSecret456!"},
    )
    assert login_new.status_code == 200


def test_purpose_separation_email_otp_fails_for_password_reset(client, db_session):
    """An EMAIL_VERIFICATION token cannot be used to verify a PASSWORD_RESET."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "purpose_mix@smartsalary.in",
            "password": "SecurePassword123!",
            "full_name": "Mix User",
        },
    )
    v_id = reg_res.json()["verification_id"]
    otp = TestEmailInbox.get_last_email()["otp"]

    # Try verifying with password reset endpoint
    res = client.post(
        "/api/v1/auth/verify-password-reset-otp",
        json={"verification_id": v_id, "otp": otp},
    )
    assert res.status_code == 400
    assert "purpose" in res.json()["detail"].lower()


def test_zero_plaintext_otp_in_database(client, db_session):
    """Plaintext OTP is never stored in DB; only HMAC-SHA256 digest is stored."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "crypto_check@smartsalary.in",
            "password": "SecurePassword123!",
            "full_name": "Crypto User",
        },
    )
    raw_otp = TestEmailInbox.get_last_email()["otp"]

    token = db_session.scalar(select(VerificationToken).where(VerificationToken.email == "crypto_check@smartsalary.in"))
    assert token is not None
    assert token.token_hash != raw_otp
    assert len(token.token_hash) == 64  # SHA-256 hex length
    assert raw_otp not in token.token_hash
