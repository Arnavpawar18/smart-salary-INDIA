
from pydantic import BaseModel, ConfigDict


class SchemaSummaryResponse(BaseModel):
    total_domain_tables: int
    domains: dict[str, list[str]]
    migration_revision: str
    financial_years: list[str]

    model_config = ConfigDict(from_attributes=True)
