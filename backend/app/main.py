from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.api import api_router
from app.api.v1.endpoints.employee_portal import get_employee_tax_center_data
from app.api.v1.endpoints.enterprise import (
    get_enterprise_dashboard,
    get_enterprise_tax_analytics,
    get_risk_engine_metrics,
    list_enterprise_audit_logs,
    list_pending_approvals,
)
from app.core.auth_middleware import get_current_user, get_optional_user
from app.core.config import settings
from app.core.database import check_db_connection, get_db
from app.core.limiter_exceptions import RateLimitExceeded
from app.core.redis_client import redis_lifespan
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.tenant_context import TenantContext, get_tenant_context
from app.engine.common.enums import TaxRegime
from app.engine.dto.salary_dto import SalaryInput
from app.models.auth import User
from app.models.calculation import CalculationRun
from app.models.employee import Employee
from app.presentation.money import format_inr
from app.presentation.quality import QualityClassifier
from app.repositories.session_repository import SessionRepository
from app.services.calculation_context_service import resolve_owned_calculation
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
    lifespan=redis_lifespan,
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle RateLimitExceeded and return a JSON response with appropriate headers."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


# OWASP ASVS Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Static and Templates Directories
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Register Global Jinja2 Custom Filters and Helpers
templates.env.filters["inr"] = format_inr
templates.env.globals["format_inr"] = format_inr


def _asset_version() -> str:
    watched_assets = [
        STATIC_DIR / "css" / "app.css",
        STATIC_DIR / "js" / "app.js",
        STATIC_DIR / "js" / "htmx.min.js",
    ]
    latest_mtime = max((p.stat().st_mtime_ns for p in watched_assets if p.exists()), default=0)
    return str(latest_mtime)


templates.env.globals["asset_version"] = _asset_version()

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
def page_home(request: Request, current_user=Depends(get_optional_user)):
    """Home / Platform Overview Page."""
    return templates.TemplateResponse(
        request=request,
        name="pages/home.html",
        context={"active_page": "home", "current_user": current_user},
    )


@app.get("/login", response_class=HTMLResponse)
def page_login(request: Request, current_user=Depends(get_optional_user)):
    """User Login Portal."""
    return templates.TemplateResponse(
        request=request,
        name="pages/auth.html",
        context={"active_page": "auth", "initial_mode": "login", "current_user": current_user},
    )


@app.get("/register", response_class=HTMLResponse)
def page_register(request: Request, current_user=Depends(get_optional_user)):
    """User Registration Portal."""
    return templates.TemplateResponse(
        request=request,
        name="pages/auth.html",
        context={"active_page": "auth", "initial_mode": "register", "current_user": current_user},
    )


@app.get("/forgot-password", response_class=HTMLResponse)
def page_forgot_password(request: Request, current_user=Depends(get_optional_user)):
    """Password Reset Portal."""
    return templates.TemplateResponse(
        request=request,
        name="pages/auth.html",
        context={"active_page": "auth", "initial_mode": "forgot", "current_user": current_user},
    )


@app.get("/calculator", response_class=HTMLResponse)
def page_calculator(request: Request, current_user=Depends(get_optional_user)):
    """Salary Calculator Page with Full 28 States + 8 UTs Coverage."""
    from app.core.compliance.state_jurisdiction_master import StateJurisdictionMaster

    states_list = StateJurisdictionMaster.list_all()
    return templates.TemplateResponse(
        request=request,
        name="pages/calculator.html",
        context={"active_page": "calculator", "current_user": current_user, "states": states_list},
    )


def _safe_decimal(value: str | None, default: str = "0") -> Decimal:
    """Convert a form field string to Decimal safely, treating empty/None as default."""
    if not value or not str(value).strip():
        return Decimal(default)
    try:
        return Decimal(str(value).strip())
    except Exception:
        return Decimal(default)


