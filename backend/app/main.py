from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.api import api_router
from app.core.auth_middleware import get_current_user
from app.core.config import settings
from app.core.database import check_db_connection, get_db
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.models.auth import User
from app.models.employee import Employee
from app.presentation.money import format_inr
from app.presentation.quality import QualityClassifier
from app.repositories.session_repository import SessionRepository
from app.services.calculation_service import CalculationService
from app.services.dashboard_service import DashboardService
from app.services.metadata_service import get_schema_summary
from app.services.salary_service import SalaryService
from app.services.scenario_service import ScenarioService

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

# Register Global Jinja2 Custom Filters and Helpers
templates.env.filters["inr"] = format_inr
templates.env.globals["format_inr"] = format_inr

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
    """HTMX Endpoint returning minimal Level 1 result partial (result_minimal.html)."""
    form_data = await request.form()
    fy = form_data.get("financial_year", "2025-26")
    regime_str = form_data.get("regime", "NEW")
    state_code = form_data.get("state_code", "KA")
    is_quick_mode = form_data.get("is_quick_mode", "true").lower() == "true"

    # Handle monthly vs annual gross input
    if "monthly_gross_salary" in form_data and form_data["monthly_gross_salary"]:
        monthly_val = Decimal(form_data["monthly_gross_salary"])
        annual_gross = monthly_val * Decimal("12")
    else:
        annual_gross = Decimal(form_data.get("annual_gross_salary", "1200000"))

    # Parse optional detailed components
    basic_val = Decimal(form_data["basic_salary"]) * Decimal("12") if form_data.get("basic_salary") else None
    hra_val = Decimal(form_data["hra"]) * Decimal("12") if form_data.get("hra") else Decimal("0.00")
    sec_80c = Decimal(form_data.get("section_80c", "0")) or Decimal("0.00")
    sec_80d = Decimal(form_data.get("section_80d", "0")) or Decimal("0.00")

    has_custom = basic_val is not None or hra_val > 0 or sec_80c > 0 or sec_80d > 0

    salary_inp = SalaryInput(
        financial_year=fy,
        annual_gross=annual_gross,
        basic_salary=basic_val,
        hra=hra_val,
    )

    service = CalculationService(db)
    result = service.calculate_salary(
        salary_input=salary_inp,
        regime=TaxRegime(regime_str),
        state_code=state_code,
        persist=True,
    )

    quality = QualityClassifier.classify(
        is_quick_mode=is_quick_mode,
        has_custom_components=has_custom,
        is_supported=True,
    )
    metrics = SalaryService.compute_analytical_metrics(result)

    return templates.TemplateResponse(
        request=request,
        name="partials/result_minimal.html",
        context={
            "result": result.to_dict(),
            "quality": quality,
            "metrics": metrics,
            "calculation_id": 1,
        },
    )


@app.get("/calculator/{calculation_id}/how", response_class=HTMLResponse)
def partial_calculator_how(
    request: Request,
    calculation_id: int,
    db: Session = Depends(get_db),
):
    """HTMX Endpoint returning lazy-loaded Level 2 mathematical trace & ledger."""
    service = CalculationService(db)
    calc_data = service.get_calculation_by_id(calculation_id)
    if not calc_data:
        raise HTTPException(status_code=404, detail="Calculation not found")

    res = calc_data["result"]
    monthly_sched = SalaryService.generate_monthly_schedule(res)
    metrics = SalaryService.compute_analytical_metrics(res)

    return templates.TemplateResponse(
        request=request,
        name="partials/how_details.html",
        context={
            "result": res.to_dict(),
            "monthly_schedule": monthly_sched,
            "metrics": metrics,
            "calculation_id": calculation_id,
        },
    )


@app.post("/calculator/what-if", response_class=HTMLResponse)
async def partial_calculator_what_if(
    request: Request,
    db: Session = Depends(get_db),
):
    """HTMX Endpoint returning What-If raise simulator partial."""
    form_data = await request.form()
    salary_raw = Decimal(form_data.get("salary", "1200000"))
    fy = form_data.get("financial_year", "2025-26")
    state_code = form_data.get("state_code", "KA")
    regime_str = form_data.get("regime", "NEW")

    scenario_svc = ScenarioService(db)
    sim_data = scenario_svc.calculate_what_if_raises(
        base_salary=salary_raw,
        financial_year=fy,
        state_code=state_code,
        regime=TaxRegime(regime_str),
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/simulator_panel.html",
        context={"sim_data": sim_data},
    )


@app.get("/calculator/export/{calculation_id}", response_class=HTMLResponse)
def page_calculator_export(
    request: Request,
    calculation_id: int,
    db: Session = Depends(get_db),
):
    """Printable official salary summary page."""
    service = CalculationService(db)
    calc_data = service.get_calculation_by_id(calculation_id)
    if not calc_data:
        raise HTTPException(status_code=404, detail="Calculation not found")

    return templates.TemplateResponse(
        request=request,
        name="pages/print_summary.html",
        context={"result": calc_data["result"].to_dict()},
    )


@app.get("/dashboard", response_class=HTMLResponse)
def page_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticated Employee Financial Dashboard."""
    emp = db.scalar(select(Employee).where(Employee.user_id == current_user.id))
    if not emp:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    dashboard_svc = DashboardService(db)
    summary = dashboard_svc.get_employee_dashboard_summary(emp.id)

    return templates.TemplateResponse(
        request=request,
        name="pages/dashboard.html",
        context={
            "active_page": "dashboard",
            "employee": emp,
            "summary": summary,
        },
    )


@app.get("/profile/security", response_class=HTMLResponse)
def page_security_center(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticated Security Center & Active Session Manager."""
    session_repo = SessionRepository(db)
    sessions = session_repo.get_user_active_sessions(current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="pages/security_center.html",
        context={
            "active_page": "security",
            "current_user": current_user,
            "sessions": sessions,
        },
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
