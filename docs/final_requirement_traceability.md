# SmartSalary India — Final Requirement Traceability Matrix (RTM)

| Project | SmartSalary India (Production Release) |
| :--- | :--- |
| **Release Candidate** | v1.0.0-PROD-STITCH |
| **Statutory Scope** | AY 2026-27, AY 2025-26, Section 115BAC (Finance Act 2025), EPFO Act 1952, ESIC Act 1948, 28 States + 8 UTs PT Schedules |
| **Engine Invariants** | Code Calculates, Laws Authorize, AI Explains |
| **Verification Baseline** | 301/301 Pytest Tests Passed (100%), 120,000/120,000 Validation Scenarios (100%), Ruff Lint (0 Errors) |

---

## 1. Master Architectural Requirement Traceability

| REQ-ID | Category | Implementation Files | Test Suite Reference | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-01** | **Python-First Statutory Engine** | `backend/app/engine/core/calculator.py`, `backend/app/engine/tax/section_115bac.py` | `test_calculator_service.py`, `test_phase1_tax_engine.py` | **PASS (100%)** |
| **REQ-02** | **New Tax Regime (Section 115BAC)** | `backend/app/engine/tax/section_115bac.py`, `backend/app/engine/tax/rebate_87a.py` | `test_tax_engine_slabs.py`, `test_section_87a_rebate.py` | **PASS (100%)** |
| **REQ-03** | **Old Tax Regime Engine** | `backend/app/engine/tax/old_regime_calculator.py` | `test_old_vs_new_regime.py`, `test_deductions_80c_80d.py` | **PASS (100%)** |
| **REQ-04** | **Rebate Under Section 87A** | `backend/app/engine/tax/rebate_87a.py` | `test_section_87a_rebate.py`, `test_marginal_relief_87a.py` | **PASS (100%)** |
| **REQ-05** | **Surcharge & Marginal Relief** | `backend/app/engine/tax/surcharge_calculator.py` | `test_surcharge_and_marginal_relief.py` | **PASS (100%)** |
| **REQ-06** | **Health & Education Cess** | `backend/app/engine/tax/cess_calculator.py` | `test_tax_engine_slabs.py` | **PASS (100%)** |
| **REQ-07** | **Section 288B Rounding Rules** | `backend/app/engine/common/rounding.py` | `test_tax_engine_slabs.py`, `run_100k_system_validation.py` | **PASS (100%)** |
| **REQ-08** | **Provident Fund (EPF & EPS)** | `backend/app/engine/pf/epf_calculator.py` | `test_pf_engine.py` | **PASS (100%)** |
| **REQ-09** | **Employee State Insurance (ESI)** | `backend/app/engine/esi/esi_calculator.py` | `test_esi_engine.py` | **PASS (100%)** |
| **REQ-10** | **Professional Tax Engine (28+8)** | `backend/app/engine/pt/state_pt_calculator.py`, `backend/app/core/compliance/state_jurisdiction_master.py` | `test_pt_engine.py`, `test_state_pt_matrix.py` | **PASS (100%)** |
| **REQ-11** | **Salary Component Structure** | `backend/app/engine/salary/normalizer.py` | `test_salary_service.py` | **PASS (100%)** |
| **REQ-12** | **Salary Normalizer Invariants** | `backend/app/engine/salary/normalizer.py` | `test_m10_salary_inputs.py` | **PASS (100%)** |
| **REQ-13** | **Dual Engine Regime Comparison** | `backend/app/services/salary_service.py` | `test_old_vs_new_regime.py` | **PASS (100%)** |
| **REQ-14** | **Temporal & Fiscal Year Versioning** | `backend/app/models/tax.py`, `backend/app/seeds/seed_reference_data.py` | `test_tax_period_transitions.py` | **PASS (100%)** |
| **REQ-15** | **State Jurisdiction Master** | `backend/app/core/compliance/state_jurisdiction_master.py` | `test_jurisdiction_master.py` | **PASS (100%)** |
| **REQ-16** | **Deterministic Oracle Validation** | `backend/app/engine/oracle/independent_oracle.py` | `run_100k_system_validation.py` | **PASS (100%)** |
| **REQ-17** | **Immutable SHA-256 Provenance** | `backend/app/models/calculation.py`, `backend/app/services/calculation_service.py` | `test_calculation_snapshot_provenance.py` | **PASS (100%)** |
| **REQ-18** | **Single Source Calculation Context** | `backend/app/services/calculation_context_service.py` | `test_calculation_context_ab_isolation.py` | **PASS (100%)** |
| **REQ-19** | **Mathematical Traceability & Ledger** | `backend/app/models/calculation.py`, `backend/app/engine/core/calculator.py` | `test_phase3_ui_endpoints.py` | **PASS (100%)** |
| **REQ-20** | **Cryptographic Audit Log Ledger** | `backend/app/models/audit.py`, `backend/app/services/audit_service.py` | `test_audit_service.py`, `test_enterprise_api.py` | **PASS (100%)** |
| **REQ-21** | **Multi-Tenant Enterprise Isolation** | `backend/app/core/tenant_context.py`, `backend/app/models/organization.py` | `test_tenant_isolation.py`, `test_enterprise_rbac_and_idor.py` | **PASS (100%)** |
| **REQ-22** | **Role-Based Access Control (RBAC)** | `backend/app/models/auth.py`, `backend/app/core/auth_middleware.py` | `test_auth_api.py`, `test_enterprise_rbac_and_idor.py` | **PASS (100%)** |
| **REQ-23** | **Anti-IDOR Security Enforcement** | `backend/app/services/calculation_context_service.py`, `backend/app/api/v1/endpoints/enterprise.py` | `test_calculation_context_ab_isolation.py`, `test_enterprise_rbac_and_idor.py` | **PASS (100%)** |
| **REQ-24** | **Maker-Checker Separation of Duties** | `backend/app/api/v1/endpoints/enterprise.py` | `test_enterprise_rbac_and_idor.py` | **PASS (100%)** |
| **REQ-25** | **Cryptographic Session Management** | `backend/app/core/security.py`, `backend/app/core/auth_middleware.py`, `backend/app/models/session.py` | `test_session_revocation.py`, `test_auth_primitives.py` | **PASS (100%)** |
| **REQ-26** | **HMAC-SHA256 OTP System** | `backend/app/services/otp_service.py`, `backend/app/api/v1/endpoints/auth.py` | `test_email_otp_auth.py` | **PASS (100%)** |
| **REQ-27** | **OWASP ASVS Security Hardening** | `backend/app/core/security_headers.py`, `backend/app/core/auth_middleware.py` | `test_m6_security_hardening.py` | **PASS (100%)** |
| **REQ-28** | **Distributed Sliding-Window Limiter**| `backend/app/core/limiter.py`, `backend/app/core/redis_rate_limiter.py`, `backend/app/core/rate_limiter.py` | `test_rate_limiter_core.py` | **PASS (100%)** |
| **REQ-29** | **Domain Database Schema (40 Tables)**| `backend/app/models/__init__.py`, `backend/app/models/` | `test_domain_models.py` | **PASS (100%)** |
| **REQ-30** | **Database Seeding & Reference Data** | `backend/app/seeds/seed_reference_data.py` | `test_reference_data_seeding.py` | **PASS (100%)** |
| **REQ-31** | **Batch Enterprise Payroll Engine** | `backend/app/models/payroll.py`, `backend/app/api/v1/endpoints/enterprise.py` | `test_m11_company_e2e.py`, `test_enterprise_api.py` | **PASS (100%)** |
| **REQ-32** | **Tax Declaration Proof Verification** | `backend/app/models/compliance.py`, `backend/app/api/v1/endpoints/enterprise.py` | `test_enterprise_api.py`, `test_enterprise_rbac_and_idor.py` | **PASS (100%)** |
| **REQ-33** | **Statutory Compliance Filings** | `backend/app/models/compliance.py`, `backend/app/api/v1/endpoints/enterprise.py` | `test_enterprise_api.py` | **PASS (100%)** |
| **REQ-34** | **Enterprise Risk Analytics Engine** | `backend/app/api/v1/endpoints/enterprise.py` | `test_enterprise_rbac_and_idor.py` | **PASS (100%)** |
| **REQ-35** | **Employee Self-Service Portal** | `backend/app/api/v1/endpoints/employee_portal.py`, `backend/app/templates/pages/employee_dashboard.html` | `test_enterprise_rbac_and_idor.py` | **PASS (100%)** |
| **REQ-36** | **Three-Way Payslip Reconciliation** | `backend/app/engine/rag/llm_provider.py`, `backend/app/models/payslip.py` | `test_final_user_journey_e2e.py` | **PASS (100%)** |
| **REQ-37** | **Tamper-Evident QR Payslips** | `backend/app/presentation/money.py`, `backend/app/templates/pages/print_summary.html` | `test_phase3_ui_endpoints.py` | **PASS (100%)** |
| **REQ-38** | **Hybrid RAG Knowledge Retrieval** | `backend/app/engine/rag/retriever.py`, `backend/app/models/knowledge.py` | `test_rag_retrieval.py` | **PASS (100%)** |
| **REQ-39** | **Strict Grounding & Anti-Hallucination**| `backend/app/engine/rag/citation_validator.py`, `backend/app/services/ai_service.py` | `test_auth_state_and_ai_integration.py` | **PASS (100%)** |
| **REQ-40** | **Statutory Source Card Display** | `backend/app/engine/rag/source_display_service.py` | `test_auth_state_and_ai_integration.py` | **PASS (100%)** |
| **REQ-41** | **Deterministic LLM Responses** | `backend/app/engine/rag/llm_provider.py` | `test_auth_state_and_ai_integration.py` | **PASS (100%)** |
| **REQ-42** | **Full-Featured Calculator UI** | `backend/app/templates/pages/calculator.html`, `backend/app/templates/partials/result_card.html` | `test_phase3_ui_endpoints.py` | **PASS (100%)** |
| **REQ-43** | **Interactive Rupee Journey Flow** | `backend/app/templates/pages/index.html` | `test_design_system_propagation.py` | **PASS (100%)** |
| **REQ-44** | **What-If Raise & Bonus Simulator** | `backend/app/services/scenario_service.py`, `backend/app/api/v1/endpoints/scenarios.py` | `test_phase3_ui_endpoints.py` | **PASS (100%)** |
| **REQ-45** | **Company Executive Dashboard** | `backend/app/templates/pages/enterprise_dashboard.html` | `test_phase3_ui_endpoints.py` | **PASS (100%)** |
| **REQ-46** | **Centralized Stitch Design Tokens** | `backend/app/static/css/app.css` | `test_design_system_propagation.py` | **PASS (100%)** |
| **REQ-47** | **Deterministic Dark & Light Modes** | `backend/app/static/css/app.css`, `backend/app/templates/base.html` | `test_design_system_propagation.py` | **PASS (100%)** |
| **REQ-48** | **High-Density Fintech Tables** | `backend/app/static/css/app.css`, `backend/app/templates/pages/enterprise_approvals.html` | `test_design_system_propagation.py` | **PASS (100%)** |
| **REQ-49** | **Responsive Mobile Drawer & Navbar**| `backend/app/templates/base.html`, `backend/app/static/css/app.css` | `test_design_system_propagation.py` | **PASS (100%)** |
| **REQ-50** | **Subsystem Health & Telemetry** | `backend/app/api/v1/endpoints/health.py`, `backend/app/core/observability.py` | `test_health.py` | **PASS (100%)** |
| **REQ-51** | **Automated Validation Harness (120k)**| `backend/scripts/run_100k_system_validation.py` | `run_100k_system_validation.py` | **PASS (100%)** |
| **REQ-52** | **End-to-End Enterprise Journey** | `backend/tests/test_final_user_journey_e2e.py` | `test_final_user_journey_e2e.py` | **PASS (100%)** |
| **REQ-53** | **Zero Lint Defect Standard** | `backend/app/`, `backend/tests/` | `ruff check backend/app backend/tests` | **PASS (100%)** |

