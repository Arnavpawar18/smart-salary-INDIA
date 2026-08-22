# SMARTSALARY MASTER REQUIREMENT EXECUTION AUDIT

Audit date: 2026-08-22

## 1. Overall status

NOT READY

The current repository has substantial implementation in place and the financial engine validation is clean, but the product is not fully requirement-complete. Several requirements are implemented only partially, some enterprise/employee UI data is hardcoded or fallback data, the full test gate is blocked by a filesystem temp-directory issue, and Ruff is failing.

## 2. Requirement scorecard

| Requirement | Current implementation | Exact files / functions | Test / runtime evidence | Status | Recommended fix | Security impact | Business logic affected |
|---|---|---|---|---|---|---|---|
| Normal login with email/password and no OTP | Login verifies active user password with `PasswordHasher`; no OTP branch in login. Login failure detail corrected to required `"Incorrect email or password"`. | `backend/app/api/v1/endpoints/auth.py:382` `login_user`; `backend/app/core/security.py` `PasswordHasher` | `test_auth_api.py`, `test_email_otp_auth.py`; targeted rerun `20 passed` | IMPLEMENTED + VERIFIED | Keep tests asserting exact error text and no OTP requirement. | Positive; no account enumeration by error text. | No |
| Password hashing | Argon2id via `pwdlib` wrapper. | `backend/app/core/security.py` `PasswordHasher` | `test_auth_primitives.py`, `test_m6_security_hardening.py` | IMPLEMENTED + VERIFIED | None. | Positive. | No |
| Session cookies | Access/refresh cookies are HttpOnly; Secure depends on `ENVIRONMENT`; SameSite Lax; paths are `/` and `/api/v1/auth/refresh`; CSRF cookie non-HttpOnly. | `backend/app/core/auth_middleware.py:37` `set_auth_cookies` | Auth tests; runtime GET/static passed | IMPLEMENTED + VERIFIED | Add browser-level cookie assertions for production Secure mode. | Positive. | No |
| Refresh rotation and persistent session table | `UserSession` table stores JTI and token hash; `SessionRepository` creates/rotates/revokes sessions. Refresh now validates active JTI, token hash, and expiry before rotation. | `backend/app/models/session.py`; `backend/app/repositories/session_repository.py:57`; `backend/app/api/v1/endpoints/auth.py:455` | `test_auth_primitives.py`, `test_session_revocation.py`; targeted rerun `20 passed` | IMPLEMENTED + VERIFIED | Add explicit test for token-hash mismatch and expired persistent session. | Positive. | No |
| Protected requests reject revoked sessions | Access tokens are verified by signature/user only; no access-token session binding or access JTI blacklist. Refresh tokens reject revoked sessions. | `backend/app/core/auth_middleware.py:107` `get_current_user`; `backend/app/repositories/session_repository.py` | Source inspection | PARTIAL | Add session id/JTI claim to access token or authoritative access session lookup without weakening current auth. | Medium: logout revokes refresh but access token may remain valid until expiry. | No |
| Logout | `/logout` revokes current refresh session, clears cookies, now uses existing CSRF dependency. | `backend/app/api/v1/endpoints/auth.py:659`; `backend/app/core/auth_middleware.py:86` | Targeted auth/session rerun `20 passed` | IMPLEMENTED BUT NOT FULLY VERIFIED | Add test proving missing CSRF fails and refresh reuse after logout fails. | Positive. | No |
| Logout-all | Revokes all refresh sessions, clears cookies, now uses CSRF dependency. | `backend/app/api/v1/endpoints/auth.py:637` | Targeted auth/session rerun `20 passed` | IMPLEMENTED BUT NOT FULLY VERIFIED | Add test for CSRF and multi-session refresh rejection. | Positive. | No |
| Forgot password | Generic response, OTP generation, verification, reset token, password reset, session revocation. Registered email path returns `verification_id`; unknown email returns `verification_id: null`. SMTP failure returns 502 for known active user. | `backend/app/api/v1/endpoints/auth.py:245`, `:291`, `:326`; `backend/app/services/otp_service.py`; `backend/app/services/email_service.py` | `test_email_otp_auth.py` | IMPLEMENTED + VERIFIED | Consider whether returning `verification_id` only for known users weakens enumeration protection for API clients. | Medium. | No |
| OTP security | HMAC storage, TTL, max attempts, single use, resend cooldown/hourly rate limit. OTP is present only in email content/test inbox. | `backend/app/services/otp_service.py`; `backend/app/models/verification_token.py` | `test_email_otp_auth.py` | IMPLEMENTED + VERIFIED | Add log scanning test for raw OTP/password. | Positive. | No |
| Email failure behavior | SMTP failure returns false; registration/resend/known forgot password return 502. Hardcoded SMTP credentials were removed. | `backend/app/services/email_service.py`; `backend/app/core/config.py:33` | Source inspection; targeted auth rerun | IMPLEMENTED BUT NOT VERIFIED | Add tests for SMTP failure paths. | High positive: committed secret removed. | No |
| Registration profile persistence | User and Employee are created; email/name/phone persist. `sector`, `occupation`, `state_code`, `employment_type`, `account type` are accepted but not all persisted; `state_id=1` is hardcoded. | `backend/app/api/v1/endpoints/auth.py:87`; `backend/app/models/employee.py` | Source inspection; `test_email_otp_auth.py` covers basic creation | PARTIAL | Persist declared profile fields through validated model mappings and tests. | Low/medium data integrity. | No |
| Navbar auth state | Server-side `current_user` controls Sign In/Register vs profile nav. JS reads only non-HttpOnly `csrf_token`, not `access_token`. | `backend/app/templates/partials/navbar.html:31`, `:212`; `backend/app/main.py` optional/current user dependencies | Source inspection | IMPLEMENTED BUT NOT BROWSER-VERIFIED | Add UI tests for login/logout/reload navbar states. | Positive. | No |
| Centralized design system | `app.css` contains tokens and component classes; both bases load it. Tailwind config and many utility classes remain duplicated in templates. `html.light` token block is absent; `:root` is light fallback. | `backend/app/static/css/app.css`; `backend/app/templates/base.html`; `backend/app/templates/enterprise_base.html` | Source inspection; runtime CSS 200 | PARTIAL | Move repeated Tailwind/theme config and hardcoded utility styling behind central tokens/classes. | None. | No |
| Static asset cache busting | `asset_version` now generated from static file mtimes; CSS and `app.js` use it. | `backend/app/main.py:63`; `backend/app/templates/base.html:106`; `enterprise_base.html:60` | Runtime CSS/JS 200 | IMPLEMENTED + VERIFIED | Add unit test that asset version changes after asset mtime changes. | None. | No |
| Public/employee routes | Routes exist for `/`, `/calculator`, `/dashboard`, `/payslips`, `/login`, `/register`, `/help`, `/tax-center`, `/system-status`, `/employee`. Auth required for dashboard/payslips/tax-center/employee. | `backend/app/main.py:93-598` | Runtime `/` 200; tests include UI endpoint tests | IMPLEMENTED BUT NOT FULLY VERIFIED | Browser-check all pages for console/network/layout. | Mixed; protected routes use auth. | No |
| Enterprise routes | Routes exist for `/enterprise`, risk, tax analytics, compliance, approvals, audit logs. Tenant context required for pages. | `backend/app/main.py:437-559`; `backend/app/api/v1/endpoints/enterprise.py` | `test_enterprise_api.py`, `test_enterprise_rbac_and_idor.py` | PARTIAL | Finish compliance generation/export/history, RBAC permissions, browser tests. | Medium. | No |
| Enterprise RBAC | Tenant membership enforced; role-specific permission checks are not consistently used on enterprise endpoints. | `backend/app/core/tenant_context.py`; `backend/app/api/v1/endpoints/enterprise.py` | RBAC/IDOR tests pass, but source shows no endpoint-specific role gate | PARTIAL | Add explicit role/permission gates for admin/payroll/auditor actions. | Medium/high. | No |
| Enterprise tenant isolation | Major enterprise queries scope by `ctx.organization_id`; audit logs endpoint does not scope logs to organization. | `enterprise.py:31`, `:104`, `:190`, `:250`, `:289`, `:358` | Tenant/IDOR tests pass, source issue remains | PARTIAL | Add tenant metadata to audit events and scope audit log reads. | Medium. | No |
| Risk engine | Risk index/anomalies use DB counts; departmental heatmap falls back to hardcoded departments and insights. | `enterprise.py:104` | Source inspection | PARTIAL | Label demo data or compute from real tenant data only. | Low/medium trust risk. | No |
| Tax analytics | Payroll totals are DB-backed; average saving, compliance, projected savings, distributions, departments, insights are hardcoded. | `enterprise.py:190` | Source inspection | PARTIAL | Replace placeholders with DB/service calculations or label as illustrative. | Low/medium trust risk. | No |
| Compliance reports | Page exists; no complete generation/export/history API implementation found in audited path. | `main.py:503`; `pages/enterprise_compliance.html` | Source inspection | PARTIAL | Implement report config/generation/export/history with tenant/RBAC. | Medium. | No |
| Approvals | List/action endpoints exist; tenant scoping and state transitions exist; CSRF is not applied to API action; maker-checker separation not proven. | `enterprise.py:250`, `:289` | `test_enterprise_rbac_and_idor.py` | PARTIAL | Add CSRF or approved API CSRF policy, maker-checker rules, role gates. | High for admin actions. | No |
| Audit logs | Append-only ORM protections exist; hash behavior exists in audit model/service; enterprise read is not tenant-scoped. | `backend/app/models/audit.py`; `enterprise.py:358` | Audit tests in suite; source inspection | PARTIAL | Scope audit logs by tenant and add pagination/filter tests. | Medium. | No |
| Employee tax center | Route and API exist; latest calculation influences regime taxes; section declarations and recommendations are hardcoded. Declaration submission persists aggregate declaration only. | `employee_portal.py:69`, `:151`; `main.py:575` | `test_m10_individual_e2e.py` targeted initially stale/fixture-sensitive; full suite mostly passed | PARTIAL | Persist and read actual section line items, recommendations, payslip/YTD data. | Low/medium data integrity. | No |
| Calculation API authentication | `POST /api/v1/calculations` requires `get_current_user`; anonymous returns 401, authenticated returns 201 when fixture uses app DB/auth flow. | `backend/app/api/v1/endpoints/calculations.py:29` | `test_calculation_api.py`; targeted rerun passed | IMPLEMENTED + VERIFIED | Remove runtime API lint issues. | Positive. | No |
| Calculation ownership / IDOR | Calculation detail/history/delete scope to current employee; `CalculationContext` enforces owner. | `calculations.py:124`, `:174`, `:223`; `calculation_context_service.py:65` | `test_calculation_context_ab_isolation.py` | IMPLEMENTED + VERIFIED | Add print/export auth tests because web routes allow anonymous for owned persisted runs. | Medium for web print/export. | No |
| RAG/chatbot | Chat is authenticated; sessions scoped to user; calculation context is resolved by owner/latest. Source grounding exists via retriever/citation validator. | `chat.py`; `ai_service.py`; `engine/rag/*` | RAG/security tests in full suite; source inspection | IMPLEMENTED BUT NOT FULLY VERIFIED | Add browser/UI chat tests and explicit cross-user snapshot test through API. | Medium. | No |
| Financial engine | Not modified by this audit/fix. | `backend/app/engine/` | `run_100k_system_validation.py`: 120,000 passed, 0 failures | IMPLEMENTED + VERIFIED | None. | Positive. | No |
| Full test gate | Targeted requested files mostly passed after fixes; full suite reported `299 passed` then 2 setup errors due to `scratch_tmp` deletion permission. | `backend/tests` | Command output | IMPLEMENTED BUT NOT VERIFIED | Resolve Windows permission issue for `scratch_tmp` and rerun. | None. | No |
| Ruff gate | Ruff fails with 89 issues after scoped fixes. | `backend/app`, `backend/tests` | `ruff check backend/app backend/tests` exit 1 | BROKEN | Manually clean imports/unused variables; do not run `ruff --fix` unless approved. | Low, except unused security imports revealed missing CSRF before fix. | No |
| Browser diagnostics | Uvicorn runtime HTTP/static smoke passed. Dedicated DevTools/Playwright browser diagnostics were not available in this session. | Runtime command | `/`, CSS, JS, health all 200 | IMPLEMENTED BUT NOT VERIFIED | Run actual browser console/network checks. | None. | No |

