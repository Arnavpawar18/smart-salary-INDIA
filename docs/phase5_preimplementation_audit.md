# Phase 5 Pre-Implementation Audit & Architecture Mapping

**Date:** August 22, 2026  
**Auditor:** Antigravity IDE Autonomous Agentic Subsystem  
**Scope:** Pre-Implementation Read-Only Audit of SmartSalary India Enterprise & Employee Architecture  
**Guiding Mandate:** Reuse existing models, services, routes, TenantContext, CalculationContext, authentication, authorization, payslip, and enterprise infrastructure. Do not duplicate architecture. Freeze statutory financial engines.

---

## 1. Executive Summary

This pre-implementation audit inventories all active domain models, services, authentication middleware, repository classes, and web routes. It establishes the exact integration boundaries and ensures zero redundant code or duplicate tables are introduced in Phase 5.

### Key Architectural Invariants Confirmed:
1. **Financial Engines are Untouched:** `backend/app/engine/` contains pure, deterministic calculation logic (Tax Section 115BAC, EPF 12%, ESI ₹21k threshold, PT 28 states + 8 UTs). All enterprise and employee screens will strictly consume existing database entities (`PayrollRunItem`, `CalculationSnapshot`, `CalculationRun`).
2. **Tenant Isolation is Active:** `TenantContext` (`backend/app/core/tenant_context.py`) dynamically enforces tenant boundaries by validating `OrganizationMembership` (`ACTIVE` status) and querying `role_permissions`.
3. **Audit Ledger is Tamper-Evident:** Table `audit_logs` (`backend/app/models/audit.py`) is protected by SQLAlchemy event listeners (`before_update`, `before_delete`) that throw `AuditImmutabilityError`. Every company action in Phase 5 will append to this ledger.
4. **Clean Domain Model Separation:** No new ORM tables are required for Phase 5. Existing tables (41 tables in Alembic) already define:
   - `Organization`, `OrganizationMembership` (Table 1, 2)
   - `Department`, `JobRole`, `Employee`, `TaxpayerProfile` (Tables 3, 4, 5, 6)
   - `PayrollPeriod`, `PayrollRun`, `PayrollRunItem` (Tables 7, 8, 9)
   - `TaxDeclaration`, `TaxDeclarationItem`, `StatutoryComplianceEvent` (Tables 10, 11, 12)
   - `AuditLog`, `AuditChainHead`, `AuditCheckpoint` (Tables 13, 14, 15)
   - `PayslipDocument`, `PayslipExtraction`, `ReconciliationRecord` (Tables 16, 17, 18)
   - `UserSession` (Table 41)

---

## 2. Existing Model & Service Inventory

| Subsystem / Model | File Path | Existing Capabilities | Phase 5 Integration Role |
| :--- | :--- | :--- | :--- |
| **TenantContext** | `backend/app/core/tenant_context.py` | Extracts authenticated user membership, role name, and permissions for an org. | Server-side dependency guard on all `/enterprise/*` API and web routes. |
| **Organization & Membership** | `backend/app/models/organization.py` | Multi-tenant organization boundaries, legal name, PAN/TAN, states. | Tenant header branding, switcher, and tenant data filtering. |
| **Payroll Models** | `backend/app/models/payroll.py` | `PayrollPeriod`, `PayrollRun`, `PayrollRunItem` with cryptographic hashes (`input_hash`, `result_hash`). | Feeds Tax Analytics YTD liability, departmental wage summaries, and company dashboard. |
| **Compliance & Declarations** | `backend/app/models/compliance.py` | `TaxDeclaration` (6-stage status), `TaxDeclarationItem` (80C, 80D, NPS), `StatutoryComplianceEvent` (Form 24Q, PF ECR). | Powers Risk Engine, Compliance Center, Admin Approvals workflow, and Employee Tax Center. |
| **Audit Ledger** | `backend/app/models/audit.py` | Append-only `AuditLog` with sequential hash chaining and ORM delete/update blocking. | Append-only target for all approval/rejection/clarification actions, report downloads, and admin inspections. |
| **Payslip Architecture** | `backend/app/services/payslip_service.py` | 3-way reconciliation against `PayrollRunItem` and `CalculationSnapshot`. | Powers Employee Payslip Archive and reconciliation cards. |
| **Calculation Context** | `backend/app/services/calculation_context_service.py` | Immutable `CalculationContext` dataclass with IDOR boundary checks. | Powers Employee Dashboard salary breakdown and Tax Center regime comparisons. |

---

## 3. RBAC & Authorization Guard Matrix

