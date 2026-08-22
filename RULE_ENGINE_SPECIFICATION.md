# SMART SALARY INDIA — DETERMINISTIC RULE ENGINE SPECIFICATION

> **Core Axiom:** Financial math is strictly deterministic. Rates, ceilings, and exemption formulas come from versioned, verified statutory records.

---

## 1. Rule Model & Data Schema

Every statutory rule (Tax, PF, ESI, PT, Gratuity) conforms to the versioned statutory rule interface:

```json
{
  "rule_id": "TAX-115BAC-FY2526",
  "tax_type": "INCOME_TAX",
  "jurisdiction": "CENTRAL",
  "state_code": null,
  "taxpayer_type": "INDIVIDUAL",
  "regime": "NEW",
  "financial_year": "2025-26",
  "assessment_year": "2026-27",
  "standard_deduction": 75000.00,
  "slabs": [
    {"min": 0, "max": 400000, "rate": 0.00},
    {"min": 400000, "max": 800000, "rate": 0.05},
    {"min": 800000, "max": 1200000, "rate": 0.10},
    {"min": 1200000, "max": 1600000, "rate": 0.15},
    {"min": 1600000, "max": 2000000, "rate": 0.20},
    {"min": 2000000, "max": 2400000, "rate": 0.25},
    {"min": 2400000, "max": null, "rate": 0.30}
  ],
  "rebate_87a": {
    "threshold": 1200000.00,
    "max_rebate": 60000.00,
    "marginal_relief_enabled": true
  },
  "cess_rate": 0.04,
  "effective_from": "2025-04-01",
  "effective_until": "2026-03-31",
  "source_authority": "CBDT / Ministry of Finance",
  "source_notification": "Finance Act 2025",
  "source_url": "https://incometaxindia.gov.in/...",
  "version": "1.0.0",
  "verified_at": "2025-04-01T00:00:00Z",
  "status": "ACTIVE"
}
```

---

## 2. Provident Fund (EPF & EPS) Engine Specification

* **Statutory Authority:** Employees' Provident Fund Organisation (EPFO)
* **Wage Definition:** Basic Salary + Dearness Allowance (DA) + Retaining Allowance
* **Statutory Wage Ceiling:** ₹15,000 / month
* **Employee Contribution:** 12% of PF Wage (capped at ₹1,800/mo if standard ceiling is chosen, or 12% of actual basic if voluntary uncapped PF is opted).
* **Employer Contribution:**
  * **EPS (Pension):** 8.33% of PF wage (statutory max ₹1,250/mo).
  * **EPF (Difference):** 3.67% of PF wage + remainder above ₹1,250.
  * **EDLI:** 0.50% (capped at ₹75/mo).
  * **Admin Charges:** 0.50% (min ₹500/mo for establishment).

---

## 3. Employees' State Insurance (ESI) Engine Specification

* **Statutory Authority:** Employees' State Insurance Corporation (ESIC)
* **Coverage Threshold:** Gross Monthly Wages $\le$ ₹21,000 (₹25,000 for Persons with Disabilities).
* **Employee Contribution:** 0.75% of Gross Monthly Wage.
* **Employer Contribution:** 3.25% of Gross Monthly Wage.
* **Exemption:** Daily average wage up to ₹176 is exempt from employee contribution (employer pays 3.25%).

---

## 4. State Professional Tax (PT) Engine Specification

State-aware tiered slabs based on monthly gross salary:

### 4.1 Karnataka (PT Act 1976 / Amendment 2023)
* Gross Salary $\le$ ₹24,999/mo: ₹0
* Gross Salary $\ge$ ₹25,000/mo: ₹200 / month

### 4.2 Maharashtra (State Tax on Professions Act 1975)
* Gross Salary $\le$ ₹7,500 (Men) / $\le$ ₹25,000 (Women): ₹0
* Men ₹7,501 to ₹10,000: ₹175 / month
* Men/Women > ₹10,000 / ₹25,000: ₹200 / month (₹300 in February to total ₹2,500/year)

### 4.3 Telangana & Andhra Pradesh
* Slabs: ₹0 up to ₹15,000; ₹150 for ₹15,001–₹20,000; ₹200 for > ₹20,000/month.

---

## 5. Gratuity Calculation Engine Specification

* **Statutory Authority:** Payment of Gratuity Act, 1972
* **Eligibility:** Minimum 5 years of continuous service (exempt in case of death/disablement).
* **Formula (Covered under Act):**
$$\text{Gratuity} = \frac{15 \times \text{Last Drawn Basic + DA} \times \text{Years of Service}}{26}$$
* **Statutory Tax-Free Ceiling:** ₹20,00,000 (Section 10(10)).
