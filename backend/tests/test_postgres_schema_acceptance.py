from sqlalchemy import func, inspect, select
from sqlalchemy.orm import sessionmaker

from app.core.database import engine as pg_engine
from app.models.auth import Permission, Role
from app.models.employee import Department, JobRole, State
from app.models.pf import PFRuleVersion
from app.models.pt import ProfessionalTaxRuleVersion
from app.models.tax import TaxPeriod, TaxRuleVersion
from app.seeds.seed_reference_data import seed_reference_data


def test_real_postgres_exact_49_domain_tables():
    """Verify that database contains all domain tables (including M8.1 audit ledger tables and verification_tokens)."""
    inspector = inspect(pg_engine)
    all_tables = inspector.get_table_names()
    domain_tables = [t for t in all_tables if t != "alembic_version"]

    assert len(domain_tables) == 52, f"Expected 52 domain tables, got {len(domain_tables)}"
    assert "user_sessions" in domain_tables
    assert "verification_tokens" in domain_tables
    assert "organizations" in domain_tables
    assert "payroll_runs" in domain_tables
    assert "tax_declarations" in domain_tables
    assert "statutory_compliance_events" in domain_tables


def test_real_postgres_constraints():
    """Verify 1:1 and foreign key constraints in database."""
    inspector = inspect(pg_engine)

    # 1. employees.user_id UNIQUE
    emp_uniques = inspector.get_unique_constraints("employees")
    emp_uniq_cols = [col for u in emp_uniques for col in u["column_names"]]
    assert "user_id" in emp_uniq_cols, "employees.user_id must be UNIQUE"

    # 2. taxpayer_profiles.employee_id UNIQUE NOT NULL
    tp_uniques = inspector.get_unique_constraints("taxpayer_profiles")
    tp_uniq_cols = [col for u in tp_uniques for col in u["column_names"]]
    assert "employee_id" in tp_uniq_cols, "taxpayer_profiles.employee_id must be UNIQUE"

    tp_cols = {c["name"]: c for c in inspector.get_columns("taxpayer_profiles")}
    assert tp_cols["employee_id"]["nullable"] is False, "taxpayer_profiles.employee_id must be NOT NULL"

    # 3. calculation_snapshots.calculation_run_id UNIQUE NOT NULL
    snap_uniques = inspector.get_unique_constraints("calculation_snapshots")
    snap_uniq_cols = [col for u in snap_uniques for col in u["column_names"]]
    assert "calculation_run_id" in snap_uniq_cols, "calculation_snapshots.calculation_run_id must be UNIQUE"


def test_real_postgres_financial_types():
    """Verify types: NUMERIC, JSONB, DATE, TIMESTAMPTZ."""
    inspector = inspect(pg_engine)

    sal_cols = {c["name"]: str(c["type"]) for c in inspector.get_columns("salary_records")}
    assert "NUMERIC" in sal_cols["annual_ctc"] or "DECIMAL" in sal_cols["annual_ctc"]

    pf_cols = {c["name"]: str(c["type"]) for c in inspector.get_columns("pf_rules")}
    assert "NUMERIC" in pf_cols["employee_epf_rate"] or "DECIMAL" in pf_cols["employee_epf_rate"]


def test_real_postgres_seed_idempotency():
    """Verify seeding with 0 duplicates on second run."""
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

        global_depts_1 = session.scalar(select(func.count(Department.id)).where(Department.organization_id.is_(None)))
        assert states_1 == 36
        assert roles_1 == 5
        assert perms_1 == 11
        assert global_depts_1 == 6
        assert jobs_1 == 6
        assert tps_1 == 3
        assert trv_1 == 6
        assert pf_1 == 3
        assert pt_1 == 6

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
