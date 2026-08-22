# SmartSalary India — Requirement Traceability Matrix (Phase 2 Master)

| Req ID | Requirement Description | File / Route | Backend Service / Model | DB Support | Frontend Support | Browser Journey | Test Baseline | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **AUTH-001** | User Registration with Argon2id hash & background Email OTP | `/api/v1/auth/register` | `User`, `Employee`, `OTPService` | ✓ | `auth.html` | ⚠️ | `test_email_otp_auth.py` | **PARTIAL** (Missing Sector/Occupation in Form) |
| **AUTH-002** | OTP Verification & Account Activation (`is_active=True`) | `/api/v1/auth/verify-email-otp` | `VerificationToken`, `User` | ✓ | `auth.html` | ✓ | `test_email_otp_auth.py` | **IMPLEMENTED** |
| **AUTH-003** | Normal Login without OTP (Argon2id + JWT + Session) | `/api/v1/auth/login` | `UserSession`, `SessionRepository` | ✓ | `auth.html` | ✓ | `test_auth_api.py` | **IMPLEMENTED** |
| **AUTH-004** | Forgot Password with OTP reset token & session revocation | `/api/v1/auth/forgot-password` | `OTPPurpose.PASSWORD_RESET` | ✓ | `auth.html` | ✓ | `test_email_otp_auth.py` | **IMPLEMENTED** |
| **AUTH-005** | Login persistence across browser session re-entry | `/api/v1/auth/refresh` | `JWTProvider`, `UserSession` | ✓ | `app.js` | ✓ | `test_auth_api.py` | **IMPLEMENTED** |
| **CALC-001** | Deterministic Tax Calculation (AY 2026-27 Sec 115BAC) | `/calculator/calculate` | `TaxCalculator`, `CalculationService` | ✓ | `calculator.html` | ✓ | `test_tax_engine.py` | **IMPLEMENTED** |
| **CALC-002** | 28 States + 8 UTs Jurisdictional Master Coverage | `/calculator` | `StateJurisdictionMaster`, `PtCalculator` | ✓ | `calculator.html` | ✓ | `test_pt_multi_state.py` | **IMPLEMENTED** |
| **CALC-003** | Anonymous Calculation Auth Gate & Preservation | `/calculator/calculate` | `result_auth_required.html` | ✓ | `calculator.html` | ⚠️ | `test_web_pages.py` | **PARTIAL** (Ensure seamless state carry-over) |
| **CALC-004** | Quick to Detailed switch without input loss | `/calculator` | Form state preservation | — | `calculator.html` | ✓ | Manual / Browser | **IMPLEMENTED** |
| **SNAP-001** | Immutable SHA-256 Calculation Snapshot persistence | `CalculationService` | `CalculationSnapshot`, `CalculationRun` | ✓ | `result_minimal.html` | ✓ | `test_calculation_api.py` | **IMPLEMENTED** |
| **SNAP-002** | Unified `CalculationContext` single source of truth | `resolve_owned_calculation` | `CalculationContext` DTO | ✓ | RAG/PDF/Payslip | ⚠️ | New context tests | **PARTIAL** (Unification needed) |
| **RAG-001** | RAG Assistant Grounded in Active Snapshot & Evidence | `/api/v1/chat/inquire` | `AIService`, `FinancialRAGRetriever` | ✓ | `ai_assistant_drawer.html` | ⚠️ | `test_m6_1_rag_security.py` | **PARTIAL** (Add Intent Layer & 3-state Firewall) |
| **RAG-002** | RAG Citation Validation against retrieved sources | `CitationValidator` | `CitationValidator`, `RAGSourceDisplay` | ✓ | `ai_assistant_drawer.html` | ✓ | `test_m6_1_rag_security.py` | **IMPLEMENTED** |
| **RAG-003** | RAG Same Question Consistency & Abstention | `AIService` | `AIService.process_inquiry` | ✓ | `ai_assistant_drawer.html` | ⚠️ | RAG regression tests | **PARTIAL** |
| **PDF-001** | Calculation Print & Printable Summary View | `/calculator/export/{id}` | `CalculationService` | ✓ | `print_summary.html` | ✓ | `test_web_pages.py` | **IMPLEMENTED** |
| **PDF-002** | Calculation A/B Contamination Isolation Test | `CalculationService` | `CalculationRepository` | ✓ | Downstream exports | ⚠️ | A/B isolation suite | **PARTIAL** |
| **PAY-001** | Payslip Intelligence & Three-Way Reconciliation | `/api/v1/payslips/upload` | `PayslipService`, `ReconciliationEngine` | ✓ | `payslips.html` | ⚠️ | `test_payslip_security.py` | **PARTIAL** |
| **COMP-001** | Company Portal, Employees & Multi-Tenant Batch Payroll | `/api/v1/enterprise/...` | `PayrollRun`, `Organization` | ✓ | `dashboard.html` | ❌ | `test_tenant_isolation.py` | **BROKEN IN NAVBAR** (Needs dedicated portal route) |
| **COMP-002** | Multi-Role RBAC (Admin, Payroll Admin, HR, Employee) | `get_tenant_context` | `Role`, `user_roles` | ✓ | Middleware / API | ✓ | `test_tenant_isolation.py` | **IMPLEMENTED** |
| **UI-001** | Fintech Responsive UX (375px to 1440px) & Large Numbers | Base styles | `format_inr`, CSS container rules | — | `app.css`, `base.html` | ✓ | Visual / Browser | **IMPLEMENTED** |
| **UI-002** | Clean Homepage without internal engineering metrics | `/` | `home.html` | — | `home.html` | ⚠️ | Visual / Browser | **NEEDS CLEANUP** |
| **EVID-001** | Official Tax & Regulatory Sources Hub | `/system-status` | `OfficialSourcesRegistry`, `EvidenceDocument` | ✓ | `system_status.html` | ✓ | `test_vertical_slice.py` | **IMPLEMENTED** |
