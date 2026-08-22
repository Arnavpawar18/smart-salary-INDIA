# Milestone M9: Regulatory Coverage Matrix

**Verification Scope**: Comprehensive coverage across Indian employment types, salary brackets, and statutory deduction categories.

---

## 1. Domain Coverage

| Statutory Domain | Covered Acts / Schemes | Engine Module | Oracle Validated | Status |
|---|---|---|---|---|
| **Income Tax (New Regime)** | Income-tax Act, 1961 & 2025; Finance Act 2024 | `app.engine.tax` | Yes (`IndependentRegulatoryOracle`) | **VERIFIED** |
| **Income Tax (Old Regime)** | Chapter VI-A (80C, 80D), Section 115BAC Opt-Out | `app.engine.tax` | Yes | **VERIFIED** |
| **Section 87A Rebate** | Full rebate up to statutory limits + marginal relief | `app.engine.tax.rebates` | Yes | **VERIFIED** |
| **Surcharges & Cess** | 10%, 15%, 25% slabs with marginal relief; 4% Cess | `app.engine.tax.surcharge` | Yes | **VERIFIED** |
| **Provident Fund (EPF/EPS)** | EPF & MP Act 1952 (12% employee / employer split) | `app.engine.pf` | Yes | **VERIFIED** |
| **Professional Tax (PT)** | KA, MH, TS, WB, GJ, TN State Schedules | `app.engine.professional_tax` | Yes | **VERIFIED** |
| **Section 288B Rounding** | Statutory rounding to nearest ₹10 | `app.engine.common.rounding`| Yes | **VERIFIED** |

---

## 2. Test Execution Proof
- Tests Executed: `backend/tests/test_m9_*.py`
- Test Pass Rate: **35 / 35 (100%)**
