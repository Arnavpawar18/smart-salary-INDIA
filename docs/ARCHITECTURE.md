# SmartSalary Architecture

SmartSalary is a **Python-First Full-Stack Financial Intelligence Platform** engineered for Indian statutory tax, provident fund (PF), and professional tax (PT) compliance.

## High-Level Architecture Overview

```
                          Web Browser
                               │
                       HTML + HTMX + CSS
                               │
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    └──────────┬──────────┘
                               │
                      ┌────────┴────────┐
                      ▼                 ▼
                  Jinja2             REST API
                      │                 │
                      └────────┬────────┘
                               ▼
                            Services
                               │
                       ┌───────┴────────┐
                       ▼                ▼
                Calculation Engine   Data Access
                   (Phase 2)            │
                       │                │
                       └────────┬───────┘
                                ▼
                           PostgreSQL
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
                  Tax/PF      Payslip     RAG/AI
                   Rules      Pipeline   (Phase 7)
```

## Pure Calculation Engine Hard Boundary
- Future engines in `app/engine/` remain pure, deterministic, zero-I/O, database-independent, and framework-independent.
- Database access and orchestration are isolated to `app/services/`.

## Authoritative 40-Table Domain Model
SmartSalary establishes exactly 40 domain tables:
1. **Auth & RBAC (5)**: `users`, `roles`, `permissions`, `user_roles`, `role_permissions`
2. **Employee & Org (5)**: `departments`, `job_roles`, `states`, `employees`, `taxpayer_profiles`
3. **Salary & Income (3)**: `salary_records`, `salary_components`, `income_sources`
4. **Calculation (4)**: `calculation_runs`, `calculation_snapshots`, `calculation_traces`, `calculation_line_items`
5. **Tax Engine (9)**: `tax_periods`, `tax_rule_versions`, `tax_slabs`, `tax_rebates`, `tax_exemptions`, `tax_deductions`, `tax_surcharges`, `tax_cess_rules`, `tax_sources`
6. **Provident Fund (3)**: `pf_rule_versions`, `pf_rules`, `pf_interest_rules`
7. **Professional Tax (2)**: `professional_tax_rule_versions`, `professional_tax_slabs`
8. **Payslip (3)**: `payslip_documents`, `payslip_extractions`, `payslip_validations`
9. **Knowledge / RAG (3)**: `knowledge_documents`, `knowledge_chunks`, `knowledge_sources`
10. **Chat (2)**: `chat_sessions`, `chat_messages`
11. **Audit (1)**: `audit_logs`
