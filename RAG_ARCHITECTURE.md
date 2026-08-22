# SMART SALARY INDIA — REGULATORY RAG ARCHITECTURE

> **Purpose:** Provide verifiable, citation-backed natural language explanations for salary, tax, and deduction calculations based on official Indian government publications.

---

## 1. End-to-End Regulatory RAG Architecture

```
                                  REGULATORY RAG PIPELINE
                                             │
    ┌────────────────────────────────────────┴────────────────────────────────────────┐
    ▼                                                                                 ▼
[ INGESTION PIPELINE ]                                                     [ RETRIEVAL & SERVING ]
1. Official Sources (CBDT, EPFO, ESIC, States)                             1. User Query + User Calculation Context
2. Document Parsing (PyMuPDF, OCR for Gazettes)                            2. Context Filtering (FY, State, Tax Type)
3. Semantic & Structural Chunking (Sections, Clauses)                      3. Hybrid Retrieval:
4. Rich Statutory Metadata Attachment                                         - Dense Vector Search (cosine similarity)
5. Embedding Generation                                                       - Sparse BM25 Keyword Search
6. Vector Database Ingestion                                               4. Cross-Encoder Reranking
                                                                           5. Citation-Anchored Context Assembly
                                                                           6. LLM Generates Source-Cited Explanation
```

---

## 2. Chunking & Statutory Metadata Schema

Every indexed regulatory chunk is enriched with strict structured metadata:

```json
{
  "chunk_id": "chunk_incometax_sec115bac_p3",
  "document_id": "doc_finance_act_2025_gazette",
  "authority": "CBDT / Ministry of Finance",
  "tax_type": "INCOME_TAX",
  "jurisdiction": "CENTRAL",
  "state": null,
  "document_type": "ACT_AMENDMENT",
  "financial_year": "2025-26",
  "assessment_year": "2026-27",
  "section_reference": "Section 115BAC(1A)",
  "effective_from": "2025-04-01",
  "effective_until": "2026-03-31",
  "notification_number": "Finance Act 2025, Notification No. 12/2025",
  "source_url": "https://incometaxindia.gov.in/gazette/2025/finance_act_2025.pdf",
  "verified": true,
  "verified_at": "2025-04-01T08:00:00Z",
  "content": "Under sub-section (1A) of section 115BAC, for assessment year 2026-27, the standard deduction from salary income under clause (ia) of section 16 shall be seventy-five thousand rupees..."
}
```

---

## 3. Hybrid Retrieval & Dynamic Query Filtering

When a user asks:
> *"Why did you deduct ₹200 Professional Tax when I work in Bangalore?"*

The system performs:
1. **Metadata Filter Enforcement:**
   * `tax_type`: `PROFESSIONAL_TAX`
   * `state`: `Karnataka`
   * `effective_from <= current_date <= effective_until`
2. **Hybrid Search Scoring:**
   $$\text{Score} = 0.6 \times \text{DenseVectorScore} + 0.4 \times \text{BM25Score}$$
3. **Cross-Encoder Rerank:** Top 10 candidate chunks re-scored by relevance to user query and calculation trace.
4. **LLM Prompt Injection:**
   ```
   [SYSTEM]
   You are Smart Salary India Regulatory AI.
   Explain the calculation clearly based ONLY on the provided verified statutory source chunks.
   Always cite the Authority, Notification / Section, and Official Source URL.
   Do NOT compute new numbers. Use the numbers provided in the Calculation Context.
   ```
