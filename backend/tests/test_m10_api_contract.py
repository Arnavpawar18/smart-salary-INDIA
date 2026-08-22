import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.core.security import JWTProvider
from app.main import app
from app.models.auth import User
from app.models.employee import Employee


def test_m10_api_status_codes_and_error_handling(db_session):
    client = TestClient(app)

    # 1. 401 Unauthorized for protected calculation route without auth
    anon_res = client.post(
        "/api/v1/calculations",
        json={"financial_year": "2025-26", "annual_gross_salary": 1000000.00, "state_code": "KA", "regime": "NEW"},
    )
    assert anon_res.status_code == 401

    # 2. Authenticate test user
    test_user = User(
        email=f"m10_contract_{uuid.uuid4().hex[:6]}@smartsalary.in",
        hashed_password="mock_hashed_password_2026",
        full_name="M10 Contract User",
        is_active=True,
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    emp = Employee(
        user_id=test_user.id,
        first_name="M10",
        last_name="User",
        email=test_user.email,
        date_of_joining=date(2025, 4, 1),
        employee_code=f"EMP-M10-{uuid.uuid4().hex[:4]}",
    )
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)

    token = JWTProvider.create_access_token(user_id=test_user.id, role="EMPLOYEE", employee_id=emp.id)
    client.cookies.set("access_token", token)

    # 3. 201 Created for valid calculation with authenticated user
    res_201 = client.post(
        "/api/v1/calculations",
        json={"financial_year": "2025-26", "annual_gross_salary": 1000000.00, "state_code": "KA", "regime": "NEW"},
    )
    assert res_201.status_code == 201
    assert "result_hash" in res_201.json()

    # 4. 422 Unprocessable Entity for invalid field type
    res_422 = client.post(
        "/api/v1/calculations",
        json={"financial_year": 2025, "annual_gross_salary": "NOT_A_NUMBER"},
    )
    assert res_422.status_code == 422

    # 5. 401 Unauthorized for protected route without auth (new client instance)
    anon_client = TestClient(app)
    res_401 = anon_client.get("/api/v1/calculations/history")
    assert res_401.status_code in (401, 403)

