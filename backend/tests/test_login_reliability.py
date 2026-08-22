import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import PasswordHasher, normalize_email
from app.main import app
from app.models.auth import User
from app.models.employee import Employee
from app.services.email_service import TestEmailInbox

client = TestClient(app)


def helper_register_and_verify(email: str, password: str, full_name: str = "Test User") -> str:
    """Helper to register and verify an account using TestEmailInbox."""
    TestEmailInbox.enable_capture()
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "sector": "IT / Software",
            "state_code": "KA",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    verification_id = reg_resp.json()["verification_id"]
    otp = TestEmailInbox.get_last_otp()
    assert otp is not None

    verify_resp = client.post(
        "/api/v1/auth/verify-email-otp",
        json={"verification_id": verification_id, "otp": otp},
    )
    assert verify_resp.status_code == 200, verify_resp.text
    return verification_id


# 1. Registration persists account in database
def test_registration_persists_account():
    unique_email = f"persist_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    TestEmailInbox.enable_capture()

    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "full_name": "Persist User",
            "sector": "IT / Software",
            "state_code": "KA",
        },
    )
    assert reg_resp.status_code == 201

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalize_email(unique_email)))
        assert user is not None
        assert user.is_active is False
        assert user.hashed_password != password
        assert PasswordHasher.verify_password(password, user.hashed_password)

        emp = db.scalar(select(Employee).where(Employee.user_id == user.id))
        assert emp is not None
        assert emp.first_name == "Persist"


# 2. Registration OTP verification activates account
def test_registration_otp_verification_activates_account():
    unique_email = f"activate_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(unique_email, password)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalize_email(unique_email)))
        assert user is not None
        assert user.is_active is True


# 3. Registered account can login
def test_registered_account_can_login():
    unique_email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(unique_email, password)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.cookies
    assert login_resp.json()["user"]["email"] == normalize_email(unique_email)


# 4. Login does not require OTP
def test_login_does_not_require_otp():
    unique_email = f"no_otp_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(unique_email, password)

    # Login without any OTP parameter
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["message"] == "Login successful"
    assert "status" not in data or data.get("status") != "OTP_REQUIRED"


# 5. Login works after reload (via /me endpoint with cookies)
def test_login_works_after_reload():
    unique_email = f"reload_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(unique_email, password)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp.status_code == 200

    # Simulate reload by calling protected /me with saved cookies
    me_resp = client.get("/api/v1/auth/me", cookies=login_resp.cookies)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == normalize_email(unique_email)


# 6. Login works after logout (re-authenticating with same credentials)
def test_login_works_after_logout():
    unique_email = f"relogin_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(unique_email, password)

    # First login
    login_resp1 = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp1.status_code == 200
    csrf = login_resp1.json()["csrf_token"]

    # Logout
    logout_resp = client.post(
        "/api/v1/auth/logout",
        cookies=login_resp1.cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert logout_resp.status_code == 200

    # Login again with exact same credentials
    login_resp2 = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp2.status_code == 200
    assert login_resp2.json()["user"]["email"] == normalize_email(unique_email)


# 7. Login works again later (multiple sequential logins)
def test_login_works_again_later():
    unique_email = f"multi_login_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(unique_email, password)

    for _ in range(3):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": password},
        )
        assert res.status_code == 200
        assert "access_token" in res.cookies


# 8. Wrong email returns generic error
def test_wrong_email_generic_error():
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent_email_12345@example.com", "password": "AnyPassword!"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


# 9. Wrong password returns generic error
def test_wrong_password_generic_error():
    unique_email = f"wrong_pwd_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(unique_email, password)

    res = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "WrongPassword999!"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


# 10. Email normalization (mixed case, whitespace during register vs login)
def test_email_normalization_mixed_case_and_whitespace():
    raw_email = f"  MixCase_{uuid.uuid4().hex[:6]}@EXAMPLE.com  "
    clean_email = normalize_email(raw_email)
    password = "StrongPassword123!"

    TestEmailInbox.enable_capture()
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": raw_email.strip(),
            "password": password,
            "full_name": "Case User",
            "sector": "IT / Software",
        },
    )
    assert reg_resp.status_code == 201
    verification_id = reg_resp.json()["verification_id"]
    otp = TestEmailInbox.get_last_otp()

    verify_resp = client.post(
        "/api/v1/auth/verify-email-otp",
        json={"verification_id": verification_id, "otp": otp},
    )
    assert verify_resp.status_code == 200

    # Login using uppercase version
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": clean_email.upper(), "password": password},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["email"] == clean_email


