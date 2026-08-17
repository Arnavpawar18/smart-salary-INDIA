# Statutory Professional Tax (State) Rule Matrix

This document records the **verified state-specific Professional Tax schedules** under respective State Acts.

---

## 1. State Coverage & Configuration Status

| State / UT Code | State Name | Statutory Act | Verification Status |
|---|---|---|---|
| **`KA`** | Karnataka | Karnataka Tax on Professions, Trades, Callings and Employments Act, 1976 | **VERIFIED & CONFIGURED** |
| **`MH`** | Maharashtra | Maharashtra State Tax on Professions, Trades, Callings and Employments Act, 1975 | **VERIFIED & CONFIGURED** |
| **`TS`** | Telangana | Telangana Tax on Professions, Trades, Callings and Employments Act, 1987 | **VERIFIED & CONFIGURED** |
| **`DL`** | Delhi | No Professional Tax levied in Delhi | **EXEMPT (₹0)** |
| **OTHER** | Other States/UTs | State-specific rules pending verified research | **NOT_CONFIGURED (Fail-Closed)** |

---

## 2. Verified State Slab Schedules

### 2.1 Karnataka (`KA`)
| Slab Order | Monthly Gross Salary (₹) | Monthly PT (₹) | Annual PT (₹) |
|---|---|---|---|
| **1** | ₹0 to ₹14,999 | ₹0 | ₹0 |
| **2** | ₹15,000 and above | **₹200** | **₹2,400** |

---

### 2.2 Maharashtra (`MH`)
*Note: Under Maharashtra statutory schedule, monthly PT is ₹200 for 11 months and ₹300 for the month of February.*

| Slab Order | Monthly Gross Salary (₹) | Gender Applicable | Monthly PT (₹) | February PT (₹) | Annual PT (₹) |
|---|---|---|---|---|---|
| **1** | ₹0 to ₹7,500 | ALL (Male & Female) | ₹0 | ₹0 | ₹0 |
| **2** | ₹7,501 to ₹10,000 | ALL (Male & Female) | **₹175** | **₹175** | **₹2,100** |
| **3** | ₹10,001 to ₹25,000 | Female only | ₹0 (Exempt) | ₹0 | ₹0 |
| **4** | Above ₹10,000 (Male) / Above ₹25,000 (Female) | ALL | **₹200** | **₹300** | **₹2,500** |

---

### 2.3 Telangana (`TS`)
| Slab Order | Monthly Gross Salary (₹) | Monthly PT (₹) | Annual PT (₹) |
|---|---|---|---|
| **1** | ₹0 to ₹15,000 | ₹0 | ₹0 |
| **2** | ₹15,001 to ₹20,000 | **₹150** | **₹1,800** |
| **3** | Above ₹20,000 | **₹200** | **₹2,400** |

---

## 3. Strict Fail-Closed Policy
If calculation is requested for an unconfigured state, the Professional Tax engine raises `ProfessionalTaxRuleNotConfiguredError` rather than defaulting to ₹0.
