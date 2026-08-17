from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.auth import Permission, Role
from app.models.employee import Department, JobRole, State
from app.models.pf import PFRuleVersion
from app.models.pt import ProfessionalTaxRuleVersion
from app.models.tax import TaxPeriod, TaxRuleVersion

# 36 Indian States and Union Territories (28 States + 8 UTs) with GST/Official State Codes
INDIAN_STATES_DATA = [
    # States (28)
    {"code": "AP", "name": "Andhra Pradesh", "is_union_territory": False},
    {"code": "AR", "name": "Arunachal Pradesh", "is_union_territory": False},
    {"code": "AS", "name": "Assam", "is_union_territory": False},
    {"code": "BR", "name": "Bihar", "is_union_territory": False},
    {"code": "CG", "name": "Chhattisgarh", "is_union_territory": False},
    {"code": "GA", "name": "Goa", "is_union_territory": False},
    {"code": "GJ", "name": "Gujarat", "is_union_territory": False},
    {"code": "HR", "name": "Haryana", "is_union_territory": False},
    {"code": "HP", "name": "Himachal Pradesh", "is_union_territory": False},
    {"code": "JH", "name": "Jharkhand", "is_union_territory": False},
    {"code": "KA", "name": "Karnataka", "is_union_territory": False},
    {"code": "KL", "name": "Kerala", "is_union_territory": False},
    {"code": "MP", "name": "Madhya Pradesh", "is_union_territory": False},
    {"code": "MH", "name": "Maharashtra", "is_union_territory": False},
    {"code": "MN", "name": "Manipur", "is_union_territory": False},
    {"code": "ML", "name": "Meghalaya", "is_union_territory": False},
    {"code": "MZ", "name": "Mizoram", "is_union_territory": False},
    {"code": "NL", "name": "Nagaland", "is_union_territory": False},
    {"code": "OD", "name": "Odisha", "is_union_territory": False},
    {"code": "PB", "name": "Punjab", "is_union_territory": False},
    {"code": "RJ", "name": "Rajasthan", "is_union_territory": False},
    {"code": "SK", "name": "Sikkim", "is_union_territory": False},
    {"code": "TN", "name": "Tamil Nadu", "is_union_territory": False},
    {"code": "TS", "name": "Telangana", "is_union_territory": False},
    {"code": "TR", "name": "Tripura", "is_union_territory": False},
    {"code": "UP", "name": "Uttar Pradesh", "is_union_territory": False},
    {"code": "UK", "name": "Uttarakhand", "is_union_territory": False},
    {"code": "WB", "name": "West Bengal", "is_union_territory": False},
    # Union Territories (8)
    {"code": "AN", "name": "Andaman and Nicobar Islands", "is_union_territory": True},
    {"code": "CH", "name": "Chandigarh", "is_union_territory": True},
    {"code": "DH", "name": "Dadra and Nagar Haveli and Daman and Diu", "is_union_territory": True},
    {"code": "DL", "name": "Delhi", "is_union_territory": True},
    {"code": "JK", "name": "Jammu and Kashmir", "is_union_territory": True},
    {"code": "LA", "name": "Ladakh", "is_union_territory": True},
    {"code": "LD", "name": "Lakshadweep", "is_union_territory": True},
    {"code": "PY", "name": "Puducherry", "is_union_territory": True},
]

# Standard Corporate Departments
DEPARTMENTS_DATA = [
    {"code": "ENG", "name": "Engineering"},
    {"code": "PROD", "name": "Product"},
    {"code": "HR", "name": "Human Resources & Payroll"},
    {"code": "FIN", "name": "Finance & Accounting"},
    {"code": "OPS", "name": "Operations"},
    {"code": "LEGAL", "name": "Legal & Compliance"},
]

# Standard Job Roles
JOB_ROLES_DATA = [
    {"code": "SE", "title": "Software Engineer"},
    {"code": "SSE", "title": "Senior Software Engineer"},
    {"code": "EM", "title": "Engineering Manager"},
    {"code": "PM", "title": "Product Manager"},
    {"code": "HRM", "title": "HR Manager"},
    {"code": "FA", "title": "Financial Analyst"},
]

# System Roles and Permissions
ROLES_DATA = [
    {"name": "SUPER_ADMIN", "description": "Platform superuser with complete system access"},
    {"name": "HR_ADMIN", "description": "HR & Payroll Administrator"},
    {"name": "PAYROLL_OFFICER", "description": "Payroll processor and salary administrator"},
    {"name": "EMPLOYEE", "description": "Standard employee self-service user"},
    {"name": "AUDITOR", "description": "Read-only auditor with access to calculations and logs"},
]

PERMISSIONS_DATA = [
    {"code": "employee:read", "description": "Read employee profiles"},
    {"code": "employee:write", "description": "Create and update employee profiles"},
    {"code": "salary:read", "description": "Read salary structures and records"},
    {"code": "salary:write", "description": "Create and modify salary records"},
    {"code": "calculation:run", "description": "Execute tax and salary calculations"},
    {"code": "calculation:read", "description": "Read calculation runs and snapshots"},
    {"code": "payslip:upload", "description": "Upload payslip documents"},
    {"code": "payslip:read", "description": "Read payslip parse results"},
    {"code": "rules:read", "description": "Read statutory rule versions"},
    {"code": "rules:write", "description": "Create and update statutory rule versions"},
    {"code": "audit:read", "description": "Read system audit logs"},
]