| Route Category | Target URL | HTTP Method | Role Required | Server-Side Enforcement Guard | Audit Event Emitted? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Company Overview** | `/enterprise` | `GET` | Admin, Officer, SuperAdmin | `Depends(get_tenant_context)` | No (Read) |
| **Risk Engine** | `/enterprise/risk-engine` | `GET` | Admin, Officer, SuperAdmin | `Depends(get_tenant_context)` | No (Read) |
| **Tax Analytics** | `/enterprise/tax-analytics` | `GET` | Admin, Officer, SuperAdmin | `Depends(get_tenant_context)` | No (Read) |
| **Compliance Reports** | `/enterprise/compliance-reports` | `GET` | Admin, Officer, SuperAdmin | `Depends(get_tenant_context)` | No (Read) |
| **Generate Report** | `/api/v1/enterprise/compliance-reports/generate` | `POST` | Admin, Officer | `Depends(get_tenant_context)` + CSRF | Yes (`COMPLIANCE_REPORT_GENERATED`) |
| **Approvals Queue** | `/enterprise/approvals` | `GET` | Admin, Officer, SuperAdmin | `Depends(get_tenant_context)` | No (Read) |
| **Approval Action** | `/api/v1/enterprise/approvals/{id}/action` | `POST` | Admin, SuperAdmin | `Depends(get_tenant_context)` + CSRF | Yes (`DECLARATION_APPROVED` / `REJECTED`) |
| **Audit Logs** | `/enterprise/audit-logs` | `GET` | Admin, SuperAdmin, Auditor | `Depends(get_tenant_context)` | Yes (`AUDIT_LOG_INSPECTED`) |
| **Employee Dashboard** | `/employee` | `GET` | Authenticated Employee | `Depends(get_current_user)` | No (Read) |
| **Employee Tax Center**| `/tax-center` | `GET` | Authenticated Employee | `Depends(get_current_user)` | No (Read) |
| **Declaration Submit** | `/api/v1/employee/declarations` | `POST` | Authenticated Employee | `Depends(get_current_user)` + CSRF | Yes (`DECLARATION_SUBMITTED`) |
| **Payslip Archive** | `/payslips` | `GET` | Authenticated Employee | `Depends(get_current_user)` | No (Read) |

---

## 4. API & Data Contracts

### 1. Enterprise Risk Engine (`GET /api/v1/enterprise/risk-metrics`)
- **Real Backend Query:** Aggregates `TaxDeclaration` unverified ratios, `StatutoryComplianceEvent` overdue filings, and `PayrollRun` discrepancy flags.
- **Contract:**
  ```json
  {
    "risk_index": 78,
    "risk_level": "HIGH",
    "vs_last_month": "+12%",
    "anomalies": [
      {
        "id": 1,
        "type": "TDS_UNDERPAYMENT",
        "severity": "CRITICAL",
        "title": "Potential TDS Underpayment",
        "description": "Discrepancy detected in Q3 filings across 45 employee records in the Engineering department.",
        "department": "Engineering",
        "status": "OPEN",
        "timestamp": "2026-08-22T12:00:00Z"
      }
    ],
    "department_heatmap": [
      {"department": "Sales", "risk": "High", "score": 85},
      {"department": "Engineering", "risk": "Medium", "score": 55},
      {"department": "HR", "risk": "Low", "score": 20},
      {"department": "Operations", "risk": "Very Low", "score": 10}
    ],
    "ai_insights": {
      "version": "v4.2",
      "summary": "Model v4.2 detected a 40% increase in 80C declarations in Sales over the last 72 hours.",
      "supporting_evidence": "Historical data correlates this cluster with last-minute submissions before the March cutoff.",
      "recommendation": "Initiate targeted verification audit for unverified rent receipts."
    }
  }
  ```

### 2. Approval Action Contract (`POST /api/v1/enterprise/approvals/{id}/action`)
- **State Machine Guard:** Validates that status is `SUBMITTED` or `UNDER_REVIEW`. Rejects transitions from already `VERIFIED` or `REJECTED` records.
- **Contract:**
  ```json
  {
    "action": "APPROVE", // "APPROVE" | "REJECT" | "CLARIFICATION_REQUIRED"
    "remarks": "Form 12BB and LIC premium receipts verified against insurer seal.",
    "verified_deductions": 150000.00
  }
  ```

