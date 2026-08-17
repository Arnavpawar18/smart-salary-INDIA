from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auth import Permission, Role
from app.models.employee import Department, JobRole, State
from app.models.pf import PFRuleVersion
from app.models.pt import ProfessionalTaxRuleVersion
from app.models.tax import TaxPeriod, TaxRuleVersion
from app.seeds.seed_reference_data import seed_reference_data


def test_seed_reference_data_idempotent(db_session: Session):
    """
    Verify that executing the seed script multiple times is strictly idempotent:
    produces exact counts with zero duplicates.
    """
    # First seed run
    seed_reference_data(db_session)

    states_count_1 = db_session.scalar(select(func.count(State.id)))
    roles_count_1 = db_session.scalar(select(func.count(Role.id)))
    perms_count_1 = db_session.scalar(select(func.count(Permission.id)))
    depts_count_1 = db_session.scalar(select(func.count(Department.id)))
    jobs_count_1 = db_session.scalar(select(func.count(JobRole.id)))
    tax_periods_count_1 = db_session.scalar(select(func.count(TaxPeriod.id)))
    tax_rules_count_1 = db_session.scalar(select(func.count(TaxRuleVersion.id)))
    pf_rules_count_1 = db_session.scalar(select(func.count(PFRuleVersion.id)))
    pt_rules_count_1 = db_session.scalar(select(func.count(ProfessionalTaxRuleVersion.id)))

    # Assert expected reference counts
    assert states_count_1 == 36  # 28 States + 8 UTs
    assert roles_count_1 == 5
    assert perms_count_1 == 11
    assert depts_count_1 == 6
    assert jobs_count_1 == 6
    assert tax_periods_count_1 == 3
    assert tax_rules_count_1 == 6  # 2 regimes * 3 FYs
    assert pf_rules_count_1 == 3
    assert pt_rules_count_1 == 3  # KA, MH, TS verified states

    # Second seed run (Idempotency assertion)
    seed_reference_data(db_session)

    assert db_session.scalar(select(func.count(State.id))) == states_count_1
    assert db_session.scalar(select(func.count(Role.id))) == roles_count_1
    assert db_session.scalar(select(func.count(Permission.id))) == perms_count_1
    assert db_session.scalar(select(func.count(Department.id))) == depts_count_1
    assert db_session.scalar(select(func.count(JobRole.id))) == jobs_count_1
    assert db_session.scalar(select(func.count(TaxPeriod.id))) == tax_periods_count_1
    assert db_session.scalar(select(func.count(TaxRuleVersion.id))) == tax_rules_count_1
    assert db_session.scalar(select(func.count(PFRuleVersion.id))) == pf_rules_count_1
    assert db_session.scalar(select(func.count(ProfessionalTaxRuleVersion.id))) == pt_rules_count_1


def test_tax_period_date_semantics(db_session: Session):
    """
    Verify strict statutory date semantics for FY 2024-25, FY 2025-26, FY 2026-27.
    """
    seed_reference_data(db_session)

    p24 = db_session.execute(select(TaxPeriod).where(TaxPeriod.financial_year == "2024-25")).scalar_one()
    assert p24.start_date == date(2024, 4, 1)
    assert p24.end_date == date(2025, 3, 31)
    assert p24.legacy_assessment_year == "2025-26"

    p25 = db_session.execute(select(TaxPeriod).where(TaxPeriod.financial_year == "2025-26")).scalar_one()
    assert p25.start_date == date(2025, 4, 1)
    assert p25.end_date == date(2026, 3, 31)
    assert p25.legacy_assessment_year == "2026-27"

    p26 = db_session.execute(select(TaxPeriod).where(TaxPeriod.financial_year == "2026-27")).scalar_one()
    assert p26.start_date == date(2026, 4, 1)
    assert p26.end_date == date(2027, 3, 31)
    assert p26.legacy_assessment_year == "2027-28"
