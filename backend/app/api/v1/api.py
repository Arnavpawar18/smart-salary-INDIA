from fastapi import APIRouter

from app.api.v1.endpoints import health, metadata

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["Metadata"])
