# SMARTSALARY MASTER REQUIREMENT REMEDIATION PLAN

Audit date: 2026-08-22

## Priority defects

| Priority | Defect | Root cause | Affected files | Minimal fix | Security impact | Tests required | Verification command |
|---|---|---|---|---|---|---|---|
| P0 | Access tokens remain valid after refresh session revocation until JWT expiry | Access token is not bound to persistent session/JTI revocation state | `backend/app/core/auth_middleware.py`, `backend/app/core/security.py`, `backend/app/api/v1/endpoints/auth.py` | Add session/JTI binding to access token and validate active session in `get_current_user`, or introduce a compatible access-token revocation lookup | Medium/high | Logout, logout-all, revoked session protected request, refresh reuse | `pytest backend/tests/test_session_revocation.py backend/tests/test_auth_api.py -q` |
| P0 | Enterprise approval action lacks visible CSRF/maker-checker enforcement | API action uses tenant context but no CSRF dependency or separation-of-duties guard | `backend/app/api/v1/endpoints/enterprise.py` | Apply established CSRF mechanism for browser-origin mutations and enforce approver is not maker/employee owner | High | Approval CSRF missing/valid, maker-checker rejection, tenant IDOR | `pytest backend/tests/test_enterprise_rbac_and_idor.py -q` |
| P0 | Enterprise audit log endpoint is not tenant-scoped | Query returns global latest audit logs without organization filter | `backend/app/api/v1/endpoints/enterprise.py`, `backend/app/services/audit_service.py`, `backend/app/models/audit.py` | Add organization/resource tenant metadata to events and filter by `ctx.organization_id` | Medium/high | Cross-tenant audit log leak test | `pytest backend/tests/test_tenant_isolation.py backend/tests/test_enterprise_rbac_and_idor.py -q` |
| P1 | Registration does not persist all collected profile fields | Request accepts `sector`, `occupation`, `state_code`, `employment_type`; creation hardcodes `state_id=1` and omits sector/occupation/account type | `backend/app/api/v1/endpoints/auth.py`, `backend/app/models/employee.py`, related schemas/migrations | Map validated state code to `State`, persist employment type and profile/catalog fields in the correct model | Medium data integrity | Registration persistence assertions for all required fields | `pytest backend/tests/test_email_otp_auth.py backend/tests/test_auth_api.py -q` |
| P1 | Forgot-password response exposes `verification_id` only for known active accounts | Anti-enumeration message is generic but machine-readable body differs | `backend/app/api/v1/endpoints/auth.py` | Use same response shape for unknown and known accounts, or require out-of-band continuation without revealing existence | Medium | Known/unknown forgot password response equality | `pytest backend/tests/test_email_otp_auth.py -q` |
| P1 | Enterprise analytics/risk/tax-center include hardcoded production-looking values | UI/API mixes real totals with static fallback/insight values | `backend/app/api/v1/endpoints/enterprise.py`, `backend/app/api/v1/endpoints/employee_portal.py`, enterprise/tax-center templates | Replace with DB/service-backed calculations or explicitly label illustrative demo data | Medium trust/compliance | API contract tests asserting source of metrics or demo labels | `pytest backend/tests/test_enterprise_api.py backend/tests/test_m10_individual_e2e.py -q` |
| P1 | Compliance reports are not complete end-to-end | Page exists but generation/export/history workflow is not proven | `backend/app/templates/pages/enterprise_compliance.html`, `backend/app/api/v1/endpoints/enterprise.py`, services/models | Implement report config, generation, export, history with tenant/RBAC | Medium | Compliance report lifecycle tests | `pytest backend/tests/test_enterprise_api.py -q` |
| P1 | Full suite blocked by `scratch_tmp` permission issue | Existing directory cannot be removed by pytest tmp path setup on Windows | `D:\Smart_salary_india\scratch_tmp` environment | Fix ACL/handle/cleanup outside tests, then rerun requested exact command | None | Full suite | `pytest backend/tests -q --basetemp=D:\Smart_salary_india\scratch_tmp` |
| P2 | Ruff fails with 89 issues | Import ordering, unused imports, whitespace, unused variables | `backend/app`, `backend/tests` | Manually clean only touched/relevant files or do scoped lint cleanup without `ruff --fix` | Low | Ruff gate | `ruff check backend/app backend/tests` |
| P2 | Browser DevTools verification not completed | No usable browser-control tool in session; Playwright import failed | Tooling/runtime | Run real browser automation or DevTools manually against Uvicorn | None | Console/network/theme diagnostics | Browser console/network checks from audit prompt |
| P2 | Design system is partially centralized | Tailwind CDN/config and many utility classes duplicate theme choices; `html.light` block absent | `backend/app/static/css/app.css`, `backend/app/templates/base.html`, `backend/app/templates/enterprise_base.html`, page templates | Move repeated theme tokens/classes into `app.css`; add explicit `html.light`; reduce hardcoded template styles | None | Design propagation tests and screenshots | `pytest backend/tests/test_design_system_propagation.py -q` |

## Fixes already applied in this audit

- Removed committed SMTP username/password defaults; credentials must now come from environment/.env.
- Corrected login failure message to the required exact text.
- Added existing CSRF dependency to `/api/v1/auth/logout` and `/api/v1/auth/logout-all`.
- Added refresh-session token-hash and expiry validation before rotation.
- Replaced manual static asset version with deterministic static file mtime versioning and applied it to `app.js`.

## Do not modify without separate approval

- Financial engine formulas
- Section 115BAC logic
- EPF/ESI/PT calculations
- CalculationContext semantics
- RAG retrieval architecture
- PDF/payslip/payroll calculation logic
- Tenant isolation architecture
