from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_renders():
    """Verify GET / returns 200 and valid HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "SmartSalary" in response.text
    assert "Python-First" in response.text


def test_calculator_page_renders():
    """Verify GET /calculator returns 200 and calculator shell."""
    response = client.get("/calculator")
    assert response.status_code == 200
    assert "Salary &amp; Tax Calculator" in response.text or "Salary & Tax Calculator" in response.text
    assert "Annual CTC" in response.text


def test_system_status_page_renders():
    """Verify GET /system-status returns 200 and 40 domain tables architecture."""
    response = client.get("/system-status")
    assert response.status_code == 200
    assert "System Architecture Explorer" in response.text
    assert "40 Domain Tables" in response.text


def test_system_status_panel_htmx_partial():
    """Verify GET /system-status/panel returns 200 HTML fragment for HTMX swaps."""
    response = client.get("/system-status/panel")
    assert response.status_code == 200
    assert "FastAPI Server" in response.text
    assert "PostgreSQL" in response.text
