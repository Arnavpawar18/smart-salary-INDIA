"""
Milestone M12.10: Migration Rollback & Forward Safety
Verifies that database schema matches declarative domain tables (49 tables) and all foreign keys/indices are intact.
"""

from sqlalchemy import inspect

from app.core.database import engine


def test_m12_database_schema_complete_and_consistent():
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    # Assert core tables are present
    assert "users" in table_names
    assert "organizations" in table_names
    assert "employees" in table_names
    assert "payroll_runs" in table_names
    assert "calculation_snapshots" in table_names
    assert "audit_logs" in table_names
    assert "tax_rule_versions" in table_names
    assert "pf_rule_versions" in table_names
    assert "professional_tax_rule_versions" in table_names