@app.post("/calculator/calculate", response_class=HTMLResponse)
async def partial_calculator_calculate(
    request: Request,
    current_user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    HTMX Endpoint returning Level 1 result partial.
    Calculates deterministic take-home for preview; links to user profile if authenticated.
    """
    form_data = await request.form()

    fy = form_data.get("financial_year", "2025-26")
    regime_str = form_data.get("regime", "NEW")
    state_code = form_data.get("state_code", "KA")
    is_quick_mode = form_data.get("is_quick_mode", "true").lower() == "true"

    # Handle monthly vs annual gross input (safe Decimal conversion, no arbitrary min/max limits)
    monthly_raw = form_data.get("monthly_gross_salary", "")
    if monthly_raw and str(monthly_raw).strip():
        monthly_val = _safe_decimal(monthly_raw)
        annual_gross = monthly_val * Decimal("12")
    else:
        annual_gross = _safe_decimal(form_data.get("annual_gross_salary", "1200000"), "1200000")

    # Parse optional detailed components
    basic_raw = form_data.get("basic_salary", "")
    basic_val = _safe_decimal(basic_raw) * Decimal("12") if basic_raw and str(basic_raw).strip() else None
    hra_val = _safe_decimal(form_data.get("hra", ""))
    sec_80c = _safe_decimal(form_data.get("section_80c", ""))
    sec_80d = _safe_decimal(form_data.get("section_80d", ""))

    has_custom = basic_val is not None or hra_val > 0 or sec_80c > 0 or sec_80d > 0

    salary_inp = SalaryInput(
        financial_year=fy,
        annual_gross=annual_gross,
        basic_salary=basic_val,
        hra=hra_val,
    )

    # Check Authentication Gate: Anonymous users receive auth required card with preserved parameters
    if not current_user:
        return templates.TemplateResponse(
            request=request,
            name="partials/result_auth_required.html",
            context={
                "form_data": form_data,
                "current_user": None,
            },
        )

    # Associate with user's Employee profile if authenticated
    emp = db.scalar(select(Employee).where(Employee.user_id == current_user.id))
    emp_id = emp.id if emp else None

    service = CalculationService(db)
    result = service.calculate_salary(
        salary_input=salary_inp,
        regime=TaxRegime(regime_str),
        state_code=state_code,
        employee_id=emp_id,
        persist=True,
    )

    # Get persisted calculation ID
    calc_run = (
        db.scalar(
            select(CalculationRun)
            .order_by(CalculationRun.id.desc())
        )
    )
    calc_id = calc_run.id if calc_run else 1

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
            "calculation_id": calc_id,
            "current_user": current_user,
        },
    )




@app.get("/calculator/{calculation_id}/how", response_class=HTMLResponse)
def partial_calculator_how(
    request: Request,
    calculation_id: int,
    current_user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """HTMX Endpoint returning lazy-loaded Level 2 mathematical trace & ledger from CalculationContext."""
    ctx = resolve_owned_calculation(db, calculation_id, user=current_user, allow_anonymous=True)
    res_dict = ctx.output_snapshot

    return templates.TemplateResponse(
        request=request,
        name="partials/how_details.html",
        context={
            "result": res_dict,
            "monthly_schedule": res_dict.get("monthly_schedule", {}),
            "metrics": res_dict.get("metrics", {}),
            "calculation_id": calculation_id,
            "calculation_context": ctx.to_dict(),
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
        name="partials/what_if_result.html",
        context={"sim_data": sim_data},
    )


@app.get("/calculator/export/{calculation_id}", response_class=HTMLResponse)
def page_calculator_export(
    request: Request,
    calculation_id: int,
    current_user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Printable official salary summary page strictly bound to CalculationContext."""
    ctx = resolve_owned_calculation(db, calculation_id, user=current_user, allow_anonymous=True)
    return templates.TemplateResponse(
        request=request,
        name="pages/print_summary.html",
        context={
            "result": ctx.output_snapshot,
            "calculation_id": calculation_id,
            "calculation_context": ctx.to_dict(),
        },
    )


@app.get("/calculator/export/{calculation_id}/json", response_class=JSONResponse)
def api_calculator_export_json(
    calculation_id: int,
    current_user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Authoritative CalculationContext JSON export."""
    ctx = resolve_owned_calculation(db, calculation_id, user=current_user, allow_anonymous=True)
    clean_data = ctx.to_dict()
    return JSONResponse(content=clean_data, headers={
        "Content-Disposition": f"attachment; filename=SmartSalary_Calculation_{calculation_id}.json"
    })


@app.get("/calculator/export/{calculation_id}/pdf")
def api_calculator_export_pdf(
    calculation_id: int,
    current_user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Authoritative PDF salary & tax statement generator."""
    from fastapi.responses import Response

    from app.services.pdf_generator_service import generate_calculation_pdf

    ctx = resolve_owned_calculation(db, calculation_id, user=current_user, allow_anonymous=True)
    pdf_bytes = generate_calculation_pdf(ctx)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=SmartSalary_Statement_{calculation_id}.pdf"
        }
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
            "current_user": current_user,
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


@app.get("/payslips", response_class=HTMLResponse)
def page_payslips(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticated Payslip Intelligence & Three-Way Reconciliation Portal."""
    from app.services.payslip_service import PayslipService

    service = PayslipService(db)
    docs = service.repo.list_employee_documents(current_user.employee_id) if current_user.employee_id else []

    return templates.TemplateResponse(
        request=request,
        name="pages/payslips.html",
        context={
            "active_page": "payslips",
            "current_user": current_user,
            "documents": docs,
        },
    )


@app.get("/system-status", response_class=HTMLResponse)
def page_system_status(request: Request, current_user=Depends(get_optional_user)):
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
            "current_user": current_user,
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


# ── Phase 5: Enterprise Portal Web Routes ───────────────────────────────────


@app.get("/enterprise", response_class=HTMLResponse)
def page_enterprise_dashboard(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Company Portal Overview Dashboard."""
    summary = get_enterprise_dashboard(ctx=ctx, db=db)
    return templates.TemplateResponse(
        request=request,
        name="pages/enterprise_dashboard.html",
        context={
            "active_subpage": "enterprise_overview",
            "current_user": current_user,
            "organization": ctx.organization,
            "tenant_role": ctx.role_name,
            "summary": summary,
        },
    )


@app.get("/enterprise/risk-engine", response_class=HTMLResponse)
def page_enterprise_risk(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI Risk Engine Dashboard."""
    metrics = get_risk_engine_metrics(ctx=ctx, db=db)
    return templates.TemplateResponse(
        request=request,
        name="pages/enterprise_risk_engine.html",
        context={
            "active_subpage": "enterprise_risk",
            "current_user": current_user,
            "organization": ctx.organization,
            "tenant_role": ctx.role_name,
            "metrics": metrics,
        },
    )


@app.get("/enterprise/tax-analytics", response_class=HTMLResponse)
def page_enterprise_analytics(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Corporate Tax Analytics Dashboard."""
    analytics = get_enterprise_tax_analytics(ctx=ctx, db=db)
    return templates.TemplateResponse(
        request=request,
        name="pages/enterprise_tax_analytics.html",
        context={
            "active_subpage": "enterprise_analytics",
            "current_user": current_user,
            "organization": ctx.organization,
            "tenant_role": ctx.role_name,
            "analytics": analytics,
        },
    )


@app.get("/enterprise/compliance-reports", response_class=HTMLResponse)
def page_enterprise_compliance(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compliance Reports & Filings."""
    return templates.TemplateResponse(
        request=request,
        name="pages/enterprise_compliance.html",
        context={
            "active_subpage": "enterprise_compliance",
            "current_user": current_user,
            "organization": ctx.organization,
            "tenant_role": ctx.role_name,
        },
    )


@app.get("/enterprise/approvals", response_class=HTMLResponse)
def page_enterprise_approvals(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin Approvals Workflow Center."""
    approvals = list_pending_approvals(ctx=ctx, db=db, status_filter="ALL")
    return templates.TemplateResponse(
        request=request,
        name="pages/enterprise_approvals.html",
        context={
            "active_subpage": "enterprise_approvals",
            "current_user": current_user,
            "organization": ctx.organization,
            "tenant_role": ctx.role_name,
            "approvals": approvals,
        },
    )


@app.get("/enterprise/audit-logs", response_class=HTMLResponse)
def page_enterprise_audit_logs(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Append-Only Audit Logs Viewer."""
    logs = list_enterprise_audit_logs(ctx=ctx, db=db, limit=50, offset=0)
    return templates.TemplateResponse(
        request=request,
        name="pages/enterprise_audit_logs.html",
        context={
            "active_subpage": "enterprise_audit",
            "current_user": current_user,
            "organization": ctx.organization,
            "tenant_role": ctx.role_name,
            "logs": logs,
        },
    )


# ── Phase 5: Employee Self-Service Web Routes ───────────────────────────────

@app.get("/employee", response_class=HTMLResponse)
def page_employee_overview(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Employee Self-Service Dashboard (Alias to /dashboard)."""
    return page_dashboard(request=request, current_user=current_user, db=db)


@app.get("/tax-center", response_class=HTMLResponse)
def page_tax_center(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Employee Tax Center & Declarations."""
    tax_data = get_employee_tax_center_data(current_user=current_user, db=db)
    return templates.TemplateResponse(
        request=request,
        name="pages/tax_center.html",
        context={
            "active_page": "tax-center",
            "current_user": current_user,
            "tax_data": tax_data,
        },
    )


@app.get("/help", response_class=HTMLResponse)
def page_help_center(request: Request, current_user=Depends(get_optional_user)):
    """Help & Resource Center."""
    return templates.TemplateResponse(
        request=request,
        name="pages/help.html",
        context={
            "active_page": "help",
            "current_user": current_user,
        },
    )

