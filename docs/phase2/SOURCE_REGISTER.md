# Statutory Source Register & Authority Hierarchy

SmartSalary establishes a strict statutory authority hierarchy. No statutory rule is seeded or calculated without provenance linking to an authoritative source document in this register.

---

## 1. Statutory Authority Hierarchy

### Tier 1 — Primary Statutory Authorities (Absolute Authority)
1. **Central Board of Direct Taxes (CBDT) / Income Tax Department (ITD), Ministry of Finance, Government of India**
   - Official Portal: `https://www.incometax.gov.in`
   - Authority on: Income Tax Slabs, Standard Deductions under Section 16(ia), Section 87A Rebates, Marginal Relief under Finance Acts, Section 115BAC New Regime defaults, Surcharge rates, 4% Health & Education Cess.
2. **Employees' Provident Fund Organisation (EPFO), Ministry of Labour and Employment, Government of India**
   - Official Portal: `https://www.epfindia.gov.in`
   - Authority on: Employees' Provident Funds and Miscellaneous Provisions Act, 1952; EPF Scheme, 1952; EPS Scheme, 1995; EDLI Scheme, 1976.
   - Prescribes: 12% employee contribution, employer 3.67% EPF + 8.33% EPS, ₹15,000 statutory wage ceiling, 0.50% EDLI, admin charges.
3. **State Commercial Taxes / GST Departments (State Governments)**
   - **Maharashtra**: Department of Goods and Services Tax, Government of Maharashtra (`https://www.mahagst.gov.in`) — Maharashtra State Tax on Professions, Trades, Callings and Employments Act, 1975 (Schedule I).
   - **Karnataka**: Commercial Taxes Department, Government of Karnataka (`https://gst.kar.nic.in`) — Karnataka Tax on Professions, Trades, Callings and Employments Act, 1976.
   - **Telangana**: Commercial Taxes Department, Government of Telangana (`https://tgct.gov.in`) — Telangana Tax on Professions, Trades, Callings and Employments Act, 1987.

### Tier 2 — Statutory Gazettes, Notifications & Circulars
- Official Gazette of India notifications (Ministry of Law and Justice, Legislative Department).
- CBDT Circulars & Notifications for Assessment Years AY 2025-26, AY 2026-27, and AY 2027-28.

### Tier 3 — Secondary Analytical Material
- Reputable financial publications and tax calculators (used strictly for secondary sanity checking; NEVER overrides Tier 1/Tier 2).

---

## 2. Verified Statutory Documents Register

| Document ID | Issuing Authority | Reference / Title | Official URL / Source | Verification Status |
|---|---|---|---|---|
| `DOC-ITD-AY2627-SALARIED` | Income Tax Department | Salaried Individuals AY 2026-27 (Return Applicable & Slabs) | `https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1` | **VERIFIED** |
| `DOC-ITD-ESTIMATOR-2026` | Income Tax Department | Income and Tax Estimator User Manual | `https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/income-and-tax-estimator-um` | **VERIFIED** |
| `DOC-FINACT-2024` | Ministry of Finance | The Finance (No. 2) Act, 2024 (Section 115BAC amendments) | Official Gazette Notification | **VERIFIED** |
| `DOC-FINACT-2025` | Ministry of Finance | The Finance Act, 2025 (AY 2026-27 Tax Slabs & Section 87A) | Official Gazette Notification | **VERIFIED** |
| `DOC-EPFO-EMP-BOOKLET` | EPFO India | Employer Information Booklet / Contribution Rates Schedule | `https://www.epfindia.gov.in/site_docs/PDFs/MiscPDFs/Employer_Information_Booklet.pdf` | **VERIFIED** |
| `DOC-MAHAGST-PT-SCHED` | Government of Maharashtra | Profession Tax and Other Rate Schedule (Mahagst) | `https://www.mahagst.gov.in/en/profession-tax-and-other-rate-schedule` | **VERIFIED** |
| `DOC-KAR-PT-SCHED` | Government of Karnataka | Karnataka Profession Tax Act, 1976 Schedule (Rates) | `https://gst.kar.nic.in` | **VERIFIED** |
| `DOC-TEL-PT-SCHED` | Government of Telangana | Telangana Profession Tax Act, 1987 Schedule | `https://tgct.gov.in` | **VERIFIED** |

---

## 3. Strict Verification & Provenance Rules
1. Every calculation snapshot in SmartSalary records `source_document_id` and canonical `source_document_hash`.
2. Missing statutory data for any state/regime will immediately raise a fail-closed exception (`RuleNotFoundError`, `ProfessionalTaxRuleNotConfiguredError`). Zero or fabricated values are prohibited.