---

## 2. Statutory Authority Rule Lineage

- **Income Tax Department / Central Board of Direct Taxes (CBDT)**:
  - *Statute*: Income-tax Act, 1961 as amended by Finance Act, 2025.
  - *Sections*: Section 115BAC (New Tax Regime Default), Section 87A (Rebate & Marginal Relief up to ₹7,00,000 / ₹12,00,000), Section 80C/80D/80CCD (Old Regime Deductions), Section 288B (Rounding of Tax to Nearest ₹10).
- **Employees' Provident Fund Organisation (EPFO India)**:
  - *Statute*: Employees' Provident Funds and Miscellaneous Provisions Act, 1952.
  - *Rules*: 12% Employee Contribution, ₹15,000 Monthly Statutory Wage Ceiling, 8.33% EPS / 3.67% EPF Employer Split.
- **Employees' State Insurance Corporation (ESIC)**:
  - *Statute*: Employees' State Insurance Act, 1948.
  - *Rules*: 0.75% Employee, 3.25% Employer, ₹21,000 Monthly Gross Ceiling.
- **State Commercial Tax Departments (28 States & 8 Union Territories)**:
  - *Statutes*: State Professional Tax Acts (Karnataka, Maharashtra, Telangana, West Bengal, Gujarat, Tamil Nadu, Andhra Pradesh, Kerala, Madhya Pradesh, Odisha, Assam, Delhi, etc.).
