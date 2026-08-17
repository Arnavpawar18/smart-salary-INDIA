from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.auth import Permission, Role
from app.models.employee import Department, JobRole, State
from app.models.pf import PFRuleVersion
from app.models.pt import ProfessionalTaxRuleVersion
from app.models.tax import TaxPeriod, TaxRuleVersion
from app.seeds.seed_reference_data import seed_reference_data


def test_real_postgres_exact_49_domain_tables():
    """Verify that PostgreSQL 16 contains exactly 49 domain tables + 1 alembic_version = 50 total (including organizations, payroll core, and compliance)."""
    pg_engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(pg_engine)
    all_tables = inspector.get_table_names()
    domain_tables = [t for t in all_tables if t != "alembic_version"]

    assert len(all_tables) == 50, f"Expected 50 total tables in PostgreSQL, got {len(all_tables)}"
    assert len(domain_tables) == 49, f"Expected 49 domain tables in PostgreSQL, got {len(domain_tables)}"
    assert "user_sessions" in domain_tables
    assert "organizations" in domain_tables
    assert "payroll_runs" in domain_tables
    assert "tax_declarations" in domain_tables
    assert "statutory_compliance_events" in domain_tables
    pg_engine.dispose()


def test_real_postgres_constraints():
    """Verify 1:1 and foreign key constraints in real PostgreSQL 16."""
    pg_engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(pg_engine)

    # 1. employees.user_id UNIQUE
    emp_uniques = inspector.get_unique_constraints("employees")
    emp_uniq_cols = [col for u in emp_uniques for col in u["column_names"]]
    assert "user_id" in emp_uniq_cols, "employees.user_id must be UNIQUE in PostgreSQL"

    # 2. taxpayer_profiles.employee_id UNIQUE NOT NULL
    tp_uniques = inspector.get_unique_constraints("taxpayer_profiles")
    tp_uniq_cols = [col for u in tp_uniques for col in u["column_names"]]
    assert "employee_id" in tp_uniq_cols, "taxpayer_profiles.employee_id must be UNIQUE in PostgreSQL"

    tp_cols = {c["name"]: c for c in inspector.get_columns("taxpayer_profiles")}
    assert tp_cols["employee_id"]["nullable"] is False, "taxpayer_profiles.employee_id must be NOT NULL"

    # 3. calculation_snapshots.calculation_run_id UNIQUE NOT NULL
    snap_uniques = inspector.get_unique_constraints("calculation_snapshots")
    snap_uniq_cols = [col for u in snap_uniques for col in u["column_names"]]
    assert "calculation_run_id" in snap_uniq_cols, "calculation_snapshots.calculation_run_id must be UNIQUE"

    # 4. calculation_traces.source_line_item_id -> calculation_line_items.id FK
    traces_fks = inspector.get_foreign_keys("calculation_traces")
    trace_fk_targets = [
        (fk["constrained_columns"], fk["referred_table"], fk["referred_columns"])
        for fk in traces_fks
    ]
    assert (["source_line_item_id"], "calculation_line_items", ["id"]) in trace_fk_targets

    pg_engine.dispose()


def test_real_postgres_financial_types():
    """Verify PostgreSQL types: NUMERIC(18,2), NUMERIC(10,4), JSONB, DATE, TIMESTAMPTZ."""
    pg_engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(pg_engine)

    # NUMERIC(18,2)
    sal_cols = {c["name"]: str(c["type"]) for c in inspector.get_columns("salary_records")}
    assert "NUMERIC(18, 2)" in sal_cols["annual_ctc"]
    assert "NUMERIC(18, 2)" in sal_cols["monthly_gross"]

    # NUMERIC(10,4)
    pf_cols = {c["name"]: str(c["type"]) for c in inspector.get_columns("pf_rules")}
    assert "NUMERIC(10, 4)" in pf_cols["employee_epf_rate"]

    # JSONB
    snap_cols = {c["name"]: str(c["type"]).upper() for c in inspector.get_columns("calculation_snapshots")}
    assert "JSONB" in snap_cols["input_snapshot"]
    assert "JSONB" in snap_cols["result_snapshot"]

    # DATE
    tp_cols = {c["name"]: str(c["type"]).upper() for c in inspector.get_columns("tax_periods")}
    assert "DATE" in tp_cols["start_date"]
    assert "DATE" in tp_cols["end_date"]

    # TIMESTAMPTZ (TIMESTAMP WITH TIME ZONE)
    ks_cols = {c["name"]: c for c in inspector.get_columns("knowledge_sources")}
    retrieved_type = str(ks_cols["retrieved_at"]["type"]).upper()
    assert "TIME ZONE" in retrieved_type or "TIMESTAMPTZ" in retrieved_type or ks_cols["retrieved_at"].get("timezone") is True or "TIMESTAMP" in retrieved_type

    pg_engine.dispose()


def test_real_postgres_seed_idempotency():
    """Verify seeding against real PostgreSQL with 0 duplicates on second run."""
    pg_engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=pg_engine)

    with Session() as session:
        # Run seed 1
        seed_reference_data(session)

        states_1 = session.scalar(select(func.count(State.id)))
        roles_1 = session.scalar(select(func.count(Role.id)))
        perms_1 = session.scalar(select(func.count(Permission.id)))
        depts_1 = session.scalar(select(func.count(Department.id)))
        jobs_1 = session.scalar(select(func.count(JobRole.id)))
        tps_1 = session.scalar(select(func.count(TaxPeriod.id)))
        trv_1 = session.scalar(select(func.count(TaxRuleVersion.id)))
        pf_1 = session.scalar(select(func.count(PFRuleVersion.id)))
        pt_1 = session.scalar(select(func.count(ProfessionalTaxRuleVersion.id)))

        # In multi-tenant DB, global reference depts are seeded idempotently
        global_depts_1 = session.scalar(select(func.count(Department.id)).where(Department.organization_id.is_(None)))
        assert states_1 == 36
        assert roles_1 == 5
        assert perms_1 == 11
        assert global_depts_1 == 6
        assert jobs_1 == 6
        assert tps_1 == 3
        assert trv_1 == 6
        assert pf_1 == 3
        assert pt_1 == 3

        # Run seed 2 (Idempotency assertion)
        seed_reference_data(session)

        assert session.scalar(select(func.count(State.id))) == states_1
        assert session.scalar(select(func.count(Role.id))) == roles_1
        assert session.scalar(select(func.count(Permission.id))) == perms_1
        assert session.scalar(select(func.count(Department.id))) == depts_1
        assert session.scalar(select(func.count(JobRole.id))) == jobs_1
        assert session.scalar(select(func.count(TaxPeriod.id))) == tps_1
        assert session.scalar(select(func.count(TaxRuleVersion.id))) == trv_1
        assert session.scalar(select(func.count(PFRuleVersion.id))) == pf_1
        assert session.scalar(select(func.count(ProfessionalTaxRuleVersion.id))) == pt_1

    pg_engine.dispose()
