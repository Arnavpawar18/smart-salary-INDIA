# SmartSalary India — Final Statutory & Regulatory Provenance Matrix (Phase 1–26)

## 1. Statutory Provenance & Legal Citation Mapping

| Regulatory Domain | Governing Statute / Gazette / Notification | Baseline Rate / Ceiling / Formula | Invariant Verified | Status |
|---|---|---|---|---|
| **Income Tax (New Regime AY 26-27)** | Income-tax Act, 2025 / Section 115BAC (CBDT) | 0-4L (0%), 4-8L (5%), 8-12L (10%), 12-16L (15%), 16-20L (20%), 20-24L (25%), >24L (30%) | Standard Deduction INR 75,000; Section 87A rebate full up to INR 12L; Section 87A Marginal Relief | **VERIFIED** |
| **Income Tax (Old Regime)** | Income-tax Act, 1961 (as amended) | 0-2.5L (0%), 2.5-5L (5%), 5-10L (20%), >10L (30%) | Standard Deduction INR 50,000; Section 87A rebate up to INR 12,500 for income <= INR 5L | **VERIFIED** |
| **Provident Fund (EPFO)** | Employees' Provident Funds and Miscellaneous Provisions Act, 1952 | Employee EPF: 12.00%; Employer EPF: 3.67%; Employer EPS: 8.33%; EDLI: 0.50% | Statutory ceiling INR 15,000/month; Uncapped voluntary opt-in supported | **VERIFIED** |
| **Employees' State Insurance (ESIC)** | Employees' State Insurance Act, 1948 | Employee: 0.75%; Employer: 3.25% | Statutory gross threshold INR 21,000/month; Zero deduction when gross exceeds threshold | **VERIFIED** |
| **Professional Tax (Karnataka)** | Karnataka Tax on Professions, Trades, Callings and Employments Act, 1976 | Gross < 15,000: INR 0; Gross >= 15,000: INR 200/month (Annual: INR 2,400) | Strictly applied to KA jurisdiction | **VERIFIED** |
| **Professional Tax (Maharashtra)** | Maharashtra State Tax on Professions, Trades, Callings and Employments Act, 1975 | Gross <= 7,500 (Male): INR 0; 7,501-10,000: INR 175; > 10,000: INR 200 (Feb: INR 300; Annual: INR 2,500) | February seasonal adjustment (INR 300) deterministic invariant | **VERIFIED** |
| **Professional Tax (Telangana)** | Telangana Tax on Professions, Trades, Callings and Employments Act, 1987 | 0-15k: INR 0; 15,001-20,000: INR 150; > 20,000: INR 200 (Annual: INR 2,400) | Strictly isolated to TS jurisdiction | **VERIFIED** |
| **Professional Tax (Delhi / Exempt)** | N/A | Delhi NCT has NO Professional Tax | Verified zero PT deduction across all salary levels | **VERIFIED** |
| **Tax Rounding Invariant** | Income Tax Act Section 288B | Final total tax rounded to nearest multiple of INR 10 | Exact modulo 10 rounding invariant | **VERIFIED** |
| **High Income Surcharge & Marginal Relief** | Finance Act Brackets (>50L, >1Cr, >2Cr, >5Cr) | 10%, 15%, 25%, 37% (Old) / 25% (New) | Exact CBDT marginal relief capping formula | **VERIFIED** |

---

## 2. Temporal Versioning & Unverified Future Rule Isolation

SmartSalary implements fail-closed temporal enforcement:
- **Active Past / Current Rules**: Loaded deterministically by Financial Year (`2024-25`, `2025-26`, `2026-27`).
- **Unverified Future Rules (`2028-29`)**: Fail-closed rejection (`RuleNotFoundError` / `BLOCKED_FUTURE_UNVERIFIED`). Zero speculative forward projection.
