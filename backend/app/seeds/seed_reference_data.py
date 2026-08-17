from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import Permission, Role, role_permissions
from app.models.employee import Department, JobRole, State
from app.models.pf import PFRule, PFRuleVersion
from app.models.pt import ProfessionalTaxRuleVersion, ProfessionalTaxSlab
from app.models.tax import (
    TaxCessRule,
    TaxDeduction,
    TaxPeriod,
    TaxRebate,
    TaxRuleVersion,
    TaxSlab,
    TaxSurcharge,
)


def seed_reference_data(db: Session) -> None:
    """
    Idempotently seeds baseline statutory reference data and verified rule versions:
    - 5 Core Roles & 11 Permissions
    - 36 Indian States & Union Territories
    - 6 Standard Departments & 6 Job Roles
    - 3 Statutory Tax Periods (FY 2024-25, FY 2025-26, FY 2026-27)
    - Complete Verified Statutory Tax Slabs, Rebates, Deductions, Cess, and Surcharges
    - Complete Verified Statutory PF Contribution Rules
    - Complete Verified Professional Tax Slabs (KA, MH, TS)
    """

    # -------------------------------------------------------------
    # 1. System Roles (5)
    # -------------------------------------------------------------
    roles_data = [
        {"name": "SUPER_ADMIN", "description": "Full system access and platform administration"},
        {"name": "PAYROLL_ADMIN", "description": "Manages payroll structures, tax rules, and employee records"},
        {"name": "HR_MANAGER", "description": "Manages employee profiles and departmental allocations"},
        {"name": "EMPLOYEE", "description": "Standard user accessing self-service salary & tax insights"},
        {"name": "AUDITOR", "description": "Read-only access to audit logs and calculation traces"},
    ]
    for r in roles_data:
        existing = db.scalar(select(Role).where(Role.name == r["name"]))
        if not existing:
            db.add(Role(name=r["name"], description=r["description"]))
    db.flush()

    # -------------------------------------------------------------
    # 2. Permissions (11)
    # -------------------------------------------------------------
    permissions_data = [
        ("salary:calculate", "Execute deterministic salary and tax calculations"),
        ("salary:view_trace", "View step-by-step mathematical calculation trace"),
        ("employee:read", "View employee profiles and taxpayer settings"),
        ("employee:write", "Create or edit employee profiles and records"),
        ("rules:read", "View active and historical tax/PF/PT rule sets"),
        ("rules:manage", "Create, update, or retire statutory rule versions"),
        ("payslip:upload", "Upload payslip PDFs for extraction and validation"),
        ("payslip:read", "View payslip reconciliation and extraction data"),
        ("knowledge:query", "Search statutory tax knowledge base and citations"),
        ("audit:read", "View audit trail and immutability validation logs"),
        ("system:manage", "Configure system settings and organization master data"),
    ]
    for code, desc in permissions_data:
        existing = db.scalar(select(Permission).where(Permission.code == code))
        if not existing:
            db.add(Permission(code=code, description=desc))
    db.flush()

    # Link Super Admin permissions
    super_admin = db.scalar(select(Role).where(Role.name == "SUPER_ADMIN"))
    if super_admin:
        all_perms = db.scalars(select(Permission)).all()
        existing_perm_ids = {p.id for p in super_admin.permissions}
        for p in all_perms:
            if p.id not in existing_perm_ids:
                super_admin.permissions.append(p)
    db.flush()

    # -------------------------------------------------------------
    # 3. Indian States & Union Territories (36)
    # -------------------------------------------------------------
    states_data = [
        ("AP", "Andhra Pradesh", False),
        ("AR", "Arunachal Pradesh", False),
        ("AS", "Assam", False),
        ("BR", "Bihar", False),
        ("CG", "Chhattisgarh", False),
        ("GA", "Goa", False),
        ("GJ", "Gujarat", False),
        ("HR", "Haryana", False),
        ("HP", "Himachal Pradesh", False),
        ("JH", "Jharkhand", False),
        ("KA", "Karnataka", False),
        ("KL", "Kerala", False),
        ("MP", "Madhya Pradesh", False),
        ("MH", "Maharashtra", False),
        ("MN", "Manipur", False),
        ("ML", "Meghalaya", False),
        ("MZ", "Mizoram", False),
        ("NL", "Nagaland", False),
        ("OD", "Odisha", False),
        ("PB", "Punjab", False),
        ("RJ", "Rajasthan", False),
        ("SK", "Sikkim", False),
        ("TN", "Tamil Nadu", False),
        ("TS", "Telangana", False),
        ("TR", "Tripura", False),
        ("UP", "Uttar Pradesh", False),
        ("UK", "Uttarakhand", False),
        ("WB", "West Bengal", False),
        ("AN", "Andaman and Nicobar Islands", True),
        ("CH", "Chandigarh", True),
        ("DH", "Dadra and Nagar Haveli and Daman and Diu", True),
        ("DL", "Delhi", True),
        ("JK", "Jammu and Kashmir", True),
        ("LA", "Ladakh", True),
        ("LD", "Lakshadweep", True),
        ("PY", "Puducherry", True),
    ]
    for code, name, is_ut in states_data:
        existing = db.scalar(select(State).where(State.code == code))
        if not existing:
            db.add(State(code=code, name=name, is_union_territory=is_ut))
    db.flush()

    # -------------------------------------------------------------
    # 4. Departments & Job Roles
    # -------------------------------------------------------------
    departments_data = [
        ("ENG", "Engineering"),
        ("FIN", "Finance & Accounts"),
        ("HR", "Human Resources"),
        ("PROD", "Product Management"),
        ("OPS", "Operations"),
        ("EXEC", "Executive Leadership"),
    ]
    for code, name in departments_data:
        existing = db.scalar(select(Department).where(Department.code == code))
        if not existing:
            db.add(Department(code=code, name=name))
    db.flush()

    job_roles_data = [
        ("SE", "Software Engineer"),
        ("SSE", "Senior Software Engineer"),
        ("EM", "Engineering Manager"),
        ("FA", "Financial Analyst"),
        ("HRBP", "HR Business Partner"),
        ("DIR", "Director"),
    ]
    for code, title in job_roles_data:
        existing = db.scalar(select(JobRole).where(JobRole.code == code))
        if not existing:
            db.add(JobRole(code=code, title=title))
    db.flush()

    # -------------------------------------------------------------
    # 5. Tax Periods (FY 2024-25, FY 2025-26, FY 2026-27)
    # -------------------------------------------------------------
    tax_periods_data = [
        ("2024-25", "2025-26", date(2024, 4, 1), date(2025, 3, 31), False),
        ("2025-26", "2026-27", date(2025, 4, 1), date(2026, 3, 31), True),
        ("2026-27", "2027-28", date(2026, 4, 1), date(2027, 3, 31), False),
    ]
    for fy, ay, s_date, e_date, is_curr in tax_periods_data:
        existing = db.scalar(select(TaxPeriod).where(TaxPeriod.financial_year == fy))
        if not existing:
            db.add(
                TaxPeriod(
                    financial_year=fy,
                    assessment_year=ay,
                    start_date=s_date,
                    end_date=e_date,
                    is_current=is_curr,
                )
            )
    db.flush()

    # -------------------------------------------------------------
    # 6. Verified Tax Rule Versions, Slabs, Rebates, Deductions, Cess
    # -------------------------------------------------------------
    tax_periods_map = {tp.financial_year: tp.id for tp in db.scalars(select(TaxPeriod)).all()}

    # --- A. FY 2025-26 / FY 2026-27 NEW REGIME (DOC-ITD-AY2627-SALARIED) ---
    for fy_code in ["2025-26", "2026-27"]:
        v_code = f"TRV-{fy_code}-NEW-v1"
        trv = db.scalar(select(TaxRuleVersion).where(TaxRuleVersion.version_code == v_code))
        if not trv:
            trv = TaxRuleVersion(
                tax_period_id=tax_periods_map[fy_code],
                version_code=v_code,
                regime="NEW",
                effective_from=date(int(fy_code[:4]), 4, 1),
                effective_to=date(int(fy_code[:4]) + 1, 3, 31),
                status="ACTIVE",
            )
            db.add(trv)
            db.flush()

            # Slabs: 0-4L(0%), 4-8L(5%), 8-12L(10%), 12-16L(15%), 16-20L(20%), 20-24L(25%), >24L(30%)
            slabs = [
                (1, Decimal("0.00"), Decimal("400000.00"), Decimal("0.0000")),
                (2, Decimal("400000.00"), Decimal("800000.00"), Decimal("0.0500")),
                (3, Decimal("800000.00"), Decimal("1200000.00"), Decimal("0.1000")),
                (4, Decimal("1200000.00"), Decimal("1600000.00"), Decimal("0.1500")),
                (5, Decimal("1600000.00"), Decimal("2000000.00"), Decimal("0.2000")),
                (6, Decimal("2000000.00"), Decimal("2400000.00"), Decimal("0.2500")),
                (7, Decimal("2400000.00"), None, Decimal("0.3000")),
            ]
            for order, f_amt, t_amt, rate in slabs:
                db.add(TaxSlab(tax_rule_version_id=trv.id, slab_order=order, from_amount=f_amt, to_amount=t_amt, tax_rate=rate))

            # Rebate: Section 87A up to ₹60,000 for income <= ₹12 Lakh
            db.add(TaxRebate(tax_rule_version_id=trv.id, section="87A", threshold_taxable_income=Decimal("1200000.00"), max_rebate_amount=Decimal("60000.00")))

            # Standard Deduction: ₹75,000
            db.add(TaxDeduction(tax_rule_version_id=trv.id, section="16(ia)", name="Standard Deduction", max_limit=Decimal("75000.00")))

            # Cess: 4% Health & Education Cess
            db.add(TaxCessRule(tax_rule_version_id=trv.id, name="Health and Education Cess", cess_rate=Decimal("0.0400")))

            # Surcharges
            surcharges = [
                (Decimal("5000000.00"), Decimal("10000000.00"), Decimal("0.1000")),
                (Decimal("10000000.00"), Decimal("20000000.00"), Decimal("0.1500")),
                (Decimal("20000000.00"), None, Decimal("0.2500")),
            ]
            for f_inc, t_inc, s_rate in surcharges:
                db.add(TaxSurcharge(tax_rule_version_id=trv.id, from_income=f_inc, to_income=t_inc, surcharge_rate=s_rate, is_marginal_relief_applicable=True))

    # --- B. FY 2024-25 NEW REGIME (DOC-FINACT-2024) ---
    v_code_2425 = "TRV-2024-25-NEW-v1"
    trv_2425 = db.scalar(select(TaxRuleVersion).where(TaxRuleVersion.version_code == v_code_2425))
    if not trv_2425:
        trv_2425 = TaxRuleVersion(
            tax_period_id=tax_periods_map["2024-25"],
            version_code=v_code_2425,
            regime="NEW",
            effective_from=date(2024, 4, 1),
            effective_to=date(2025, 3, 31),
            status="ACTIVE",
        )
        db.add(trv_2425)
        db.flush()

        # Slabs 24-25: 0-3L(0%), 3-7L(5%), 7-10L(10%), 10-12L(15%), 12-15L(20%), >15L(30%)
        slabs_2425 = [
            (1, Decimal("0.00"), Decimal("300000.00"), Decimal("0.0000")),
            (2, Decimal("300000.00"), Decimal("700000.00"), Decimal("0.0500")),
            (3, Decimal("700000.00"), Decimal("1000000.00"), Decimal("0.1000")),
            (4, Decimal("1000000.00"), Decimal("1200000.00"), Decimal("0.1500")),
            (5, Decimal("1200000.00"), Decimal("1500000.00"), Decimal("0.2000")),
            (6, Decimal("1500000.00"), None, Decimal("0.3000")),
        ]
        for order, f_amt, t_amt, rate in slabs_2425:
            db.add(TaxSlab(tax_rule_version_id=trv_2425.id, slab_order=order, from_amount=f_amt, to_amount=t_amt, tax_rate=rate))

        db.add(TaxRebate(tax_rule_version_id=trv_2425.id, section="87A", threshold_taxable_income=Decimal("700000.00"), max_rebate_amount=Decimal("25000.00")))
        db.add(TaxDeduction(tax_rule_version_id=trv_2425.id, section="16(ia)", name="Standard Deduction", max_limit=Decimal("75000.00")))
        db.add(TaxCessRule(tax_rule_version_id=trv_2425.id, name="Health and Education Cess", cess_rate=Decimal("0.0400")))

    # --- C. OLD REGIME (ALL FYs) ---
    for fy_code in ["2024-25", "2025-26", "2026-27"]:
        v_code_old = f"TRV-{fy_code}-OLD-v1"
        trv_old = db.scalar(select(TaxRuleVersion).where(TaxRuleVersion.version_code == v_code_old))
        if not trv_old:
            trv_old = TaxRuleVersion(
                tax_period_id=tax_periods_map[fy_code],
                version_code=v_code_old,
                regime="OLD",
                effective_from=date(int(fy_code[:4]), 4, 1),
                effective_to=date(int(fy_code[:4]) + 1, 3, 31),
                status="ACTIVE",
            )
            db.add(trv_old)
            db.flush()

            # Old Slabs: 0-2.5L(0%), 2.5-5L(5%), 5-10L(20%), >10L(30%)
            old_slabs = [
                (1, Decimal("0.00"), Decimal("250000.00"), Decimal("0.0000")),
                (2, Decimal("250000.00"), Decimal("500000.00"), Decimal("0.0500")),
                (3, Decimal("500000.00"), Decimal("1000000.00"), Decimal("0.2000")),
                (4, Decimal("1000000.00"), None, Decimal("0.3000")),
            ]
            for order, f_amt, t_amt, rate in old_slabs:
                db.add(TaxSlab(tax_rule_version_id=trv_old.id, slab_order=order, from_amount=f_amt, to_amount=t_amt, tax_rate=rate))

            db.add(TaxRebate(tax_rule_version_id=trv_old.id, section="87A", threshold_taxable_income=Decimal("500000.00"), max_rebate_amount=Decimal("12500.00")))
            db.add(TaxDeduction(tax_rule_version_id=trv_old.id, section="16(ia)", name="Standard Deduction", max_limit=Decimal("50000.00")))
            db.add(TaxDeduction(tax_rule_version_id=trv_old.id, section="80C", name="Section 80C", max_limit=Decimal("150000.00")))
            db.add(TaxDeduction(tax_rule_version_id=trv_old.id, section="80D", name="Section 80D Health Insurance", max_limit=Decimal("25000.00")))
            db.add(TaxCessRule(tax_rule_version_id=trv_old.id, name="Health and Education Cess", cess_rate=Decimal("0.0400")))
    db.flush()

    # -------------------------------------------------------------
    # 7. Verified PF Contribution Rules (EPFO)
    # -------------------------------------------------------------
    for fy_code in ["2024-25", "2025-26", "2026-27"]:
        v_code_pf = f"PFRV-{fy_code}-v1"
        pfrv = db.scalar(select(PFRuleVersion).where(PFRuleVersion.version_code == v_code_pf))
        if not pfrv:
            pfrv = PFRuleVersion(
                version_code=v_code_pf,
                effective_from=date(int(fy_code[:4]), 4, 1),
                effective_to=date(int(fy_code[:4]) + 1, 3, 31),
                status="ACTIVE",
            )
            db.add(pfrv)
            db.flush()

            db.add(
                PFRule(
                    pf_rule_version_id=pfrv.id,
                    employee_epf_rate=Decimal("0.1200"),
                    employer_epf_rate=Decimal("0.0367"),
                    employer_eps_rate=Decimal("0.0833"),
                    employer_edli_rate=Decimal("0.0050"),
                    admin_charges_rate=Decimal("0.0050"),
                    statutory_wage_ceiling=Decimal("15000.00"),
                    eps_wage_ceiling=Decimal("15000.00"),
                    vpf_allowed=True,
                )
            )
    db.flush()

    # -------------------------------------------------------------
    # 8. Verified Professional Tax Slabs (KA, MH, TS)
    # -------------------------------------------------------------
    states_dict = {s.code: s.id for s in db.scalars(select(State)).all()}

    # Karnataka (KA)
    pt_ka = db.scalar(select(ProfessionalTaxRuleVersion).where(ProfessionalTaxRuleVersion.version_code == "PTRV-KA-v1"))
    if not pt_ka:
        pt_ka = ProfessionalTaxRuleVersion(
            state_id=states_dict["KA"],
            version_code="PTRV-KA-v1",
            effective_from=date(2024, 4, 1),
            status="ACTIVE",
        )
        db.add(pt_ka)
        db.flush()
        db.add(ProfessionalTaxSlab(pt_rule_version_id=pt_ka.id, slab_order=1, from_monthly_salary=Decimal("0.00"), to_monthly_salary=Decimal("14999.99"), monthly_tax_amount=Decimal("0.00"), february_tax_amount=Decimal("0.00"), gender_applicable="ALL"))
        db.add(ProfessionalTaxSlab(pt_rule_version_id=pt_ka.id, slab_order=2, from_monthly_salary=Decimal("15000.00"), to_monthly_salary=None, monthly_tax_amount=Decimal("200.00"), february_tax_amount=Decimal("200.00"), gender_applicable="ALL"))

    # Maharashtra (MH) - includes Feb adjustment ₹300
    pt_mh = db.scalar(select(ProfessionalTaxRuleVersion).where(ProfessionalTaxRuleVersion.version_code == "PTRV-MH-v1"))
    if not pt_mh:
        pt_mh = ProfessionalTaxRuleVersion(
            state_id=states_dict["MH"],
            version_code="PTRV-MH-v1",
            effective_from=date(2024, 4, 1),
            status="ACTIVE",
        )
        db.add(pt_mh)
        db.flush()
        db.add(ProfessionalTaxSlab(pt_rule_version_id=pt_mh.id, slab_order=1, from_monthly_salary=Decimal("0.00"), to_monthly_salary=Decimal("7500.00"), monthly_tax_amount=Decimal("0.00"), february_tax_amount=Decimal("0.00"), gender_applicable="ALL"))
        db.add(ProfessionalTaxSlab(pt_rule_version_id=pt_mh.id, slab_order=2, from_monthly_salary=Decimal("7501.00"), to_monthly_salary=Decimal("10000.00"), monthly_tax_amount=Decimal("175.00"), february_tax_amount=Decimal("175.00"), gender_applicable="ALL"))
        db.add(ProfessionalTaxSlab(pt_rule_version_id=pt_mh.id, slab_order=3, from_monthly_salary=Decimal("10001.00"), to_monthly_salary=None, monthly_tax_amount=Decimal("200.00"), february_tax_amount=Decimal("300.00"), gender_applicable="ALL"))

    # Telangana (TS)
    pt_ts = db.scalar(select(ProfessionalTaxRuleVersion).where(ProfessionalTaxRuleVersion.version_code == "PTRV-TS-v1"))
    if not pt_ts:
        pt_ts = ProfessionalTaxRuleVersion(
            state_id=states_dict["TS"],
            version_code="PTRV-TS-v1",
            effective_from=date(2024, 4, 1),
            status="ACTIVE",
        )
        db.add(pt_ts)
        db.flush()
        db.add(ProfessionalTaxSlab(pt_rule_version_id=pt_ts.id, slab_order=1, from_monthly_salary=Decimal("0.00"), to_monthly_salary=Decimal("15000.00"), monthly_tax_amount=Decimal("0.00"), february_tax_amount=Decimal("0.00"), gender_applicable="ALL"))
        db.add(ProfessionalTaxSlab(pt_rule_version_id=pt_ts.id, slab_order=2, from_monthly_salary=Decimal("15001.00"), to_monthly_salary=Decimal("20000.00"), monthly_tax_amount=Decimal("150.00"), february_tax_amount=Decimal("150.00"), gender_applicable="ALL"))
        db.add(ProfessionalTaxSlab(pt_rule_version_id=pt_ts.id, slab_order=3, from_monthly_salary=Decimal("20001.00"), to_monthly_salary=None, monthly_tax_amount=Decimal("200.00"), february_tax_amount=Decimal("200.00"), gender_applicable="ALL"))

    db.commit()
