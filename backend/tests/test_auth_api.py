import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_csrf_token_endpoint():
    res = client.get("/api/v1/auth/csrf-token")
    assert res.status_code == 200
    data = res.json()
    assert "csrf_token" in data
    assert "." in data["csrf_token"]


def test_auth_register_login_refresh_logout_flow():
    from app.services.email_service import TestEmailInbox

    TestEmailInbox.enable_capture()
    unique_email = f"emp_{uuid.uuid4().hex[:8]}@smartsalary.in"
    password = "StrongPassword2026!"

    # 1. Register User (Receives OTP requirement)
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "full_name": "Arnav Pawar",
            "phone": "9876543210",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["status"] == "OTP_REQUIRED"
    assert "verification_id" in reg_data
    v_id = reg_data["verification_id"]

    # 2. Verify Email OTP
    last_email = TestEmailInbox.get_last_email()
    assert last_email is not None
    otp = last_email["otp"]
    verify_res = client.post(
        "/api/v1/auth/verify-email-otp",
        json={"verification_id": v_id, "otp": otp},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "VERIFIED"

    # 3. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.cookies
    assert login_res.json()["user"]["email"] == unique_email

    # 4. Get Me (Authenticated)
    client.cookies.update(login_res.cookies)
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == unique_email
    assert me_data["employee_details"]["first_name"] == "Arnav"

    # 5. Refresh Token
    client.cookies.set("refresh_token", login_res.cookies["refresh_token"])
    refresh_res = client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.cookies

    # 6. Logout
    client.cookies.set("refresh_token", refresh_res.cookies["refresh_token"])
    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
    TestEmailInbox.disable_capture()


def test_auth_unauthenticated_and_wrong_password_denial():
    # Unauthenticated /me
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401

    # Wrong password login
    res_wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@smartsalary.in", "password": "WrongPassword!"},
    )
    assert res_wrong.status_code == 401
