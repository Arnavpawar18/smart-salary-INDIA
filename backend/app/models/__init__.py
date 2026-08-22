# Authoritative export of all 40 domain models for SmartSalary India.
from app.models.audit import AuditLog
from app.models.auth import Permission, Role, User, role_permissions, user_roles
from app.models.base import Base, TimestampMixin
from app.models.calculation import (
    CalculationLineItem,
    CalculationRun,
    CalculationSnapshot,
    CalculationTrace,
)
from app.models.chat import ChatMessage, ChatSession
from app.models.compliance import StatutoryComplianceEvent, TaxDeclaration, TaxDeclarationItem
from app.models.employee import Department, Employee, JobRole, State, TaxpayerProfile
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeSource
from app.models.organization import Organization, OrganizationMembership
from app.models.payroll import PayrollPeriod, PayrollRun, PayrollRunItem
from app.models.payslip import PayslipDocument, PayslipExtraction, PayslipValidation
from app.models.pf import PFInterestRule, PFRule, PFRuleVersion
from app.models.pt import ProfessionalTaxRuleVersion, ProfessionalTaxSlab
from app.models.salary import IncomeSource, SalaryComponent, SalaryRecord
from app.models.session import UserSession
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
from app.models.verification_token import VerificationToken

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
    "VerificationToken",
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
