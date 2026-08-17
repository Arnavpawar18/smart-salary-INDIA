# SmartSalary Phases 4–7 — Master Product & Architecture Roadmap

> **Authoritative Baseline:** Phases 1–3 are verified and passing 55/55 tests.
> **Master Principle:**
> - Phase 2 owns financial calculations.
> - Phase 4 owns identity and access.
> - Phase 5 owns enterprise workflows.
> - Phase 6 owns evidence extraction.
> - Phase 7 owns grounded explanation.

---

## 1. Consolidated Phase Structure

| Phase | Phase Name | Primary Capabilities | Milestone Gate |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Foundation & Schema** | Python-First FastAPI + 40 Domain Tables + Alembic | ✅ Verified |
| **Phase 2** | **Deterministic Engine** | Slabs, 87A Rebate, Cess, EPFO PF, State PT, Traces, Snapshots | ✅ Verified (`tag: phase2-verified`) |
| **Phase 3** | **Employee Financial Intelligence** | Quick/Detailed UI, Projections, What-If Simulator, Export | ✅ Verified |
| **Phase 4** | **Identity, Security & Employee Platform** | Argon2id, Persistent `user_sessions` (41st table), RBAC, Object Auth, CSRF | `tag: phase4-verified` |
| **Phase 5** | **Enterprise Operations** | HR Portal, Payroll Lifecycle, 6-Stage Compliance, Admin | `tag: phase5-verified` |
| **Phase 6** | **Payslip Intelligence** | PDF/OCR Ingestion, Extraction Provenance, Multi-Status Reconciliation | `tag: phase6-verified` |
| **Phase 7** | **Grounded Financial AI** | Official Knowledge RAG, Numerical Grounding, AI Abstention, Benchmark | `tag: phase7-verified` |

---

## 2. End-to-End Intelligence Version Chain

```text
┌──────────────────────────────────────────────────────────┐
│ CALCULATION ENGINE VERSION   : CALC-1.0.0               │
│ TAX STATUTORY RULE VERSION   : TRV-2025-26-NEW-v1       │
│ PF STATUTORY RULE VERSION    : PFRV-2025-26-v1          │
│ PT STATUTORY RULE VERSION    : KA-PT-2025-26-v1         │
│ STATUTORY ROUNDING POLICY    : ROUND-1.0.0              │
│ PAYSLIP EXTRACTOR VERSION    : EXTRACT-1.0.0            │
│ OCR ENGINE & VERSION         : TESSERACT-5.x            │
│ RAG RETRIEVAL PIPELINE       : RAG-1.0.0                │
│ PROMPT ARCHITECTURE VERSION  : PROMPT-1.0.0             │
│ LLM MODEL & SNAPSHOT ID      : provider/model-version   │
└──────────────────────────────────────────────────────────┘
```

Full details are documented in [implementation_plan.md](file:///C:/Users/pawar/.gemini/antigravity-ide/brain/5dc0d3e2-5224-400a-82df-e6a1c48d0802/implementation_plan.md).
