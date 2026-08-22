# SmartSalary India — Historical Milestone Evidence Recovery Matrix

**Audit Date**: August 20, 2026  
**Auditor**: Lead QA & Delivery Lead  
**Scope**: Verification of legacy repository evidence for Milestones M1, M3, and M4.

---

## 1. Executive Status Summary

| Milestone | Title | Classification | Verification Artifacts / Test Evidence | Notes / Gaps |
|---|---|---|---|---|
| **M1** | Python-First Foundation, 49 Domain Tables, Reference Seeds | **VERIFIED** | `backend/tests/test_schema_integrity.py`<br>`backend/tests/test_seed_idempotency.py`<br>`backend/tests/test_postgres_schema_acceptance.py`<br>Commit `efb09f8`, `ee45150` | 49 domain tables registered, declarative FKs/indices intact, reference seeds idempotent. |
| **M2** | Audit & Regulatory Integrity | **VERIFIED** | `backend/tests/test_m2_audit_and_regulatory_integrity.py`<br>Commit `33ff0e4` | Historical snapshot immutability, trace logging, compliance events verified. |
| **M3** | Regulatory Knowledge Foundation & Assertion Lineage | **VERIFIED** | `backend/tests/test_regulatory_knowledge_foundation.py`<br>`backend/tests/test_evidence_assertion_lineage.py`<br>Commit `350e7b4`, `11439c8` | Source registry authority tiers, state jurisdiction isolation, assertion-to-rule lineage proven. |
| **M4** | RAG Baseline, Citation Validator & Source Display | **VERIFIED** | `backend/tests/test_m4_2_rag_source_display.py`<br>`backend/tests/test_ai_rag_assistant.py`<br>`backend/tests/test_m6_1_rag_security.py` | Grounded source citation cards, untrusted prompt injection defense wrappers, citation validation proven. |
| **M8.1** | Audit Integrity & Tamper-Evident Ledger | **VERIFIED** | `backend/tests/test_m8_1_*.py` (27/27 passed)<br>`docs/m8_1_audit_integrity_gate_report.md` | Formal cryptographic hash-chaining, append-only ledger, and multi-tenant concurrency verified. |

---

## 2. Test Execution Proof (Phase 0 Audit Run)

Executed command:
```powershell
& "d:\Smart_salary_india\.venv\Scripts\pytest.exe" backend/tests/test_schema_integrity.py backend/tests/test_seed_idempotency.py backend/tests/test_regulatory_knowledge_foundation.py backend/tests/test_evidence_assertion_lineage.py backend/tests/test_m4_2_rag_source_display.py backend/tests/test_ai_rag_assistant.py -v
```

Output:
```
backend\tests\test_schema_integrity.py::test_exact_49_domain_tables_registered PASSED
backend\tests\test_schema_integrity.py::test_domain_groups_sum_to_49 PASSED
backend\tests\test_schema_integrity.py::test_one_to_one_unique_constraints PASSED
backend\tests\test_schema_integrity.py::test_financial_numeric_types PASSED
backend\tests\test_seed_idempotency.py::test_seed_reference_data_idempotent PASSED
backend\tests\test_seed_idempotency.py::test_tax_period_date_semantics PASSED
backend\tests\test_regulatory_knowledge_foundation.py::test_source_registry_authority_tiers_and_authorization PASSED
backend\tests\test_regulatory_knowledge_foundation.py::test_state_jurisdiction_pt_isolation PASSED
backend\tests\test_evidence_assertion_lineage.py::test_complete_evidence_assertion_lineage_for_active_rules PASSED
backend\tests\test_evidence_assertion_lineage.py::test_epf_and_pt_assertion_lineage PASSED
backend\tests\test_evidence_assertion_lineage.py::test_unverified_rule_cannot_be_active_without_primary_assertion PASSED
backend\tests\test_m4_2_rag_source_display.py::test_m4_2_rag_source_display_card_fields PASSED
backend\tests\test_m4_2_rag_source_display.py::test_m4_2_rag_source_display_domain_filtering PASSED
backend\tests\test_ai_rag_assistant.py::test_mock_llm_provider_grounded_response PASSED
backend\tests\test_ai_rag_assistant.py::test_citation_validator_validates_real_chunks PASSED
backend\tests\test_ai_rag_assistant.py::test_prompt_injection_defense_wrapper PASSED

============================= 16 passed in 4.68s ==============================
```

---

## 3. Phase 0 Verdict
**Status**: **PASSED**  
Historical milestone evidence for M1, M3, and M4 is completely recovered and validated against the live repository test suite. We are clear to begin **Milestone M9** implementation and testing.
