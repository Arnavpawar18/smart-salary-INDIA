from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import check_db_connection
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
    """Salary Calculator Shell Page."""
    return templates.TemplateResponse(
        request=request,
        name="pages/calculator.html",
        context={"active_page": "calculator"},
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
