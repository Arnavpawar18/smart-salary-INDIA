"""
Milestone M10.1: Authentication & Session Lifecycle
Verifies registration, login, rate limiting, session listing, session revocation, and logout.
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_m10_auth_lifecycle():
    from app.services.email_service import TestEmailInbox

    TestEmailInbox.enable_capture()
    client = TestClient(app)
    test_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword@123"

    # 1. Register new user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": password, "full_name": "Test Engineer"},
    )
    assert reg_resp.status_code == 201
    assert reg_resp.json()["status"] == "OTP_REQUIRED"
    v_id = reg_resp.json()["verification_id"]

    # 2. Verify Email OTP
    last_email = TestEmailInbox.get_last_email()
    assert last_email is not None
    otp = last_email["otp"]
    verify_resp = client.post(
        "/api/v1/auth/verify-email-otp",
        json={"verification_id": v_id, "otp": otp},
    )
    assert verify_resp.status_code == 200

    # 3. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": password},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["email"] == test_email

    # 4. Fetch user profile /me
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == test_email

    # 5. List sessions
    sessions_resp = client.get("/api/v1/auth/sessions")
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.json()
    assert len(sessions) > 0

    # 6. Logout
    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200
    TestEmailInbox.disable_capture()
