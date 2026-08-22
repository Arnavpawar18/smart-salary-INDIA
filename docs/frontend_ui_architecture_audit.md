# SmartSalary India — Frontend & UI Architecture Forensic Audit

## 1. Executive Summary
This forensic audit identifies the structural causes preventing consistent Stitch UI rendering across Chrome and Edge.

## 2. Identified Sources & Conflicts

### A. Template Initial Class Discrepancy
- `base.html` line 2: `<html lang="en" class="dark">`
- `enterprise_base.html` line 2: `<html lang="en" class="light">`
- **Impact:** Navigating from enterprise to public pages (or vice versa) caused theme state thrashing when `localStorage.getItem('theme')` was unset, resulting in the default "light" background loading dark-mode cards with low contrast.

### B. Static Cache Invalidation Strategy
- Templates currently use hardcoded `?v=20260821` queries in `<link rel="stylesheet" href="/static/css/app.css?v=20260821">`.
- **Solution:** Provide an automated, centralized asset versioning helper in Jinja context or update global asset versioning to guarantee instant cache-busting.

### C. Tailwind CDN vs Authoritative CSS System
- `<script src="https://cdn.tailwindcss.com"></script>` provides layout utilities (`flex`, `grid`, `space-y-*`, `p-*`, `gap-*`).
- **Conflict Resolution:** All visual attributes (colors, background surfaces, typography, borders, shadows, radii, and transitions) are governed exclusively by `app.css` design tokens (`:root` and `html.dark`).
- **Load Order:** `app.css` is loaded **after** Tailwind CDN, ensuring custom properties and `.glass-card`, `.btn-primary`, `.status-pill-*` take precedence over default styles.

### D. Centralized Design Token Inventory in `app.css`
- Brand: `--color-brand-primary`, `--color-brand-primary-hover`, `--color-brand-primary-glow`
- Semantic: `--color-success`, `--color-warning`, `--color-danger`
- Surfaces: `--bg-canvas`, `--bg-surface`, `--bg-surface-elevated`, `--bg-subtle`
- Typography: `--font-heading`, `--font-body`, `--font-mono`
- Radii: `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-xl`, `--radius-2xl`, `--radius-full`
- Motion: `--transition-fast`, `--transition-normal`, `--transition-slow`
