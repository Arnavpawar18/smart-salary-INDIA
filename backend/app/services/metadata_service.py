from typing import Any

from app.models.base import Base

# Authoritative domain categorization for the exact 41 domain tables
DOMAIN_GROUPS: dict[str, list[str]] = {
    "auth": ["users", "roles", "permissions", "user_roles", "role_permissions", "user_sessions"],
    "employee": ["departments", "job_roles", "states", "employees", "taxpayer_profiles"],
    "salary": ["salary_records", "salary_components", "income_sources"],
    "calculation": ["calculation_runs", "calculation_snapshots", "calculation_traces", "calculation_line_items"],
    "tax": [
        "tax_periods",
        "tax_rule_versions",
        "tax_slabs",
        "tax_rebates",
        "tax_exemptions",
        "tax_deductions",
        "tax_surcharges",
        "tax_cess_rules",
        "tax_sources",
    ],
    "pf": ["pf_rule_versions", "pf_rules", "pf_interest_rules"],
    "professional_tax": ["professional_tax_rule_versions", "professional_tax_slabs"],
    "payslip": ["payslip_documents", "payslip_extractions", "payslip_validations"],
    "knowledge": ["knowledge_documents", "knowledge_chunks", "knowledge_sources"],
    "chat": ["chat_sessions", "chat_messages"],
    "audit": ["audit_logs"],
}


def get_schema_summary() -> dict[str, Any]:
    """
    Dynamically inspects the database schema and returns authoritative metadata.
    """
    # Count authoritative domain tables defined in metadata
    declared_tables = list(Base.metadata.tables.keys())

    # Financial years supported by Phase 1 reference data
    financial_years = ["2024-25", "2025-26", "2026-27"]

    return {
        "total_domain_tables": len(declared_tables),
        "domains": DOMAIN_GROUPS,
        "migration_revision": "001_initial_domain_schema",
        "financial_years": financial_years,
    }
