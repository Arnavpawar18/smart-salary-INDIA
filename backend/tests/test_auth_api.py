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
    unique_email = f"emp_{uuid.uuid4().hex[:8]}@smartsalary.in"
    password = "StrongPassword2026!"

    # 1. Register User
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
    assert reg_data["user"]["email"] == unique_email
    assert reg_data["user"]["role"] == "EMPLOYEE"
    assert "access_token" in reg_res.cookies
    assert "refresh_token" in reg_res.cookies

    # 2. Get Me (Authenticated)
    me_res = client.get("/api/v1/auth/me", cookies=reg_res.cookies)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == unique_email
    assert me_data["employee_details"]["first_name"] == "Arnav"

    # 3. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.cookies

    # 4. Refresh Token
    refresh_res = client.post("/api/v1/auth/refresh", cookies={"refresh_token": login_res.cookies["refresh_token"]})
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.cookies

    # 5. Logout
    logout_res = client.post("/api/v1/auth/logout", cookies={"refresh_token": refresh_res.cookies["refresh_token"]})
    assert logout_res.status_code == 200


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
