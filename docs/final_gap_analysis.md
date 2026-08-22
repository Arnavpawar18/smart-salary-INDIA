# SMARTSALARY INDIA — FINAL GAP ANALYSIS & REMEDIATION MATRIX

**Audit Date:** August 22, 2026  
**Document Purpose:** Authoritative gap report identifying all incomplete, partial, or incorrectly implemented requirements across the SmartSalary India repository, prioritized from P0 to P3.

---

## 1. Summary of Identified Gaps

| Gap ID | Priority | Subsystem / Requirement | Problem & Root Cause | Affected File(s) & Function(s) | Security / Business Impact |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **GAP-P0-01** | **P0** | **Session Revocation for Access Tokens** | Access tokens are checked only for signature/expiry in `get_current_user`; persistent session revocation is not checked for access tokens, allowing access tokens to be used until 15-min expiry after logout or single-session revocation. | `backend/app/core/auth_middleware.py` (`get_current_user`), `backend/app/core/security.py` | Medium/High: Active access tokens survive single session revocation until natural expiry. |
| **GAP-P0-02** | **P0** | **Enterprise Approval Maker-Checker & CSRF** | Approval action `/api/v1/enterprise/approvals/{id}/action` lacked explicit maker-checker validation (a user could approve their own tax declaration) and did not enforce CSRF dependency. | `backend/app/api/v1/endpoints/enterprise.py` (`process_approval_action`) | High: Separation of duties violation in payroll compliance. |
| **GAP-P0-03** | **P0** | **Enterprise Audit Logs Tenant Scoping** | `list_enterprise_audit_logs` returned global audit logs without filtering by `ctx.organization_id`. | `backend/app/api/v1/endpoints/enterprise.py` (`list_enterprise_audit_logs`) | High: Cross-tenant audit log metadata visibility. |
| **GAP-P1-01** | **P1** | **Registration Profile Completeness & State Mapping** | `register_user` hardcoded `state_id=1` regardless of user's selected `state_code`, and did not persist `employment_type` or occupation from `RegisterRequest`. | `backend/app/api/v1/endpoints/auth.py` (`register_user`) | Medium: Data integrity of newly registered employee profile. |
| **GAP-P1-02** | **P1** | **Forgot Password Response Verification ID Leakage** | `POST /forgot-password` returned `verification_id` UUID only for existing active users and `null` for non-existent users, leaking account existence to API clients. | `backend/app/api/v1/endpoints/auth.py` (`forgot_password`) | Medium: User account enumeration vulnerability. |
| **GAP-P1-03** | **P1** | **Employee Tax Center & Enterprise Analytics Real Backend Queries** | Employee Tax Center and Enterprise Analytics mixed real payroll totals with static mock deduction breakdowns and placeholders. | `backend/app/api/v1/endpoints/employee_portal.py`, `enterprise.py` | Low/Medium: Presentation fidelity and data realism. |
| **GAP-P1-04** | **P1** | **Compliance Reports Workflow End-to-End Wiring** | Compliance center report generation API (`/api/v1/enterprise/compliance-reports`) was not fully exposed for export/history lifecycle. | `backend/app/api/v1/endpoints/enterprise.py`, `enterprise_compliance.html` | Medium: Compliance export lifecycle incomplete. |
| **GAP-P1-05** | **P1** | **Ruff Lint Errors (89 issues)** | Unused imports, improper import ordering, and formatting issues in `backend/app` and `backend/tests`. | `backend/app/`, `backend/tests/` | Low: Code cleanliness and CI/CD gate pass. |
| **GAP-P2-01** | **P2** | **Deterministic Light Mode Tokens in app.css** | `:root` contained light theme fallback, but explicit `html.light` class token block was missing for deterministic theme toggling. | `backend/app/static/css/app.css` | Low: Theme switching visual consistency. |
| **GAP-P2-02** | **P2** | **Live Browser Rendering Automation & Diagnostic Verification** | Verification previously relied on curl/HTTP; full browser inspection via browser agent is required to verify rendering, fonts, HTMX, and charts. | Browser runtime | Low/Medium: Visual UX verification. |

---

## 2. Detailed Technical Gap Specifications & Remediation

### GAP-P0-01: Persistent Session Revocation for Access Tokens
- **Root Cause**: `get_current_user` in `backend/app/core/auth_middleware.py` validated JWT signature and expiration, but did not verify whether the user's active session or the access token's JTI / user's persistent session state has been revoked in `user_sessions`.
- **Authoritative Fix**: In `get_current_user`, after verifying the token payload, verify that the user has at least one active, unrevoked session in `SessionRepository`, or if `session_jti` is present in token claims, verify that specific session is unrevoked and not expired. This ensures that calling `logout` or `logout-all` immediately invalidates access without waiting for 15-minute JWT expiration.
- **Safety**: Do NOT alter token signing algorithm or password hashing logic.

### GAP-P0-02: Enterprise Approval Maker-Checker & CSRF
- **Root Cause**: In `backend/app/api/v1/endpoints/enterprise.py`, `process_approval_action` allowed any tenant administrator to approve any declaration without checking if `decl.employee.user_id == ctx.user_id`.
- **Authoritative Fix**:
  1. Add `_: None = Depends(verify_csrf)` for browser-origin protection.
  2. Add check: If `decl.employee and decl.employee.user_id == ctx.user_id`, raise `HTTPException(403, detail="Separation of duties violation: Maker cannot approve or review their own declaration.")`.
  3. Ensure audit logging logs the approval event with `tenant_id=ctx.organization_id`.

### GAP-P0-03: Enterprise Audit Logs Tenant Scoping
- **Root Cause**: In `backend/app/api/v1/endpoints/enterprise.py`, `list_enterprise_audit_logs` queried `AuditLog` ordered by ID without filtering by `AuditLog.tenant_id == ctx.organization_id`.
- **Authoritative Fix**: Filter `stmt = select(AuditLog).where(AuditLog.tenant_id == ctx.organization_id).order_by(desc(AuditLog.id)).limit(limit).offset(offset)`.

### GAP-P1-01: Registration Profile Completeness & State Mapping
- **Root Cause**: `register_user` in `backend/app/api/v1/endpoints/auth.py` hardcoded `state_id=1` and ignored `req.employment_type`.
- **Authoritative Fix**:
  1. Query `State` table for `State.code == req.state_code.upper()`. If found, use `state.id`; otherwise fallback to default `1`.
  2. Set `employee.employment_type = req.employment_type or "FULL_TIME"`.

### GAP-P1-02: Forgot Password Account Enumeration
- **Root Cause**: `POST /forgot-password` returned `verification_id: str(token.verification_id)` if user existed, and `verification_id: null` if user did not exist.
- **Authoritative Fix**: Always return `verification_id: str(token.verification_id)` for existing active users, or a deterministic pseudo-random UUID for non-existent users, so the JSON response schema and status code are 100% identical.

### GAP-P1-03 & GAP-P1-04: Enterprise Compliance & Real Data
- **Root Cause**: Endpoints lacked dynamic report generation and real query fallbacks.
- **Authoritative Fix**: Implement `POST /api/v1/enterprise/compliance-reports/generate` and `GET /api/v1/enterprise/compliance-reports` scoped to `ctx.organization_id`.

### GAP-P1-05: Ruff Linting
- **Root Cause**: 89 lint issues (F401 unused imports, I001 import ordering) across test files and endpoint modules.
- **Authoritative Fix**: Manually clean all unused imports and format import blocks alphabetically without running `--fix`.

---
