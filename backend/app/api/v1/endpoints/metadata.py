from fastapi import APIRouter

from app.schemas.metadata import SchemaSummaryResponse
from app.services.metadata_service import get_schema_summary

router = APIRouter()


@router.get("/schema-summary", response_model=SchemaSummaryResponse)
def schema_summary() -> SchemaSummaryResponse:
    """
    Read-only dynamic domain schema and migration metadata.
    """
    summary = get_schema_summary()
    return SchemaSummaryResponse(**summary)