# Strict Date Semantics for Statutory Tax Periods
TAX_PERIODS_DATA = [
    {
        "financial_year": "2024-25",
        "start_date": date(2024, 4, 1),
        "end_date": date(2025, 3, 31),
        "legacy_assessment_year": "2025-26",
    },
    {
        "financial_year": "2025-26",
        "start_date": date(2025, 4, 1),
        "end_date": date(2026, 3, 31),
        "legacy_assessment_year": "2026-27",
    },
    {
        "financial_year": "2026-27",
        "start_date": date(2026, 4, 1),
        "end_date": date(2027, 3, 31),
        "legacy_assessment_year": "2027-28",
    },
]


def seed_reference_data(db: Session) -> None:
    """
    Idempotent seeding of all reference and structural metadata.
    Safe to run multiple times without duplicating or corrupting data.
    """
    print("Starting idempotent reference data seeding...")

    # 1. Seed Roles
    for r_data in ROLES_DATA:
        existing = db.execute(select(Role).where(Role.name == r_data["name"])).scalar_one_or_none()
        if not existing:
            db.add(Role(**r_data))
    db.commit()

    # 2. Seed Permissions
    for p_data in PERMISSIONS_DATA:
        existing = db.execute(select(Permission).where(Permission.code == p_data["code"])).scalar_one_or_none()
        if not existing:
            db.add(Permission(**p_data))
    db.commit()

    # 3. Seed States / UTs (36)
    for s_data in INDIAN_STATES_DATA:
        existing = db.execute(select(State).where(State.code == s_data["code"])).scalar_one_or_none()
        if not existing:
            db.add(State(**s_data))
    db.commit()

    # 4. Seed Departments
    for d_data in DEPARTMENTS_DATA:
        existing = db.execute(select(Department).where(Department.code == d_data["code"])).scalar_one_or_none()
        if not existing:
            db.add(Department(**d_data))
    db.commit()

    # 5. Seed Job Roles
    for j_data in JOB_ROLES_DATA:
        existing = db.execute(select(JobRole).where(JobRole.code == j_data["code"])).scalar_one_or_none()
        if not existing:
            db.add(JobRole(**j_data))
    db.commit()

    # 6. Seed Tax Periods (FY 2024-25, 2025-26, 2026-27)
    for tp_data in TAX_PERIODS_DATA:
        existing = db.execute(select(TaxPeriod).where(TaxPeriod.financial_year == tp_data["financial_year"])).scalar_one_or_none()
        if not existing:
            db.add(TaxPeriod(**tp_data))
    db.commit()

    # 7. Seed Rule Version Shell Records (Ready for Phase 2 without fabricated rates)
    for tp_data in TAX_PERIODS_DATA:
        tp = db.execute(select(TaxPeriod).where(TaxPeriod.financial_year == tp_data["financial_year"])).scalar_one()

        # New Regime Shell
        new_vcode = f"TAX_NEW_{tp_data['financial_year'].replace('-', '_')}_v1"
        existing_new = db.execute(select(TaxRuleVersion).where(TaxRuleVersion.version_code == new_vcode)).scalar_one_or_none()
        if not existing_new:
            db.add(TaxRuleVersion(
                tax_period_id=tp.id,
                version_code=new_vcode,
                regime="NEW",
                effective_from=tp_data["start_date"],
                effective_to=tp_data["end_date"],
                status="ACTIVE",
            ))

        # Old Regime Shell
        old_vcode = f"TAX_OLD_{tp_data['financial_year'].replace('-', '_')}_v1"
        existing_old = db.execute(select(TaxRuleVersion).where(TaxRuleVersion.version_code == old_vcode)).scalar_one_or_none()
        if not existing_old:
            db.add(TaxRuleVersion(
                tax_period_id=tp.id,
                version_code=old_vcode,
                regime="OLD",
                effective_from=tp_data["start_date"],
                effective_to=tp_data["end_date"],
                status="ACTIVE",
            ))
    db.commit()

    # 8. Seed PF Rule Version Shells
    for fy in ["2024-25", "2025-26", "2026-27"]:
        pf_vcode = f"EPFO_STATUTORY_{fy.replace('-', '_')}_v1"
        existing_pf = db.execute(select(PFRuleVersion).where(PFRuleVersion.version_code == pf_vcode)).scalar_one_or_none()
        if not existing_pf:
            db.add(PFRuleVersion(
                version_code=pf_vcode,
                effective_from=date(int(fy[:4]), 4, 1),
                effective_to=date(int(fy[:4]) + 1, 3, 31),
                status="ACTIVE",
            ))
    db.commit()

    # 9. Seed Professional Tax Rule Version Shells (MH, KA)
    mh_state = db.execute(select(State).where(State.code == "MH")).scalar_one_or_none()
    if mh_state:
        pt_vcode = "PT_MH_STATUTORY_2024_25_v1"
        existing_pt = db.execute(select(ProfessionalTaxRuleVersion).where(ProfessionalTaxRuleVersion.version_code == pt_vcode)).scalar_one_or_none()
        if not existing_pt:
            db.add(ProfessionalTaxRuleVersion(
                state_id=mh_state.id,
                version_code=pt_vcode,
                effective_from=date(2024, 4, 1),
                status="ACTIVE",
            ))
    db.commit()

    print("Reference data seeding completed successfully.")


if __name__ == "__main__":
    with SessionLocal() as session:
        seed_reference_data(session)
