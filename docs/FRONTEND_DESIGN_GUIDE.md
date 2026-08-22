# SmartSalary India — Frontend Design System & UI Implementation Guide

> **Core Philosophy:** *Trust + Financial Clarity + Indian Regulatory Context + Deterministic Intelligence.*  
> Reject generic AI dashboard clichés. Every visual token, component, interaction, motion, and copy choice must be strictly justified by the user's financial task and official statutory evidence.

---

## 1. Architectural Scope & Boundary

This design system and quality standard governs the entire user-facing surface of SmartSalary India while leaving deterministic engines and RAG architecture untouched:

```
Deterministic Core (Untouched)          Frontend UI & Interaction Layer (Governed)
┌────────────────────────────────┐      ┌──────────────────────────────────────────────┐
│ • Tax & Slab Engines (AY 26-27)│      │ • Palette: Ink, Paper, Emerald, Amber, Slate │
│ • PF / EPS / EDLI Calculations │      │ • Typography: Inter / Plus Jakarta Sans      │
│ • ESI & State PT Engines       │ ───► │ • Signature Element: "The Rupee Journey"     │
│ • CalculationSnapshot & Trace  │      │ • Contextual Modes: Individual vs Corporate  │
│ • Vector RAG & Citation Proofs │      │ • "Why?" Disclosure & Statutory Evidence Drawer│
└────────────────────────────────┘      └──────────────────────────────────────────────┘
```

---

## 2. Semantic Financial Color & Token System

Colors encode real financial meaning rather than arbitrary aesthetics:

| Token Name | Hex Value | Semantic Purpose / Context in SmartSalary |
| :--- | :--- | :--- |
| `--color-ink` | `#0F172A` / `#020617` | Deep contrast foreground / text (Dark mode default) |
| `--color-paper` | `#F8FAFC` / `#090D16` | Background foundation |
| `--color-savings` | `#10B981` / `#059669` | Money retained, Net take-home, Growth, Surplus |
| `--color-tax` | `#F97316` / `#EA580C` | Direct Income Tax, TDS withholding, Surcharge, Cess |
| `--color-statutory` | `#8B5CF6` / `#7C3AED` | PF, EPS, EDLI, ESIC, State Professional Tax |
| `--color-expense` | `#64748B` / `#94A3B8` | Rent, Living expenses, Non-statutory outflows |
| `--color-info` | `#3B82F6` / `#2563EB` | Guidance notes, Section references, Exemptions |
| `--color-verified` | `#0D9488` / `#0F766E` | Official CBDT/MoLE Gazette backed calculation citation |
| `--color-anomaly` | `#EF4444` / `#DC2626` | 43B(h) violation, TDS threshold breach, 50% CTC basic violation |

---

## 3. The Signature Element: "The Rupee Journey" (Money Flow)

Every calculation, analytics view, PDF payslip, and chat response anchors around one single unified visualization:

$$\text{Gross CTC} \xrightarrow{\quad} \text{Income Tax} \xrightarrow{\quad} \text{Statutory Deductions} \xrightarrow{\quad} \text{Living Expenses} \xrightarrow{\quad} \mathbf{\text{Net Savings / Take-Home}}$$

### Implementation Rules:
1. **Homepage:** Interactive hero split visualization dynamically balancing ₹1,00,000 monthly CTC in real time.
2. **Calculator Results:** Visual horizontal bar breakdown displaying proportional allocations with dedicated click-to-explain triggers.
3. **PDF Reports & Payslips:** Exact proportional ledger rendering matching web styling.
4. **Contextual AI Chat:** AI explains each step of this exact flow when invoked.

---

## 4. UI Component & Interaction Standards

### A. Calculator Flow (Non-Monolithic)
Instead of a crowded 30-field input form, calculations use a deterministic 6-step guided sequence:
1. `01 Profile` (Age, Resident Status, FY/AY selection)
2. `02 Work` (Salaried, Professional 44ADA, Gig, Director, Govt)
3. `03 Income` (Basic, HRA, Special, Allowances, Perquisites)
4. `04 Deductions` (80C, 80D, 80CCD(2) NPS, Housing Interest 24b)
5. `05 Expenses & Rent` (Metro/Non-Metro HRA exemption data)
6. `06 Review & Calculate` (Old vs New Regime comparison side-by-side)

### B. The "Why?" Explanatory Interaction
Every calculated figure (TDS, PF, Tax Slab, Rebate) includes an inline `[Why?]` pill:
*   Clicking opens a side drawer detailing:
    1. **Mathematical Step:** Exact formula with injected user variables.
    2. **Statutory Authority:** (e.g. *CBDT Notification No. 114/2026 / Section 202*).
    3. **Grounding Citation:** Official link to Gazette / CBDT Schema document.
    4. **AI Deep Dive:** One-click prompt to ask the RAG assistant for optimization.

### C. Data Reality Badges
Data confidence is explicitly encoded:
*   `● ACTUAL`: Recorded historical payroll / tax slip data.
*   `○ ESTIMATED`: Calculated deterministically based on provided user inputs.
*   `◌ PROJECTED`: Future FY forecast based on annualized metrics.

### D. Contextual AI Assistant Modes
*   **General Mode:** System navigation, Indian tax regime definitions, rule comparisons.
*   **Calculation Mode:** Automatically injects the active `CalculationSnapshot` ID into context so queries like *"Why was ₹1,800 deducted?"* answer deterministically with citations.

---

## 5. Motion, Typography & Accessibility Directives

*   **Motion Restraint:**
    *   ✓ Progressive counter animations on final salary figures.
    *   ✓ Smooth width-transition for the money flow breakdown bar.
    *   ✓ Subtle slide-in drawer for "Why?" explanations.
    *   ❌ No bouncing cards, neon glows, full-screen particle canvases, or decorative 3D loaders.
*   **Reduced Motion:** Mandatory `@media (prefers-reduced-motion: reduce)` disabling non-essential transitions.
*   **Typography:** Strict numerical legibility using tabular numerals (`font-feature-settings: 'tnum'`) for currency amounts to ensure perfect vertical alignment across tables and payslips.
*   **Actionable Error States:** Instead of *"Something went wrong"*, specify exact statutory reasons: *"CBDT validation error: Section 80CCD(2) deduction exceeds 14% of Basic + DA for Central Govt employee."*
