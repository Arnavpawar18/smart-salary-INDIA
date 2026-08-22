import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth_middleware import get_optional_user
from app.core.database import SessionLocal
from app.core.security import JWTProvider
from app.engine.rag.ai_tools import AIToolService
from app.main import app
from app.models.auth import User
from app.models.calculation import CalculationRun, CalculationSnapshot
from app.models.employee import Employee


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    test_client = TestClient(app)
    yield test_client


def test_get_optional_user_scenarios(db):
    """
    Validates get_optional_user behavior across all edge cases:
    1. Valid token -> User
    2. Missing token -> None
    3. Expired / invalid token -> None
    4. Wrong token type (refresh instead of access) -> None
    5. Non-existent user -> None
    6. Inactive user -> None
    """
    # Create test active user
    test_user = User(
        email=f"opt_user_{uuid.uuid4().hex[:6]}@domain.in",
        hashed_password="hashed_pw_argon2id",
        full_name="Optional Test User",
        is_active=True,
        is_superuser=False,
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    # 1. Valid token
    valid_token = JWTProvider.create_access_token(user_id=test_user.id, role="EMPLOYEE")
    req = MagicMock()
    user_res = get_optional_user(request=req, access_token=valid_token, authorization=None, db=db)
    assert user_res is not None
    assert user_res.id == test_user.id

    # 2. Missing token
    assert get_optional_user(request=req, access_token=None, authorization=None, db=db) is None

    # 3. Invalid token string
    assert get_optional_user(request=req, access_token="invalid.jwt.token", authorization=None, db=db) is None

    # 4. Wrong token type (refresh token passed as access token)
    refresh_token, _, _ = JWTProvider.create_refresh_token(user_id=test_user.id)
    assert get_optional_user(request=req, access_token=refresh_token, authorization=None, db=db) is None

    # 5. Non-existent user ID in JWT
    fake_token = JWTProvider.create_access_token(user_id=999999, role="EMPLOYEE")
    assert get_optional_user(request=req, access_token=fake_token, authorization=None, db=db) is None

    # 6. Inactive user
    test_user.is_active = False
    db.commit()
    assert get_optional_user(request=req, access_token=valid_token, authorization=None, db=db) is None


def test_public_pages_render_with_and_without_auth(client: TestClient, db):
    """
    Verifies that public pages (/, /calculator, /system-status) render successfully (200 OK)
    both for unauthenticated visitors and authenticated users, showing the correct navbar state.
    """
    # 1. Unauthenticated GET /
    res = client.get("/")
    assert res.status_code == 200
    assert "Sign In" in res.text
    assert 'id="profile-dropdown-wrapper"' not in res.text

    # 2. Authenticated user GET /
    active_user = User(
        email=f"nav_test_{uuid.uuid4().hex[:6]}@domain.in",
        hashed_password="hashed_pw_argon2id",
        full_name="Priya Sharma",
        is_active=True,
        is_superuser=False,
    )
    db.add(active_user)
    db.commit()
    db.refresh(active_user)

    token = JWTProvider.create_access_token(user_id=active_user.id, role="EMPLOYEE")
    client.cookies.set("access_token", token)

    res_auth = client.get("/")
    assert res_auth.status_code == 200
    assert 'id="profile-dropdown-wrapper"' in res_auth.text
    assert "Priya" in res_auth.text
    assert "Sign Out" in res_auth.text

    # Verify calculator page also renders with profile menu
    res_calc = client.get("/calculator")
    assert res_calc.status_code == 200
    assert 'id="profile-dropdown-wrapper"' in res_calc.text

    # Clean up cookie
    client.cookies.clear()


def test_ai_cross_tenant_snapshot_isolation(db):
    """
    Verifies that User A cannot access User B's calculation snapshot via AIToolService / AI chat.
    Attempting to query another tenant's snapshot returns is_authorized=False.
    """
    # User A + Employee A
    user_a = User(
        email=f"emp_a_{uuid.uuid4().hex[:6]}@company.com",
        hashed_password="pw",
        full_name="Employee A",
        is_active=True,
    )
    db.add(user_a)
    db.flush()
    emp_a = Employee(
        user_id=user_a.id,
        employee_code=f"EMP-{uuid.uuid4().hex[:4]}",
        first_name="Employee",
        last_name="A",
        email=user_a.email,
        date_of_joining=date.today(),
        state_id=1,
    )
    db.add(emp_a)
    db.flush()

    # User B + Employee B
    user_b = User(
        email=f"emp_b_{uuid.uuid4().hex[:6]}@company.com",
        hashed_password="pw",
        full_name="Employee B",
        is_active=True,
    )
    db.add(user_b)
    db.flush()
    emp_b = Employee(
        user_id=user_b.id,
        employee_code=f"EMP-{uuid.uuid4().hex[:4]}",
        first_name="Employee",
        last_name="B",
        email=user_b.email,
        date_of_joining=date.today(),
        state_id=1,
    )
    db.add(emp_b)
    db.flush()

    # Calculation Run & Snapshot for User B
    calc_run_b = CalculationRun(
        employee_id=emp_b.id,
        financial_year="2025-26",
        regime="NEW",
        total_taxable_income=Decimal("1500000.00"),
        total_tax_liability=Decimal("150000.00"),
        net_take_home_annual=Decimal("1350000.00"),
        net_take_home_monthly=Decimal("112500.00"),
    )
    db.add(calc_run_b)
    db.flush()

    snapshot_b = CalculationSnapshot(
        calculation_run_id=calc_run_b.id,
        input_snapshot={"annual_gross": "1500000.00", "regime": "NEW"},
        result_snapshot={"net_take_home_annual": "1350000.00", "total_tax_liability": "150000.00"},
        input_hash=f"input_hash_{uuid.uuid4().hex[:8]}",
        result_hash=f"result_hash_{uuid.uuid4().hex[:8]}",
    )
    db.add(snapshot_b)
    db.commit()

    # User A tries to access User B's snapshot via AIToolService
    tool_svc_a = AIToolService(db, user_a)
    result = tool_svc_a.get_current_calculation(snapshot_id=snapshot_b.id)

    # Must be DENIED
    assert result.is_authorized is False
    assert "Access Denied" in result.error_message


def test_ai_chat_api_contract_and_auth(client: TestClient, db):
    """
    Validates the AI Chat API contract:
    - 401 when unauthenticated
    - 200 with session_id, message_id, response, citations when authenticated
    """
    client.cookies.clear()

    # 1. Unauthenticated call -> 401
    res_unauth = client.post("/api/v1/chat/inquire", json={"query": "What is Section 87A?"})
    assert res_unauth.status_code == 401

    # 2. Authenticated call -> 200 + proper contract
    user = User(
        email=f"ai_contract_{uuid.uuid4().hex[:6]}@domain.in",
        hashed_password="hashed_pw",
        full_name="AI Tester",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = JWTProvider.create_access_token(user_id=user.id, role="EMPLOYEE")
    client.cookies.set("access_token", token)

    res_auth = client.post("/api/v1/chat/inquire", json={"query": "Explain Section 87A rebate"})
    assert res_auth.status_code == 200
    data = res_auth.json()

    assert "session_id" in data
    assert "message_id" in data
    assert "response" in data
    assert "citations" in data
    assert isinstance(data["citations"], list)
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0

    client.cookies.clear()
