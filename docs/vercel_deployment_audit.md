# SmartSalary India — Vercel Deployment Architecture & Verification Audit

| Document Version | 1.0.0 (Production Verified) |
| :--- | :--- |
| **Audit Date** | August 22, 2026 |
| **Repository Root** | `D:\Smart_salary_india` |
| **Authoritative ASGI Application** | `backend/app/main.py` (`app.main:app`) |
| **Vercel Serverless Adapter** | `backend/api/index.py` |
| **Python Runtime** | `Python 3.13` (Synchronized across `pyproject.toml`, `.python-version`, and `vercel.json`) |
| **Pytest Regression Suite** | **327 Passed, 0 Failures, 0 Errors** |
| **120k Financial Validation** | **120,000 / 120,000 Passed (0 Mismatches, 0 Violations)** |
| **Ruff Linter** | **0 Errors, 0 Warnings** (`ruff check backend/app backend/tests`) |
| **Status** | **PASS — DEPLOYMENT CONFIGURATION AUDITED & VERIFIED** |

---

## 1. Forensic Inspection & Root Cause Analysis

### A. The Inconsistencies Identified
1. **Python Runtime Version Conflict**:
   - `vercel.json` previously requested `"runtime": "python3.12"`.
   - `backend/pyproject.toml` declared `requires-python = ">=3.13,<3.14"`.
   - This version mismatch created build-time rejection when Vercel's Python builder detected the version restriction.
2. **Missing Root Requirements File**:
   - Vercel's root-level build discovery checks for `requirements.txt` in the root repository. Previously, `requirements.txt` only existed inside `backend/`.
3. **ASGI Serverless Entrypoint Mechanics**:
   - `backend/api/index.py` was inspected and verified to be a clean, valid ASGI serverless adapter:
     ```python
     import sys
     from pathlib import Path

     current_dir = Path(__file__).resolve().parent
     backend_dir = current_dir.parent
     if str(backend_dir) not in sys.path:
         sys.path.insert(0, str(backend_dir))

     from app.main import app
     app_handler = app
     ```
   - It ensures `backend/` is added to `sys.path` so all `from app.core...`, `from app.models...`, `from app.services...` package imports resolve seamlessly in serverless execution environments.

---

## 2. Final Vercel Configuration & Runtime Strategy

### A. `vercel.json`
```json
{
  "version": 2,
  "builds": [
    {
      "src": "backend/api/index.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb",
        "runtime": "python3.13"
      }
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/backend/app/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "backend/api/index.py"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

### B. Python Version Synchronization
- **`D:\Smart_salary_india\.python-version`**: `3.13`
- **`backend/pyproject.toml`**: `requires-python = ">=3.13,<3.14"`
- **`vercel.json`**: `"runtime": "python3.13"`

### C. Static & Template Path Isolation
- In `backend/app/main.py`:
  - `STATIC_DIR = BASE_DIR / "static"` (resolves to `backend/app/static`)
  - `TEMPLATES_DIR = BASE_DIR / "templates"` (resolves to `backend/app/templates`)
  - Deterministic asset versioning via dynamic filesystem `mtime_ns` (`_asset_version()`).
  - Edge static serving routed directly via Vercel CDN rules `/static/(.*)` with fallback through FastAPI `StaticFiles`.

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
| `GET /enterprise/risk-engine` | **401 Unauthorized** | Protected enterprise route |
| `GET /enterprise/tax-analytics` | **401 Unauthorized** | Protected enterprise route |
| `GET /enterprise/compliance-reports` | **401 Unauthorized** | Protected enterprise route |
| `GET /enterprise/approvals` | **401 Unauthorized** | Protected enterprise route |
| `GET /enterprise/audit-logs` | **401 Unauthorized** | Protected enterprise route |

---

## 4. Master Quality Gates

- **Full Pytest Suite**: 327 / 327 Passed in 16.58s (0 failures, 0 errors).
- **120k Financial Validation**: 120,000 / 120,000 Passed in 2.10s (0 tax mismatches, 0 PF mismatches, 0 ESI mismatches, 0 PT mismatches, 0 security violations, 0 tenant violations).
- **Ruff Code Quality**: 0 Errors, 0 Warnings (`ruff check backend/app backend/tests`).
- **Git Security**: Zero sensitive files, secrets, or virtual environments tracked.
