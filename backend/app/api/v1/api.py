from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    calculations,
    chat,
    context,
    enterprise,
    health,
    metadata,
    payslips,
    rules,
    scenarios,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["System Health"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["Domain Schema Metadata"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Session Security"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI Financial Assistant & RAG"])
api_router.include_router(payslips.router, prefix="/payslips", tags=["Payslip Intelligence & Reconciliation"])
api_router.include_router(context.router, prefix="/ui", tags=["UI Context"])
api_router.include_router(calculations.router, prefix="/calculations", tags=["Financial Calculations"])
api_router.include_router(rules.router, prefix="/rules", tags=["Statutory Rules"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["Scenario Intelligence"])
api_router.include_router(enterprise.router, tags=["Enterprise Admin & Payroll"])
