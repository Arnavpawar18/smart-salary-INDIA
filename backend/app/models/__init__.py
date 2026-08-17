"""
Authoritative export of all 40 domain models for SmartSalary India.
Total Domain Tables: Exactly 40.
"""

# 11. Audit (1 table)
from app.models.audit import AuditLog

# 1. Auth & RBAC (6 tables)
from app.models.auth import Permission, Role, User, role_permissions, user_roles
from app.models.base import Base, TimestampMixin

# 4. Calculation & Audit Engine (4 tables)
from app.models.calculation import (
    CalculationLineItem,
    CalculationRun,
    CalculationSnapshot,
    CalculationTrace,
)

# 10. Chat Foundation (2 tables)
from app.models.chat import ChatMessage, ChatSession

# Enterprise Tax Declarations & Statutory Compliance (3 tables)
from app.models.compliance import StatutoryComplianceEvent, TaxDeclaration, TaxDeclarationItem

# 2. Employee & Organizational (7 tables)
from app.models.employee import Department, Employee, JobRole, State, TaxpayerProfile

# 9. Knowledge & RAG Repository (3 tables)
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeSource
from app.models.organization import Organization, OrganizationMembership

# Enterprise Payroll Core (3 tables)
from app.models.payroll import PayrollPeriod, PayrollRun, PayrollRunItem

# 8. Payslip Domain (3 tables)
from app.models.payslip import PayslipDocument, PayslipExtraction, PayslipValidation

# 6. Provident Fund Domain (3 tables)
from app.models.pf import PFInterestRule, PFRule, PFRuleVersion

# 7. Professional Tax Domain (2 tables)
from app.models.pt import ProfessionalTaxRuleVersion, ProfessionalTaxSlab

# 3. Salary & Income (3 tables)
from app.models.salary import IncomeSource, SalaryComponent, SalaryRecord
from app.models.session import UserSession

# 5. Tax Engine Domain (9 tables)
from app.models.tax import (
    TaxCessRule,
    TaxDeduction,
    TaxExemption,
    TaxPeriod,
    TaxRebate,
    TaxRuleVersion,
    TaxSlab,
    TaxSource,
    TaxSurcharge,
)

__all__ = [
    "Base",
    "TimestampMixin",
    # Auth
    "User",
    "Role",
    "Permission",
    "user_roles",
    "role_permissions",
    "UserSession",
    # Enterprise & Organization
    "Organization",
    "OrganizationMembership",
    # Payroll Core
    "PayrollPeriod",
    "PayrollRun",
    "PayrollRunItem",
    # Compliance & Declarations
    "TaxDeclaration",
    "TaxDeclarationItem",
    "StatutoryComplianceEvent",
    # Employee
    "Department",
    "JobRole",
    "State",
    "Employee",
    "TaxpayerProfile",
    # Salary
    "SalaryRecord",
    "SalaryComponent",
    "IncomeSource",
    # Calculation
    "CalculationRun",
    "CalculationSnapshot",
    "CalculationTrace",
    "CalculationLineItem",
    # Tax
    "TaxPeriod",
    "TaxRuleVersion",
    "TaxSlab",
    "TaxRebate",
    "TaxExemption",
    "TaxDeduction",
    "TaxSurcharge",
    "TaxCessRule",
    "TaxSource",
    # PF
    "PFRuleVersion",
    "PFRule",
    "PFInterestRule",
    # PT
    "ProfessionalTaxRuleVersion",
    "ProfessionalTaxSlab",
    # Payslip
    "PayslipDocument",
    "PayslipExtraction",
    "PayslipValidation",
    # Knowledge
    "KnowledgeDocument",
    "KnowledgeChunk",
    "KnowledgeSource",
    # Chat
    "ChatSession",
    "ChatMessage",
    # Audit
    "AuditLog",
]
