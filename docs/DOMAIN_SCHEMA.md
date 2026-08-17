# SmartSalary Domain Schema (Authoritative 40 Tables)

This document establishes the frozen inventory of all 40 domain entities in SmartSalary.

| # | Table Name | Domain Group | Primary Responsibility |
|---|---|---|---|
| 1 | `users` | Auth / RBAC | Platform user accounts |
| 2 | `roles` | Auth / RBAC | RBAC role definitions |
| 3 | `permissions` | Auth / RBAC | Fine-grained permission codes |
| 4 | `user_roles` | Auth / RBAC | Association table: User ↔ Role |
| 5 | `role_permissions` | Auth / RBAC | Association table: Role ↔ Permission |
| 6 | `departments` | Employee & Org | Organization departmental structures |
| 7 | `job_roles` | Employee & Org | Job classifications & designations |
| 8 | `states` | Employee & Org | 28 States & 8 Union Territories |
| 9 | `employees` | Employee & Org | Employee profiles (`user_id` unique) |
| 10 | `taxpayer_profiles` | Employee & Org | Tax identity, PAN, regime choice (`employee_id` unique) |
| 11 | `salary_records` | Salary & Income | Effective salary periods and CTC figures |
| 12 | `salary_components` | Salary & Income | Earnings, deductions, allowances |
| 13 | `income_sources` | Salary & Income | Multi-head income sources (SALARY in Phase 1) |
| 14 | `calculation_runs` | Calculation | Calculation execution records & summary results |
| 15 | `calculation_snapshots` | Calculation | Immutable JSONB snapshots + canonical SHA-256 hashes |
| 16 | `calculation_traces` | Calculation | Step-by-step mathematical calculation trace logs |
| 17 | `calculation_line_items`| Calculation | Breakdown line items (Gross, Exemptions, Deductions, Slabs) |
| 18 | `tax_periods` | Tax Engine | Statutory Financial Years (FY 2024-25, 2025-26, 2026-27) |
| 19 | `tax_rule_versions` | Tax Engine | Versioned compliance by regime (OLD / NEW) |
| 20 | `tax_slabs` | Tax Engine | Income brackets and statutory tax rates |
| 21 | `tax_rebates` | Tax Engine | Section 87A statutory rebate thresholds |
| 22 | `tax_exemptions` | Tax Engine | Statutory exemptions (HRA, LTA, standard deduction rules) |
| 23 | `tax_deductions` | Tax Engine | Chapter VI-A statutory deductions (80C, 80D, 80CCD) |
| 24 | `tax_surcharges` | Tax Engine | High-income surcharge tiers & marginal relief flags |
| 25 | `tax_cess_rules` | Tax Engine | Health and Education Cess rates |
| 26 | `tax_sources` | Tax Engine | Legal source citations, Finance Acts, CBDT circulars |
| 27 | `pf_rule_versions` | Provident Fund | Versioned EPFO statutory compliance rules |
| 28 | `pf_rules` | Provident Fund | Contribution rates (EPF, EPS, EDLI, Admin charges) |
| 29 | `pf_interest_rules` | Provident Fund | Annual statutory PF interest rates for projection |
| 30 | `professional_tax_rule_versions` | Professional Tax | Versioned State PT schedules |
| 31 | `professional_tax_slabs` | Professional Tax | Monthly salary brackets & February differential rates |
| 32 | `payslip_documents` | Payslip Pipeline | Uploaded document metadata, file paths, SHA-256 |
| 33 | `payslip_extractions` | Payslip Pipeline | Raw/normalized extracted data & OCR engine metadata |
| 34 | `payslip_validations` | Payslip Pipeline | Reconciliation status and discrepancy flags |
| 35 | `knowledge_sources` | Knowledge Repository | Provenance metadata: publication_date, effective_date |
| 36 | `knowledge_documents` | Knowledge Repository | Statutory acts, notifications, circulars, guides |
| 37 | `knowledge_chunks` | Knowledge Repository | Embedding-ready text chunks for future RAG |
| 38 | `chat_sessions` | Chat Assistant | User consultation and query sessions |
| 39 | `chat_messages` | Chat Assistant | Chat history, assistant responses, citations |
| 40 | `audit_logs` | Audit | System-wide immutable administrative audit trails |
