# SMART SALARY INDIA — SYSTEM ARCHITECTURE SPECIFICATION

> **Tagline:** Know Your Salary. Understand Your Tax. Control Your Money.  
> **Secondary Tagline:** AI-powered. Government-source verified. State-aware. Continuously updated.  
> **Core Principle:** AI explains. Deterministic code calculates. Government sources provide evidence.

---

## 1. Executive Summary & Product Architecture

**Smart Salary India** is a high-precision, production-grade fintech and regulatory intelligence platform for Indian employees, enterprises, freelancers, and businesses. 

```
                                  SMART SALARY INDIA PLATFORM
                                               │
         ┌─────────────────────────────────────┴─────────────────────────────────────┐
         ▼                                                                           ▼
   [ INDIVIDUAL ]                                                              [ COMPANY ]
   • Take-home & CTC Calculator                                                • Organization & Multi-Tenancy
   • Salary X-Ray (Component breakdowns)                                       • Employee Lifecycle Management
   • Tax Regime Optimizer (Old vs New)                                         • Salary Structure Designer
   • State-by-State Deduction Comparator                                       • Monthly Automated Payroll Engine
   • Payslip & Offer Letter OCR Extractor                                      • Statutory Compliance Center
   • Annual Projection & What-If Simulator                                     • Form 16 / Register Exports (PDF/XLSX)
         │                                                                           │
         └─────────────────────────────────────┬─────────────────────────────────────┘
                                               │
                                               ▼
                         ┌───────────────────────────────────────────┐
                         │   DETERMINISTIC CALCULATION CORE (PYTHON) │
                         │   - Income Tax (Old/New Regimes, Slabs)   │
                         │   - Provident Fund (EPF/EPS ceilings)     │
                         │   - ESI (Gross wage ceilings & exemptions)│
                         │   - State Professional Tax (PT Slabs)     │
                         │   - Gratuity (Payment of Gratuity Act)    │
                         └─────────────────────┬─────────────────────┘
                                               │
                                               ▼
                         ┌───────────────────────────────────────────┐
                         │    REGULATORY INTELLIGENCE & RAG LAYER    │
                         │   - Government Sources (EPFO, CBDT, etc.) │
                         │   - Versioned Rule Database               │
                         │   - Hybrid Retrieval (Dense + BM25)       │
                         │   - Rule Tracing & Source Citations       │
                         │   - "Ask Salary AI" Explanation Engine    │
                         └───────────────────────────────────────────┘
```

---

## 2. Layered Technical Architecture

### 2.1 Backend Layer (Python / FastAPI / SQLAlchemy / PostgreSQL)
* **Framework:** Python 3.13+ with FastAPI for high-throughput asynchronous REST APIs.
* **ORM & Database:** SQLAlchemy 2.0 (Core + ORM) backed by PostgreSQL 16+ with connection pooling and Alembic for strict migration versioning.
* **Deterministic Financial Engine:** Pure Python classes utilizing exact arithmetic (`decimal.Decimal` with 2/4 decimal precision) ensuring IEEE-754 float drift is strictly avoided.
* **Modular Domain Structure:**
  * `app/engine/tax/`: Income Tax computation (Sections 87A, 115BAC, 80C/80D deductions, marginal relief, surcharge, cess).
  * `app/engine/pf/`: Statutory EPF & EPS with standard ₹15,000 ceiling capping or voluntary actual basic calculation.
  * `app/engine/professional_tax/`: State-specific PT rules covering Karnataka, Maharashtra, Telangana, Tamil Nadu, West Bengal, Gujarat, etc.
  * `app/engine/esi/`: ESI contribution engine respecting wage caps (₹21,000 threshold).
  * `app/engine/gratuity/`: Gratuity calculations under Payment of Gratuity Act 1972.
  * `app/engine/rag/`: Hybrid search retriever with metadata filters for regulatory documents.

### 2.2 Frontend Layer (React + TypeScript + Vite + Tailwind CSS / shadcn/ui)
* **Framework:** React 19 + TypeScript + Vite for ultra-fast HMR and bundle optimization.
* **Design System & Aesthetics:** Glassmorphism, Tailwind CSS, Lucide icons, Framer Motion for micro-interactions and smooth animated counters.
* **Visualizations:** Recharts for dynamic salary waterfall breakdowns, tax regime comparisons, and monthly payroll registers.
* **Architecture:** Modular component library (`components/ui`, `components/calculator`, `components/salary-xray`, `components/company`, `components/sources`, `components/ai-assistant`).

---

## 3. The Core Rule: Calculation vs Explanation Separation

```
[ Government Notification / Gazette / Act ]
                 │
                 ▼
[ Regulatory Knowledge Ingestion & Admin Verification ]
                 │
                 ▼
[ Versioned Production Rules (DB: tax_rules, pf_rules, pt_rules) ]
                 │
                 ├──────────────────────────────┐
                 ▼                              ▼
  [ Deterministic Calculation Engine ]    [ RAG Vector Store & Metadata ]
  - Takes verified rules                  - Stores official PDF chunks
  - Executes exact formulas               - Indexed by rule_id & notification
  - Emits CalculationTrace & Result       - Provides context to LLM
                 │                              │
                 └──────────────┬───────────────┘
                                ▼
         [ User Interface: Results + Salary X-Ray ]
         • Exact Numbers (Deterministic Engine)
         • "Why did this apply?" (RAG Explanation)
         • Official Government Source Citation & Notification Link
```

---

## 4. Security, Tenancy & Compliance Architecture
1. **Authentication:** Argon2id password hashing, JWT/Session security, and multi-factor/email OTP.
2. **Tenant Isolation:** Row-Level Tenant Security (`tenant_id`/`organization_id`) enforced at repository layer.
3. **Audit Trails:** Immutable `calculation_runs` and `audit_logs` storing inputs, output breakdown, and exact active `rule_version_id`.
4. **Data Privacy:** PII and salary fields encrypted at rest where required; no sensitive details exposed in client logs or telemetry.
