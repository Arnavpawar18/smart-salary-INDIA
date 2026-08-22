# SMART SALARY INDIA — MASTER ROADMAP & IMPLEMENTATION PLAN

---

## Phase Breakdown & Milestone Schedule

### Phase 1: Foundation & Design System (Current Milestone)
* **Goal:** Core domain design, high-performance UI shell with glassmorphic fintech design system, responsive layout, auth schemas, and baseline deterministic engines.
* **Deliverables:**
  * Master Design System tokens (Tailwind / CSS variables / Typography / Reusable UI).
  * Interactive Homepage with animated salary waterfall and "Calculate My Salary" / "Calculate My Tax" CTAs.
  * Auth flow (Minimal, privacy-first registration + login + session/JWT security).
  * Progressive Individual Onboarding (Employment Type, Industry, State/Location, Company, Salary details).

### Phase 2: Individual Salary Intelligence & Salary X-Ray
* **Goal:** High-precision interactive salary calculation and deep breakdown.
* **Deliverables:**
  * Instant CTC to Take-Home calculation with interactive dynamic charts.
  * **Salary X-Ray Engine:** Clickable deductions (Tax, EPF, EPS, ESI, PT) with granular calculation explanations, statutory rules, and official citations.
  * Old vs New Tax Regime interactive comparison with optimal regime recommendation.
  * Monthly, Quarterly, and Half-Yearly detailed projection views.

### Phase 3: Regulatory Rule Engine & Multi-State Parity
* **Goal:** Versioned database-backed rules and state-aware statutory engines.
* **Deliverables:**
  * Multi-state Professional Tax engine covering all Indian states & UTs (Karnataka, Maharashtra, Telangana, TN, Gujarat, WB, etc.).
  * Central EPF/EPS & ESI engines handling statutory wage ceilings and voluntary contributions.
  * Rule versioning, effective date ranges, and government notification links.
  * State comparison tool (e.g. Karnataka vs Maharashtra take-home differences).

### Phase 4: AI Payslip & Offer Letter OCR Extractor
* **Goal:** Intelligent document ingestion without calculation guesswork.
* **Deliverables:**
  * Secure PDF/Image upload pipeline (PyMuPDF / OCR engine).
  * Structured component extraction (Basic, HRA, Special Allowance, PF, PT, TDS).
  * Human-in-the-loop review modal ("We extracted these components. Please verify before calculation").

### Phase 5: Annual Salary Report & Projections
* **Goal:** 12-month variable income calculation and official document generation.
* **Deliverables:**
  * Monthly breakdown editor supporting irregular bonuses and variable incentives.
  * Professional PDF & Excel export for annual salary statements and tax computation summaries.

### Phase 6: What-If Salary Simulator
* **Goal:** Scenario planning and increment negotiation assistant.
* **Deliverables:**
  * Incremental CTC sliders (e.g., ₹12 LPA -> ₹18 LPA).
  * Tax bracket shift impact and net take-home increment calculator.
  * Salary restructuring advisor (Optimal HRA, Food coupons, NPS 80CCD(2)).

### Phase 7 & 8: Company Enterprise & Automated Payroll Engine
* **Goal:** Multi-tenant organization workspace with statutory payroll calculation.
* **Deliverables:**
  * RBAC Matrix (Super Admin, HR Admin, Payroll Admin, Finance, Employee).
  * Employee Directory and Salary Structure templates with statutory validation.
  * Automated Monthly Payroll Run (Gross -> Deductions -> Net -> Payslip generation).
  * Statutory compliance reports (EPF ECR format, ESI return, Form 24Q TDS summary, PT chalan).

### Phase 9: Regulatory RAG & "Ask Salary AI"
* **Goal:** Evidence-backed AI explanations grounded in verified government documents.
* **Deliverables:**
  * Hybrid retrieval (dense embeddings + BM25 keyword matching) with metadata filtering.
  * Reranking and citation injection linking answers directly to EPFO/CBDT circulars.
  * Dedicated interactive chat assistant.

### Phase 10: Automated Regulatory Monitor & Update Pipeline
* **Goal:** Continuous tracking of official government notifications.
* **Deliverables:**
  * Scheduled scraper/watcher for EPFO, CBDT, and State gazette notifications.
  * Candidate rule extraction -> conflict detection -> admin approval workflow.
