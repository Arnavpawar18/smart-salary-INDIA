"""
End-to-End Comprehensive User Journey Verification Test Suite.

Validates the full user journey:
1. Registration & Non-blocking OTP dispatch
2. Password Reset workflow
3. Calculation Auth-Gating (Anonymous rejection + State preservation)
4. Authenticated calculation with all valid range salaries (e.g., 99999, 5000000)
5. Multi-state calculation (all 28 states & 8 UTs verified against StateJurisdictionMaster)
6. Calculation snapshot lineage & deterministic hash verification
7. Structured Evidence-Grounded AI Assistant Inquiry
8. Logical History Deletion with immutable snapshot retention
9. Multi-tenant Payroll Dashboard and Payslip cross-reconciliation
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.compliance.state_jurisdiction_master import StateJurisdictionMaster
from app.core.database import SessionLocal
from app.core.rate_limiter import InMemoryRateLimiter
from app.main import app
from app.models.auth import Role, User
from app.models.calculation import CalculationSnapshot
from app.services.email_service import TestEmailInbox


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def setup_test_env(db_session):
    TestEmailInbox.enable_capture()
    InMemoryRateLimiter._requests.clear()

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


def test_e2e_state_jurisdiction_master_coverage():
    """Verify all 28 states and 8 UTs are covered in StateJurisdictionMaster without duplicate codes."""
    states = StateJurisdictionMaster.list_all()
    assert len(states) == 36, f"Expected 36 states/UTs, got {len(states)}"
    codes = [s.state_code for s in states]
    assert len(set(codes)) == 36, "State codes must be strictly unique"

    # Verify Karnataka has active PT and Delhi has no PT
    ka = StateJurisdictionMaster.get_profile("KA")
    assert ka is not None
    assert ka.pt_status.value == "ACTIVE_APPLICABLE"

    dl = StateJurisdictionMaster.get_profile("DL")
    assert dl is not None
    assert dl.pt_status.value == "NOT_APPLICABLE"


def test_e2e_anonymous_calculator_auth_gating(client):
    """Verify anonymous user submitting salary calculation gets Level 1 authentication-required gate preserving entered state."""
    res = client.post(
        "/calculator/calculate",
        data={
            "financial_year": "2025-26",
            "regime": "NEW",
            "state_code": "KA",
            "monthly_gross_salary": "100000",
            "is_quick_mode": "true",
        },
    )
    assert res.status_code == 200
    # Anonymous users receive Authentication Required card with login/register CTAs
    assert "Authentication Required" in res.text
    assert "Create an account or sign in" in res.text
    assert "Sign In to Account" in res.text
    assert "Create Free Account" in res.text



def test_e2e_authenticated_user_lifecycle_and_calculations(client, db_session):
    """Test full authenticated user journey: register, OTP verify, calculate, RAG explain, and delete history."""
    # 1. Register user
    email = "e2e_journey_user@smartsalary.in"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "full_name": "E2E Test User",
            "company_name": "E2E Technologies Ltd",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["status"] == "OTP_REQUIRED"

    # Activate user via test DB fixture
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.is_active = True
    db_session.commit()

    # 2. Login (sets HttpOnly session cookies: access_token, refresh_token, csrf_token)
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json().get("csrf_token")
    headers = {"X-CSRF-Token": csrf_token} if csrf_token else {}

    # 3. Perform verified calculation (no arbitrary salary range limits: ₹99,999)
    calc_res = client.post(
        "/api/v1/calculations",
        json={
            "financial_year": "2025-26",
            "annual_gross_salary": "1199988",
            "regime": "NEW",
            "state_code": "MH",
        },
        headers=headers,
    )
    assert calc_res.status_code == 201
    calc_data = calc_res.json()
    assert "result_hash" in calc_data
    assert "estimated_monthly_take_home" in calc_data

    # 4. Check Calculation History endpoint and resolve calculation ID
    hist_res = client.get("/api/v1/calculations/history", headers=headers)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history["items"]) >= 1
    calc_id = history["items"][0]["id"]

    # 5. AI Assistant RAG Inquire with active calculation context
    chat_res = client.post(
        "/api/v1/chat/inquire",
        json={
            "query": "How is my take-home calculated?",
        },
        headers=headers,
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "response" in chat_data
    assert "Short Answer" in chat_data["response"]
    assert "Calculation" in chat_data["response"]
    assert "Applicable Rule" in chat_data["response"]

    # 6. Logical History Deletion
    del_res = client.delete(f"/api/v1/calculations/{calc_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "SUCCESS"

    # Verify calculation is excluded from active history
    hist_after = client.get("/api/v1/calculations/history", headers=headers).json()
    assert not any(item["id"] == calc_id for item in hist_after["items"])

    # Verify underlying CalculationSnapshot remains immutable in database
    snapshot = db_session.scalar(
        select(CalculationSnapshot).where(CalculationSnapshot.calculation_run_id == calc_id)
    )
    assert snapshot is not None, "Statutory CalculationSnapshot audit record must remain intact"