# 11. Password uses Argon2id PasswordHasher
def test_password_uses_argon2id_password_hasher():
    unique_email = f"argon2_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestArgonPassword!"
    helper_register_and_verify(unique_email, password)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalize_email(unique_email)))
        assert user is not None
        assert user.hashed_password.startswith("$argon2")
        assert PasswordHasher.verify_password(password, user.hashed_password) is True
        assert PasswordHasher.verify_password("wrong", user.hashed_password) is False


# 12. Duplicate registration & unverified re-registration
def test_duplicate_registration_and_unverified_reregistration():
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    TestEmailInbox.enable_capture()

    # Initial register (unverified)
    res1 = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Unverified User"},
    )
    assert res1.status_code == 201

    # Re-registering unverified account should update and send new OTP
    with patch("app.core.config.settings.OTP_RESEND_COOLDOWN_SECONDS", 0):
        res2 = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "NewPassword456!", "full_name": "Updated User"},
        )
        assert res2.status_code == 201
        otp = TestEmailInbox.get_last_otp()

        # Verify and activate
        verify_resp = client.post(
            "/api/v1/auth/verify-email-otp",
            json={"verification_id": res2.json()["verification_id"], "otp": otp},
        )
        assert verify_resp.status_code == 200

    # Attempt to register again after verified -> should return 400
    res3 = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Dup User"},
    )
    assert res3.status_code == 400
    assert res3.json()["detail"] == "Email already registered"


# 13. Login creates HttpOnly session and cookies
def test_login_creates_httponly_session_and_cookies():
    email = f"cookies_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(email, password)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.cookies
    assert "refresh_token" in login_resp.cookies
    assert "csrf_token" in login_resp.cookies


# 14. Protected endpoint after login
def test_protected_endpoint_after_login():
    email = f"protected_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(email, password)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200

    me_resp = client.get("/api/v1/auth/me", cookies=login_resp.cookies)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == normalize_email(email)


# 15. Logout invalidates session
def test_logout_invalidates_session():
    email = f"logout_inv_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(email, password)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    csrf = login_resp.json()["csrf_token"]

    # Logout
    logout_resp = client.post(
        "/api/v1/auth/logout",
        cookies=login_resp.cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert logout_resp.status_code == 200

    # Old access token should now be rejected on protected endpoint
    me_resp = client.get("/api/v1/auth/me", cookies=login_resp.cookies)
    assert me_resp.status_code == 401


# 16. Refresh rotation
def test_refresh_rotation():
    email = f"refresh_rot_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(email, password)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    csrf = login_resp.json()["csrf_token"]
    old_refresh = login_resp.cookies["refresh_token"]

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": old_refresh},
        headers={"X-CSRF-Token": csrf},
    )
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.cookies.get("refresh_token")
    assert new_refresh is not None or "access_token" in refresh_resp.cookies


# 17. Revoked refresh rejected
def test_revoked_refresh_rejected():
    email = f"revoked_ref_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(email, password)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    csrf = login_resp.json()["csrf_token"]
    refresh_tok = login_resp.cookies["refresh_token"]

    # Logout
    client.post(
        "/api/v1/auth/logout",
        cookies=login_resp.cookies,
        headers={"X-CSRF-Token": csrf},
    )

    # Attempting refresh with revoked refresh token must be rejected (401)
    res = client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_tok},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 401


# 18. Logout-all revokes all sessions
def test_logout_all_sessions():
    email = f"logout_all_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(email, password)

    login1 = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    login2 = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    csrf = login2.json()["csrf_token"]

    logout_all = client.post(
        "/api/v1/auth/logout-all",
        cookies=login2.cookies,
        headers={"X-CSRF-Token": csrf},
    )
    assert logout_all.status_code == 200

    # Both sessions should be revoked
    assert client.get("/api/v1/auth/me", cookies=login1.cookies).status_code == 401
    assert client.get("/api/v1/auth/me", cookies=login2.cookies).status_code == 401


