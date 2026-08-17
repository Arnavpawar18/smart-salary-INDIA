from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import check_db_connection, get_db
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.services.calculation_service import CalculationService
from app.services.metadata_service import get_schema_summary

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="SmartSalary — Salary, Tax, PF and Professional Tax Intelligence Platform for India (Python-First)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Static and Templates Directories
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


def get_current_health_dict():
    is_connected = check_db_connection()
    return {
        "status": "healthy" if is_connected else "degraded",
        "database": "connected" if is_connected else "unreachable",
        "timestamp": datetime.now(UTC),
    }


# ==========================================
# Web Page Routes (Jinja2 + HTMX)
# ==========================================


@app.get("/", response_class=HTMLResponse)
def page_home(request: Request):
    """Home / Platform Overview Page."""
    return templates.TemplateResponse(
        request=request,
        name="pages/home.html",
        context={"active_page": "home"},
    )


@app.get("/calculator", response_class=HTMLResponse)
def page_calculator(request: Request):
    """Salary Calculator Page."""
    return templates.TemplateResponse(
        request=request,
        name="pages/calculator.html",
        context={"active_page": "calculator"},
    )


@app.post("/calculator/calculate", response_class=HTMLResponse)
async def partial_calculator_calculate(
    request: Request,
    db: Session = Depends(get_db),
):
    """HTMX Endpoint returning calculation_result.html fragment."""
    form_data = await request.form()
    fy = form_data.get("financial_year", "2025-26")
    regime_str = form_data.get("regime", "NEW")
    state_code = form_data.get("state_code", "KA")
    gross_salary_raw = form_data.get("annual_gross_salary", "1200000")

    service = CalculationService(db)
    salary_inp = SalaryInput(
        financial_year=fy,
        annual_gross=Decimal(gross_salary_raw),
    )

    result = service.calculate_salary(
        salary_input=salary_inp,
        regime=TaxRegime(regime_str),
        state_code=state_code,
        persist=True,
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/calculation_result.html",
        context={"result": result.to_dict()},
    )


@app.get("/system-status", response_class=HTMLResponse)
def page_system_status(request: Request):
    """Full System Status & Architecture Explorer Page."""
    health_data = get_current_health_dict()
    schema_data = get_schema_summary()
    return templates.TemplateResponse(
        request=request,
        name="pages/system_status.html",
        context={
            "active_page": "system-status",
            "health": health_data,
            "schema": schema_data,
        },
    )


@app.get("/system-status/panel", response_class=HTMLResponse)
def partial_status_panel(request: Request):
    """HTMX Partial for Status Panel Refresh."""
    health_data = get_current_health_dict()
    schema_data = get_schema_summary()
    return templates.TemplateResponse(
        request=request,
        name="partials/status_panel.html",
        context={
            "health": health_data,
            "schema": schema_data,
        },
    )
