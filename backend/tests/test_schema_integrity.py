from app.models.base import Base
from app.services.metadata_service import DOMAIN_GROUPS


def test_exact_49_domain_tables_registered():
    """Verify that exactly 49 domain tables are declared in Base.metadata."""
    declared_tables = Base.metadata.tables
    assert len(declared_tables) == 49, f"Expected exactly 49 tables, found {len(declared_tables)}"


def test_domain_groups_sum_to_49():
    """Verify that domain group mapping contains all 49 unique tables without duplication."""
    all_grouped_tables = []
    for domain, tables in DOMAIN_GROUPS.items():
        all_grouped_tables.extend(tables)

    assert len(all_grouped_tables) == 49, f"Expected 49 grouped tables, found {len(all_grouped_tables)}"
    assert len(set(all_grouped_tables)) == 49, "Duplicate table names detected across domain groups"

    # Assert 100% equivalence with Base.metadata
    assert set(all_grouped_tables) == set(Base.metadata.tables.keys())


def test_one_to_one_unique_constraints():
    """Verify database-level unique constraints for 1:1 and 0..1 relationships."""
    tables = Base.metadata.tables

    # 1. employees.user_id is unique (0..1 User -> Employee)
    employees_cols = {c.name: c for c in tables["employees"].columns}
    assert employees_cols["user_id"].unique is True

    # 2. taxpayer_profiles.employee_id is unique (1..1 Employee -> TaxpayerProfile)
    taxpayer_cols = {c.name: c for c in tables["taxpayer_profiles"].columns}
    assert taxpayer_cols["employee_id"].unique is True
    assert taxpayer_cols["employee_id"].nullable is False

    # 3. calculation_snapshots.calculation_run_id is unique (1..1 CalculationRun -> CalculationSnapshot)
    snapshot_cols = {c.name: c for c in tables["calculation_snapshots"].columns}
    assert snapshot_cols["calculation_run_id"].unique is True
    assert snapshot_cols["calculation_run_id"].nullable is False


def test_financial_numeric_types():
    """Verify that financial amounts use Numeric(18,2) and rates use Numeric(10,4)."""
    tables = Base.metadata.tables

    # Salary Records
    sal_rec = tables["salary_records"]
    assert str(sal_rec.columns["annual_ctc"].type) == "NUMERIC(18, 2)"
    assert str(sal_rec.columns["monthly_gross"].type) == "NUMERIC(18, 2)"

    # Tax Slabs
    tax_slabs = tables["tax_slabs"]
    assert str(tax_slabs.columns["from_amount"].type) == "NUMERIC(18, 2)"
    assert str(tax_slabs.columns["tax_rate"].type) == "NUMERIC(10, 4)"

    # PF Rules
    pf_rules = tables["pf_rules"]
    assert str(pf_rules.columns["employee_epf_rate"].type) == "NUMERIC(10, 4)"
    assert str(pf_rules.columns["statutory_wage_ceiling"].type) == "NUMERIC(18, 2)"
