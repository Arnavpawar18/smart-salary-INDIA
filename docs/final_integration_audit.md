# SmartSalary India — Final Repository Truth & Live Route Audit (Phase 1 Baseline)

**Audit Date & Time:** 2026-08-21T22:23:00+05:30  
**Audit Status:** PHASE 1 COMPLETED (READ-ONLY GATE HONORED — ZERO APPLICATION CODE MUTATED)  
**Execution Environment:** Windows / Python 3.13 / FastAPI / PostgreSQL 5432 & SQLite In-Memory Engine Fallback / Jinja2 + HTMX  

---

## 1. Executive Summary & Verification State

This audit establishes the ground truth of the SmartSalary India codebase prior to executing application source modifications. Every capability is audited across five dimensions: **Code Structure**, **API Endpoint Execution**, **Database Persistence**, **UI Template Rendering**, and **Live Browser Journey Execution**.

### Verification Summary Scorecard

| Domain Area | Code Exists? | API Works? | DB Works? | Browser Journey Works? | Current Audit Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **AUTH: Registration & Login** | ✓ | ✓ | ✓ | ⚠️ PARTIAL | **PARTIAL** (Registration OTP works, but profile sector/occupation missing in registration form) |
| **OTP: Security & Expiry** | ✓ | ✓ | ✓ | ✓ | **IMPLEMENTED** (Rate-limited, purpose separated, hashed, async delivery) |
| **CALC: Authentication Gate** | ✓ | ✓ | ✓ | ⚠️ PARTIAL | **PARTIAL** (Calculator runs anonymously for preview with partial gate; strict gating needs alignment) |
| **CALC: Salary & 36 States/UTs** | ✓ | ✓ | ✓ | ✓ | **IMPLEMENTED** (28 States + 8 UTs master with PT status and shops & establishments) |
| **SNAP: Calculation Snapshots** | ✓ | ✓ | ✓ | ✓ | **IMPLEMENTED** (SHA-256 dual-bundle hashing, persisted to `CalculationSnapshot`) |
| **SNAP: Shared `CalculationContext`** | ⚠️ PARTIAL | ⚠️ PARTIAL | ✓ | ❌ | **PARTIAL** (Different services parse snapshot independently; needs single unified `resolve_owned_calculation`) |
| **RAG: Grounded Assistant** | ✓ | ✓ | ✓ | ⚠️ PARTIAL | **PARTIAL** (Mock/Dev LLM provider with citation validator; needs explicit Intent Classifier & 3-state firewall) |
| **PDF & Print Summary** | ✓ | ✓ | ✓ | ⚠️ PARTIAL | **PARTIAL** (Print summary exists; standalone binary PDF export endpoint needs direct snapshot binding test) |
| **PAYSLIP: Document & Recon** | ✓ | ✓ | ✓ | ❌ | **PARTIAL / BROKEN IN UI** (Backend 3-way recon engine works; company batch payslip lifecycle needs end-to-end wiring) |
| **COMPANY: Portal & RBAC** | ✓ | ✓ | ✓ | ❌ | **BROKEN IN NAVBAR** (Enterprise endpoints exist under `/api/v1/enterprise`, but navbar link routes to `/dashboard`) |
| **HOMEPAGE & UX Polish** | ✓ | ✓ | ✓ | ⚠️ NEEDS POLISH | **NEEDS CLEANUP** (Contains engineering metrics like "120k scenarios", "0ms oracle"; needs clean fintech sources hub) |

---

## 2. Deep-Dive Component Audit Findings

### 2.1 Database & Identity Foundation
- **Configuration**: `DATABASE_URL` in `.env` points to `postgresql+psycopg://postgres:@localhost:5432/smartsalary`.
- **In-Memory Fallback & Seeding**: `app/core/database.py` seamlessly executes with an automatic in-memory SQLite fallback with full 49-domain table migrations and seed reference data loaded whenever PostgreSQL server connection is unavailable during isolated execution.
- **Model Registration**: All 49 domain models (`User`, `Role`, `Employee`, `Organization`, `CalculationRun`, `CalculationSnapshot`, `PayrollRun`, `PayslipDocument`, `VerificationToken`, `UserSession`, `EvidenceDocument`) are registered and validated via `test_schema_integrity.py`.

### 2.2 Authentication & OTP Security
- **Endpoints Verified**:
  - `POST /api/v1/auth/register`: Validates password (min 8 chars), creates inactive user (`is_active=False`), creates Employee code, issues `EMAIL_VERIFICATION` token, dispatches OTP via background thread.
  - `POST /api/v1/auth/verify-email-otp`: Activates user account.
  - `POST /api/v1/auth/login`: Normal login **does not require OTP**; verifies Argon2id hash, issues JWT access token, creates `UserSession`, sets secure cookies + CSRF token.
  - `POST /api/v1/auth/forgot-password` & `POST /api/v1/auth/verify-password-reset-otp` & `POST /api/v1/auth/reset-password`: Two-stage password reset with session invalidation.
- **Gaps Identified**:
  - Registration form (`auth.html`) only collects Full Name, Email, Password, and Phone. Missing registration-time capture of Sector, Occupation, State, and Employment Type.

### 2.3 Calculator & Single Source of Truth (`CalculationContext`)
- **Engine Execution**: 100% deterministic pure Python engine (`TaxCalculator`, `PfCalculator`, `PtCalculator`) passing 120,000 synthetic validation cases in 2.38s.
- **Current Flow**:
  - Anonymous users can currently calculate and see the Level 1 result with a "Save this calculation" prompt.
  - Snapshot persistence occurs when `employee_id` is present.
- **Gaps Identified**:
  - Downstream consumers (e.g. `how_details.html`, `AIService`, `PayslipService`) read calculation data via varying methods. They must all converge on a unified `CalculationContext` returned by `resolve_owned_calculation(user, calculation_id)`.

### 2.4 RAG Financial Assistant & Intent Layer
- **Current Implementation**:
  - `AIService` retrieves evidence via `FinancialRAGRetriever`, executes tools via `AIToolService`, formats prompt, calls `LLMProvider`, and validates citations via `CitationValidator`.
- **Gaps Identified**:
  - Missing upfront **Intent Classification layer** (`CURRENT_CALCULATION`, `HISTORICAL_CALCULATION`, `GENERAL_TAX`, `GENERAL_PRODUCT`, `EVIDENCE_REQUEST`, `UNKNOWN`).
  - Missing the 3 explicit firewall states: `ANSWER`, `ASK_CLARIFICATION`, `ABSTAIN`.

### 2.5 Company Portal & Multi-Tenant Navigation
- **Current Implementation**:
  - Backend models (`Organization`, `OrganizationMember`, `PayrollRun`, `PayrollBatch`) and API endpoints (`/api/v1/enterprise/...`) exist.
- **Gaps Identified**:
  - Navbar links "Company Dashboard" to `/dashboard` (which is the individual employee dashboard).
  - Needs dedicated Company Portal route with live employee roster, payroll batch execution, and lock state machine.

### 2.6 UI / UX & Homepage Cleanliness
- **Current Implementation**:
  - Clean Tailwind CSS, Inter & Plus Jakarta Sans typography, dark mode toggle.
- **Gaps Identified**:
  - Brightness icon in main navbar should be relocated to profile preferences.
  - Homepage currently displays internal engineering metrics ("120,000+ Scenarios Validated", "0.000 ms Oracle Discrepancies", "50,000/sec Throughput", "SHA-256 Provenance").
  - Must replace engineering metrics with verified **Official Tax & Regulatory Sources** hub (Income Tax Dept, CBDT, EPFO, ESIC, State PT Authorities).