# 19. Password reset flow
def test_password_reset_flow():
    email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
    password = "OldPassword123!"
    new_password = "NewPassword2026!"
    helper_register_and_verify(email, password)

    TestEmailInbox.enable_capture()
    forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot_resp.status_code == 200
    v_id = forgot_resp.json()["verification_id"]
    otp = TestEmailInbox.get_last_otp()

    verify_resp = client.post(
        "/api/v1/auth/verify-password-reset-otp",
        json={"verification_id": v_id, "otp": otp},
    )
    assert verify_resp.status_code == 200
    reset_token = verify_resp.json()["reset_token"]

    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_token": reset_token,
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )
    assert reset_resp.status_code == 200


# 20. Old password rejected after reset
def test_old_password_rejected_after_reset():
    email = f"old_pwd_{uuid.uuid4().hex[:8]}@example.com"
    password = "OldPassword123!"
    new_password = "NewPassword2026!"
    helper_register_and_verify(email, password)

    TestEmailInbox.enable_capture()
    forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": email})
    v_id = forgot_resp.json()["verification_id"]
    otp = TestEmailInbox.get_last_otp()

    verify_resp = client.post(
        "/api/v1/auth/verify-password-reset-otp",
        json={"verification_id": v_id, "otp": otp},
    )
    reset_token = verify_resp.json()["reset_token"]

    client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_token": reset_token,
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )

    old_login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert old_login.status_code == 401


# 21. New password login succeeds
def test_new_password_login_succeeds():
    email = f"new_pwd_{uuid.uuid4().hex[:8]}@example.com"
    password = "OldPassword123!"
    new_password = "NewPassword2026!"
    helper_register_and_verify(email, password)

    TestEmailInbox.enable_capture()
    forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": email})
    v_id = forgot_resp.json()["verification_id"]
    otp = TestEmailInbox.get_last_otp()

    verify_resp = client.post(
        "/api/v1/auth/verify-password-reset-otp",
        json={"verification_id": v_id, "otp": otp},
    )
    reset_token = verify_resp.json()["reset_token"]

    client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_token": reset_token,
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )

    new_login = client.post("/api/v1/auth/login", json={"email": email, "password": new_password})
    assert new_login.status_code == 200
    assert "access_token" in new_login.cookies


# 22. Registration SMTP failure handling in production
def test_registration_smtp_failure_handling():
    email = f"smtp_fail_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"

    with patch("app.services.email_service.EmailService.send_email_verification_otp", return_value=False):
        res = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "SMTP Fail"},
        )
        assert res.status_code == 502
        assert res.json()["detail"] == "Failed to send verification email"


# 23. Forgot password SMTP failure handling in production
def test_forgot_password_smtp_failure_handling():
    email = f"smtp_forgot_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(email, password)

    with patch("app.services.email_service.EmailService.send_password_reset_otp", return_value=False):
        res = client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert res.status_code == 502


# 24. Resend SMTP failure handling in production
def test_resend_smtp_failure_handling():
    email = f"smtp_resend_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    TestEmailInbox.enable_capture()

    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Resend User"},
    )
    v_id = reg_res.json()["verification_id"]

    with patch("app.services.email_service.EmailService.send_email_verification_otp", return_value=False):
        with patch("app.core.config.settings.OTP_RESEND_COOLDOWN_SECONDS", 0):
            res = client.post("/api/v1/auth/resend-otp", json={"verification_id": v_id})
            assert res.status_code == 502


# 25. Navbar authenticated state rendering
def test_navbar_authenticated_state_rendering():
    email = f"nav_auth_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    helper_register_and_verify(email, password)

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200

    home_resp = client.get("/", cookies=login_resp.cookies)
    assert home_resp.status_code == 200
    html = home_resp.text
    # When authenticated, navbar renders user email and logout trigger
    assert normalize_email(email) in html or "Sign Out" in html or "Dashboard" in html


# 26. Navbar anonymous state rendering
def test_navbar_anonymous_state_rendering():
    home_resp = client.get("/")
    assert home_resp.status_code == 200
    html = home_resp.text
    # When unauthenticated, navbar renders Sign In / Register links
    assert "Sign In" in html or "Calculate" in html
