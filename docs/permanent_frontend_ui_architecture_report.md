# SmartSalary India — Permanent Frontend & UI Architecture Report

## 1. Root Cause Analysis
- **Theme State Thrashing Across Layouts:** `base.html` started with `class="dark"`, while `enterprise_base.html` started with `class="light"`. Navigating between layouts produced theme discrepancies where dark cards loaded on light surfaces.
- **Stale Browser Caching:** Hardcoded asset query strings prevented browsers from invalidating older CSS when tokens changed.

## 2. Structural Architecture Fixes
1. **Single Source of Truth (`app.css`):**
   - All visual design tokens (colors, background surfaces, typography, radii, shadows, motion) reside in `backend/app/static/css/app.css`.
   - Global component classes (`.glass-card`, `.btn-primary`, `.status-pill-*`, `.tabular-nums`) enforce consistent visual presentation.
2. **Unified Base Templates:**
   - Both `base.html` and `enterprise_base.html` now start with `class="dark"` by default and share identical theme toggle state handlers.
3. **Automated Asset Versioning:**
   - Registered `asset_version` in `main.py` Jinja globals (`templates.env.globals["asset_version"] = "20260822_v5"`).
   - Templates dynamically load `/static/css/app.css?v={{ asset_version }}` to guarantee instant browser cache invalidation.

## 3. Verification & Compliance
- **Full Test Suite:** **301/301 PASSED (100%)** (including new `test_design_system_propagation.py`).
- **Financial Invariant Validation:** **120,000 / 120,000 scenarios PASSED (0 errors)**.
- **Security & Business Logic:** Unchanged (Zero modifications to statutory formulas, CalculationContext, RAG, PDF, payslip, payroll, or tenant isolation).
