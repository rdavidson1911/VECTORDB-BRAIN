---
kb_status: curated
note_finalized: true
kb_ingest: true
summary: "Design notes on retrieval-augmented generation in VECTORDB-BRAIN: chunking, embedding with sentence-transformers, Qdrant vector storage, and cosine similarity retrieval."
kb_reviewed_at: "2026-07-01"
ai_assisted: false
---

# RAG Design Notes

Retrieval-augmented generation in OmniKB depends on:

1. chunking source documents
2. embedding chunks with sentence-transformers
3. storing vectors and metadata in Qdrant
4. querying similar vectors using cosine similarity
