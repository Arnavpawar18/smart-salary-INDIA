from fastapi import APIRouter

from app.api.v1.endpoints import calculations, health, metadata, rules

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["System Health"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["Domain Schema Metadata"])
api_router.include_router(calculations.router, prefix="/calculations", tags=["Financial Calculations"])
api_router.include_router(rules.router, prefix="/rules", tags=["Statutory Rules"])