## 3. Runtime verification

- Server command: `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Port 8000: free before start
- Started PID: 27332
- `GET /`: 200
- `HEAD /static/css/app.css`: 200
- `HEAD /static/js/app.js`: 200
- `GET /api/v1/health`: 200
- Stopped PID: 27332

Browser DevTools console/network checks were attempted, but no working browser-control tool was available. Playwright import failed in the Node REPL with an export-shape error.

## 4. Test evidence

Targeted files before fixes:

- Passed: `test_auth_api.py`, `test_email_otp_auth.py`, `test_auth_primitives.py`, `test_m6_security_hardening.py`, `test_session_revocation.py`, `test_enterprise_api.py`, `test_tenant_isolation.py`, `test_enterprise_rbac_and_idor.py`, `test_calculation_api.py`, `test_calculation_context_ab_isolation.py`, `test_final_user_journey_e2e.py`, `test_m11_company_e2e.py`
- Initial failures: `test_phase3_ui_endpoints.py`, `test_m10_individual_e2e.py`
- Failure classification: incorrect fixture/test setup around app DB visibility/direct token cookie path; after scoped fixes, the affected rerun passed.

Targeted rerun after fixes:

- `.venv\Scripts\pytest backend\tests\test_auth_api.py backend\tests\test_email_otp_auth.py backend\tests\test_auth_primitives.py backend\tests\test_session_revocation.py backend\tests\test_phase3_ui_endpoints.py -q`
- Result: `20 passed`

Full suite:

- `.venv\Scripts\pytest backend\tests -q --basetemp=D:\Smart_salary_india\scratch_tmp`
- Result: `299 passed`, `2 errors`
- Errors: setup failed for `test_alembic_migration_lifecycle` and `test_local_document_storage_lifecycle` because pytest could not remove `D:\Smart_salary_india\scratch_tmp` (`WinError 5 Access is denied`).

Financial validation:

- `.venv\Scripts\python.exe backend\scripts\run_100k_system_validation.py`
- Result: `120,000 / 120,000`, `0 mismatches`, `0 security violations`, `0 tenant violations`

Ruff:

- `.venv\Scripts\ruff check backend/app backend/tests`
- Result: failed with 89 issues.

## 5. Files changed by this audit

- `backend/app/core/config.py`
- `backend/app/repositories/session_repository.py`
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/main.py`
- `backend/app/templates/base.html`
- `docs/master_requirement_execution_audit.md`
- `docs/master_requirement_remediation_plan.md`

## 6. Business logic safety

Untouched in this audit:

- Tax engine: yes
- CalculationContext business logic: yes
- RAG retrieval/grounding architecture: yes
- PDF generation: yes
- Payslip calculation logic: yes
- Payroll calculation logic: yes
- Company business rules: yes
- Tenant isolation architecture: yes
- Authentication architecture: not broadly changed; only scoped endpoint/session hardening

## 7. Final decision

PHASE NOT COMPLETE - DEFECTS REMAIN