### 3. Employee Tax Center (`GET /api/v1/employee/tax-center`)
- **Real Backend Query:** Fetches user's `TaxDeclaration` and active `CalculationSnapshot`.
- **Contract:**
  ```json
  {
    "financial_year": "2025-26",
    "selected_regime": "NEW",
    "old_regime_tax": 245000.00,
    "new_regime_tax": 195000.00,
    "savings": 50000.00,
    "sections": {
      "80C": {"declared": 85400.00, "verified": 85400.00, "limit": 150000.00, "breakdown": [{"name": "EPF", "amount": 45400.00}, {"name": "LIC", "amount": 40000.00}]},
      "80D": {"declared": 25000.00, "verified": 25000.00, "limit": 25000.00, "breakdown": [{"name": "Self & Family", "amount": 25000.00}]},
      "NPS_80CCD_1B": {"declared": 50000.00, "verified": 0.00, "limit": 50000.00, "breakdown": []}
    }
  }
  ```

---

## 5. UI Design System & Motion Specification

1. **Tokens & Theming:**
   - Backgrounds: `--bg-canvas` (`#080d1a` dark / `#f8fafc` light), `--bg-surface` (`#0f172a` dark / `#ffffff` light), `--bg-surface-elevated` (`#1e293b`).
   - Accents: Indigo (`#4f46e5`), Emerald (`#10b981`), Amber (`#f59e0b`), Rose (`#ef4444`).
   - Typography: Geist / Inter fonts with tabular numbers (`font-variant-numeric: tabular-nums`).
2. **Motion Engine (Respects `prefers-reduced-motion`):**
   - Page Entrance: `opacity: 0 -> 1`, `transform: translateY(8px) -> translateY(0)` (300ms cubic-bezier(0.16, 1, 0.3, 1)).
   - Card Hover: `transform: translateY(-2px)`, subtle border glow.
   - SVG Gauges: `stroke-dasharray` animation from 0 to value upon data arrival.
   - Drawers & Modals: Slide from right with backdrop blur (`backdrop-filter: blur(16px)`).
   - Zero gratuitous animations; high financial clarity.

---

## 6. Complete UI States Architecture

Every screen implements 7 explicit states:
1. **Loading State:** CSS pulse skeleton loaders matching the exact dimensions of KPI cards and table rows.
2. **Success State:** Authoritative backend data displayed with `tabular-nums` and currency formatting (`format_inr`).
3. **Empty State:** High-trust empty banners with descriptive instructions (e.g. `"No historical audit logs found for the selected date range"`).
4. **Error State:** Non-destructive retry cards with safe error codes (`"Unable to retrieve tax analytics. Check database connectivity."`).
5. **Unauthorized State:** Clear redirect to login with return URL preservation.
6. **Forbidden (403) State:** Explicit role violation card (`"Access Denied: Your account does not have Company Admin permissions for this organization."`).
7. **Stale Data State:** Refresh indicator when background synchronization is active.

---

## 7. Execution Order (Steps 1 through 20)

```
STEP 1: Create Phase 5 Schema Models in `backend/app/schemas/enterprise.py`
STEP 2: Implement Enterprise API Endpoints in `backend/app/api/v1/endpoints/enterprise.py`
STEP 3: Implement Employee Portal Endpoints in `backend/app/api/v1/endpoints/employee_portal.py`
STEP 4: Build Enterprise Base Shell `backend/app/templates/enterprise_base.html`
STEP 5: Build Reusable Jinja Components `backend/app/templates/partials/enterprise_components.html`
STEP 6: Implement Company Dashboard `backend/app/templates/pages/enterprise_dashboard.html`
STEP 7: Implement AI Risk Engine `backend/app/templates/pages/enterprise_risk_engine.html`
STEP 8: Implement Tax Analytics `backend/app/templates/pages/enterprise_tax_analytics.html`
STEP 9: Implement Compliance Center `backend/app/templates/pages/enterprise_compliance.html`
STEP 10: Implement Approval Center & State Machine `backend/app/templates/pages/enterprise_approvals.html`
STEP 11: Implement Append-Only Audit Logs `backend/app/templates/pages/enterprise_audit_logs.html`
STEP 12: Implement Employee Tax Center `backend/app/templates/pages/tax_center.html`
STEP 13: Harmonize Employee Dashboard & Payslip Archive (`pages/dashboard.html`, `pages/payslips.html`)
STEP 14: Wire Web Routes in `backend/app/main.py`
STEP 15: Update Navigation in `backend/app/templates/partials/navbar.html`
STEP 16: Write Targeted Security & IDOR Tests `backend/tests/test_enterprise_rbac_and_idor.py`
STEP 17: Run Targeted Enterprise Test Suites
STEP 18: Run Financial Invariant Safety Engine (120,000 / 120,000 scenarios)
STEP 19: Run Full Regression Test Suite
STEP 20: Run Manual Ruff Check (without `--fix`) and Produce Final Audit Report
```
