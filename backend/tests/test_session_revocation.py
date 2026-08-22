import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.email_service import TestEmailInbox

client = TestClient(app)

@pytest.fixture(scope="function")
def create_user_and_login():
    email = "revocation_test@example.com"
    password = "StrongPass123!"
    # Enable test email capture mode
    TestEmailInbox.enable_capture()
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Revocation Test",
            "sector": "IT / Software",
            "occupation": "SOFTWARE_IT",
            "state_code": "KA",
            "employment_type": "FULL_TIME",
        },
    )
    assert register_resp.status_code == 201
    verification_id = register_resp.json()["verification_id"]
    # Retrieve OTP from test inbox (synchronous service)
    otp = TestEmailInbox.get_last_otp()

    verify_resp = client.post(
        "/api/v1/auth/verify-email-otp",
        json={"verification_id": verification_id, "otp": otp},
    )
    assert verify_resp.status_code == 200
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    cookies = login_resp.cookies
    csrf_token = login_resp.json()["csrf_token"]
    yield {"cookies": cookies, "csrf_token": csrf_token}
    # Cleanup: logout all sessions
    client.post(
        "/api/v1/auth/logout-all",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
    )

def test_revoke_individual_session(create_user_and_login):
    data = create_user_and_login
    sess_resp = client.get(
        "/api/v1/auth/sessions",
        cookies=data["cookies"],
        headers={"X-CSRF-Token": data["csrf_token"]},
    )
    assert sess_resp.status_code == 200
    sessions = sess_resp.json()
    assert len(sessions) >= 1
    session_id = sessions[0]["id"]
    revoke_resp = client.delete(
        f"/api/v1/auth/sessions/{session_id}",
        cookies=data["cookies"],
        headers={"X-CSRF-Token": data["csrf_token"]},
    )
    assert revoke_resp.status_code == 200
    # Refresh should now be rejected (old refresh token revoked)
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        cookies=data["cookies"],
        headers={"X-CSRF-Token": data["csrf_token"]},
    )
    assert refresh_resp.status_code == 401
