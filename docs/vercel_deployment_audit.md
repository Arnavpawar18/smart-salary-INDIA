# SmartSalary India — Vercel Deployment Architecture & Verification Audit

| Document Version | 1.1.0 (Setuptools Wheel Resolution Verified) |
| :--- | :--- |
| **Audit Date** | August 22, 2026 |
| **Repository Root** | `D:\Smart_salary_india` |
| **Authoritative ASGI Application** | `backend/app/main.py` (`app.main:app`) |
| **Vercel Serverless Adapter** | `backend/api/index.py` |
| **Package Package Root** | `backend/` with `app/` subpackage (contains `__init__.py`) |
| **Build Backend** | `setuptools.build_meta` (PEP 621 compliant) |
| **Python Runtime** | `Python 3.13` (Synchronized across `pyproject.toml`, `.python-version`, and `vercel.json`) |
| **Pytest Regression Suite** | **327 Passed, 0 Failures, 0 Errors** |
| **120k Financial Validation** | **120,000 / 120,000 Passed (0 Mismatches, 0 Violations)** |
| **Ruff Linter** | **0 Errors, 0 Warnings** (`ruff check backend/app backend/tests`) |
| **Status** | **PASS — SETTOOLS PACKAGE DEFINITION REPAIRED & WHEEL BUILD VERIFIED** |

---

## 1. Forensic Root Cause Analysis

### A. The Exact Vercel Build Failure
When Vercel builds the project, it runs:
```bash
uv sync --active --no-dev --link-mode hardlink --locked --no-editable
```
which calls:
```text
The build backend returned an error
Call to setuptools.build_meta.build_wheel failed

configuration error:
`tool.setuptools.packages` must be valid exactly by one definition
(0 matches found)
```

### B. Root Causes Identified
1. **Misplaced `dependencies` Key in `pyproject.toml`**:
   In `backend/pyproject.toml`, the `dependencies = [...]` block was placed immediately after `[tool.setuptools.packages.find]`. Under TOML specification rules, `dependencies` was treated as a sub-property of `tool.setuptools.packages.find`, which violated the setuptools package schema.
2. **Missing `__init__.py` in `backend/app`**:
   `backend/app/__init__.py` was missing, preventing `setuptools.packages.find` from recognizing `app` as a valid Python package root.

---

## 2. Packaging & Build Repairs Applied

### A. Repaired `backend/pyproject.toml`
- Moved `dependencies` into the root `[project]` table in compliance with PEP 621.
- Cleanly isolated `[tool.setuptools.packages.find]` to specify `where = ["."]`, `include = ["app*"]`, and `exclude = ["alembic*", "tests*"]`.
- Added `[tool.setuptools.package-data]` for static files and templates:
  ```toml
  [tool.setuptools.package-data]
  "app" = ["templates/**/*", "static/**/*"]
  ```

### B. Created `backend/app/__init__.py`
- Added explicit package marker `backend/app/__init__.py`.

### C. Wheel Build Verification
Ran isolated wheel build:
```bash
cd backend
python -m build --wheel --no-isolation
```
Result:
```text
Successfully built smartsalary_backend-0.1.0-py3-none-any.whl
```
Wheel contains all `app/*` modules, `api/`, `core/`, `models/`, `services/`, `static/`, and `templates/`.

---

## 3. Local Verification & Endpoint Smoke Tests

Local server parity verified against `http://127.0.0.1:8000`:

| Route | HTTP Status | Notes |
| :--- | :---: | :--- |
| `GET /` | **200 OK** | Landing page renders with verified lineage banner |
| `GET /api/v1/health` | **200 OK** | Health check returns JSON status |
| `GET /static/css/app.css` | **200 OK** | Design system CSS stylesheet served |
| `GET /static/js/app.js` | **200 OK** | Client application script served |
| `GET /calculator` | **200 OK** | Interactive calculator interface rendered |
| `GET /tax-center` | **401 Unauthorized** | Protected employee portal route |
| `GET /help` | **200 OK** | Knowledge base and FAQ rendered |
| `GET /login` | **200 OK** | Authentication portal rendered |
| `GET /register` | **200 OK** | Registration portal rendered |
| `GET /enterprise` | **401 Unauthorized** | Protected enterprise RBAC portal |

---

## 4. Master Quality Gates

- **Full Pytest Suite**: 327 / 327 Passed in 16.88s (0 failures, 0 errors).
- **120k Financial Validation**: 120,000 / 120,000 Passed in 2.09s (0 tax mismatches, 0 PF mismatches, 0 ESI mismatches, 0 PT mismatches, 0 security violations, 0 tenant violations).
- **Ruff Code Quality**: 0 Errors, 0 Warnings (`ruff check backend/app backend/tests`).
- **Git Security**: Zero sensitive files, secrets, or virtual environments tracked.
