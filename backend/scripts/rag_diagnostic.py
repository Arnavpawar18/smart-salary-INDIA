import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.engine.rag.retriever import FinancialRAGRetriever
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeSource

db = SessionLocal()
sources = db.query(KnowledgeSource).count()
docs = db.query(KnowledgeDocument).count()
chunks = db.query(KnowledgeChunk).count()
print(f"DB Knowledge Counts: Sources={sources}, Docs={docs}, Chunks={chunks}")

retriever = FinancialRAGRetriever(db)
queries = [
    "Section 87A rebate FY 2025-26",
    "EPF employee contribution 12 percent",
    "Karnataka professional tax salary",
    "What is SmartSalary?"
]
for q in queries:
    res = retriever.retrieve_evidence(q)
    print(f"\nQuery: '{q}' -> {len(res.chunks)} chunks")
    for c in res.chunks:
        print(f"  - [{c.authority}] {c.title} ({c.section_reference}): {c.content[:80]}...")
db.close()
