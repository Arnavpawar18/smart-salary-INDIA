# Rate Limit Audit

## Overview
This document records the current state of rate‑limiting, caching, and related infrastructure in the **SmartSalary India** codebase before any modifications are made. It is produced as the first step of the **Phase 1 Repository Audit** defined in the implementation plan.

---

## 1. Existing Rate‑Limiter Implementation

- **File**: `backend/app/core/rate_limiter.py`
- **Class**: `InMemoryRateLimiter`
- **Behavior**:
  - Process‑local sliding‑window limiter using a class‑level `defaultdict` of timestamp lists.
  - Default limits: `max_requests=10` per `window_seconds=60` (hard‑coded in the class method call sites).
  - Provides `check_rate_limit(key, max_requests, window_seconds)` and `get_client_ip(request)` utilities.
- **Scope**:
  - Used by **sensitive endpoints** (login, registration, change‑password) via explicit calls in route handlers (search for `InMemoryRateLimiter.check_rate_limit`).
- **Limitations**:
  - **Process‑local only** – does not work across multiple FastAPI workers or containers.
  - No persistence; limits reset on process restart.
  - No tenant or organization awareness.
  - No `Retry‑After` header or rate‑limit metadata in responses.

---

## 2. Redis Usage in the Project

- **Search Results** (`grep "Redis"` across the repository) indicate **no Redis client integration**.
- No `redis` import statements, no `aioredis`, and no Redis connection configuration in `backend/app/core/config.py` or `.env`.
- **Conclusion**: Redis is **not currently used** for any purpose (caching, session store, or rate‑limiting).

---

## 3. Cache / Expensive‑Endpoint Indicators

- No explicit cache layer (e.g., `fastapi-cache`, `cachetools`) is present.
- All calculation endpoints (`POST /api/v1/calculations`, `compare‑regimes`, etc.) hit the database and perform heavy financial engine work on every request.
- No memoisation or result‑caching observed in `app/services/calculation_service.py`.

---

## 4. Authentication Model

- **Middleware**: `backend/app/core/auth_middleware.py` implements JWT‑based authentication.
- **Dependency helpers**:
  - `get_current_user` – requires a valid JWT and returns a `User` model instance.
  - `get_optional_user` – returns `None` for anonymous requests (used by the calculator page before the audit change).
- **Current state** (post‑audit change):
  - The `/api/v1/calculations` endpoint now **requires** `current_user: User = Depends(get_current_user)`, enforcing authentication for salary calculations.
  - History, detail, and delete endpoints also require `get_current_user`.
- **Authorization**: Ownership checks performed via `Employee` lookup (`Employee.user_id == current_user.id`).

---

## 5. Tenant / Company Model

- The data model includes an `Organization` (tenant) concept in `backend/app/models/organization.py` (not shown here but referenced by other modules).  
- `Employee` records have a foreign key `organization_id` linking them to a tenant.
- No per‑tenant rate‑limit logic currently exists; all limits, if any, are global to the process.

---

## 6. Deployment Environments

- **`.env`** file present at the repository root but **does not contain** a `REDIS_URL` variable.
- `backend/app/core/config.py` loads environment variables for DB URL, secret key, etc., but no Redis configuration.
- Development, staging, and production are expected to run the same FastAPI app behind a reverse proxy (e.g., Nginx) – no environment‑specific rate‑limit settings.

---

## 7. Test Setup

- **Test framework**: `pytest` with FastAPI `TestClient`.
- Existing tests (`backend/tests/test_calculation_api.py`, `test_compare_regimes_api_endpoint`, etc.) assume **authenticated** access for calculation endpoints after the earlier change.
- No tests currently cover rate‑limiting behavior (429 responses, headers, or concurrency).
- New rate‑limit tests will be added after the limiter core is implemented.

---

## 8. Open Items for Phase 2

| Item | Status |
|------|--------|
| Verify that no other hidden rate‑limit implementations exist (e.g., middleware not yet discovered). | ✅ Completed – grep for `RateLimiter` and `limit` returned only `InMemoryRateLimiter`.
| Determine required Redis version and connection parameters for production. | ⬜ Pending – will be defined in **Redis Architecture** section of the plan.
| Identify endpoints that should be protected beyond the current authentication‑only set (RAG, PDF, Payslip, Company payroll). | ⬜ Pending – will be addressed in **Endpoint Protection**.
| Draft environment‑specific fallback behavior for development when Redis is unavailable. | ⬜ Pending – part of **Redis Architecture**.

---

*This audit is a snapshot of the codebase as of 2026‑08‑22. No code modifications have been performed beyond the authentication requirement change already committed.*
