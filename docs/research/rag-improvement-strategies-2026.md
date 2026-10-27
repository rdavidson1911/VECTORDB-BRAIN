# RAG Improvement Strategies for OmniKB (2026)

**Status:** DRAFT  
**Date:** 2026-10-27  
**Owner:** Research (Cursor foundation pass)  
**Scope:** Map external retrieval research onto VECTORDB-BRAIN / OmniKB’s layered architecture — not a generic RAG checklist.

---

## Context

OmniKB’s differentiator is **layered knowledge** (L1 evidence → L2 episodic → L3 consistency graph + dreaming), documented in:

- `docs/vision-beyond-rag.md`
- `docs/layered-knowledge-architecture.md`
- `docs/implementation-roadmap-layered-architecture.md`
- ADR-0001 (L2 SQLite) and the consolidation / L2–L3 transfer research drafts under `docs/research/`

Layer 1 (dense MiniLM → Qdrant → `/query` → React) is live. Cleverer retrieval tricks only pay off if they plug into that model with provenance preserved.

---

## Strategy map

### 1. Dense prefetch → cross-encoder rerank

**External pattern:** Retrieve top-N with a bi-encoder; reorder with `cross-encoder/ms-marco-MiniLM-L-6-v2` (or similar).

**OmniKB fit:** Precision gain without changing embedding dims or reindexing L1. Already named in `docs/agents/L2_L3_AGENT.md` and the project charter risk mitigations.

**Near-term action:** Implement behind a settings flag after the thin-client UX foundation; benchmark latency at candidate sizes {10, 25, 50} on curated corpus. Prefer measuring rerank vs embedding-model swap before migrating off MiniLM-384 (`docs/agents/NAMING_DECISION.md`).

### 2. Hybrid dense + sparse / named vectors

**External pattern:** BM25/sparse + dense fusion (RRF or weighted) via Qdrant named vectors.

**OmniKB fit:** Recall for exact identifiers and rare tokens in personal notes. Tracked in `docs/research/qdrant-schema-scenarios.md`.

**Near-term action:** Continue experiments only on research Qdrant `:6334`. Do not alter production `:6333` schema without a Qdrant Agent migration + Orchestrator approval.

### 3. Neighbor / chunk-window expansion

**External pattern:** Expand hits to adjacent chunks for contiguous evidence.

**OmniKB fit:** `QueryRequest` already exposes `include_neighbors` and `neighbor_window`; route/service do not expand yet (`CLAUDE.md` roadmap note).

**Near-term action:** Wire expansion in the query service with payload indexes on `(source_path, chunk_index)`. Surface toggle in the web console once the API returns expanded hits.

### 4. ColBERT late interaction

**External pattern:** Token-level multivectors + MaxSim.

**OmniKB fit:** Optional pluggable strategy under reactive query — see `docs/architecture-colbert-multivector-proforma.md`. Does not replace L1 provenance or L3 relational memory.

**Near-term action:** Keep as research/proforma until dense+rerank and hybrid benches close. If adopted, log strategy id + scores into L2 session artifacts.

### 5. GraphRAG-style communities → L3 consistency graph

**External pattern:** Microsoft GraphRAG / community summaries over entity graphs.

**OmniKB fit:** Map to **L3 consistency edges + concept nodes**, not a parallel GraphRAG product. Prefer **HDBSCAN then graph-within-clusters** per `docs/agents/NAMING_DECISION.md` and `docs/research/l2-l3-transfer-protocol.md`.

**Near-term action:** Treat GraphRAG papers as optional mapping notes. Implement L3 only after L2 SQLite (ADR-0001) and a real consolidation worker exist.

### 6. HyDE / query rewrite as L2 artifacts

**External pattern:** Hypothetical document embeddings or LLM query rewrite before retrieval.

**OmniKB fit:** Do **not** index hypothetical text into L1 curated corpus. Store rewrites / hypotheses as **L2 session artifacts** so dreaming can accept, reject, or promote with provenance.

**Near-term action:** Spec artifact types (`query_rewrite`, `hyde_draft`) in the L2 schema draft; implement after session CRUD lands.

### 7. Dreaming / consolidation (differentiator)

**External pattern:** Offline reconciliation / memory consolidation (episodic → semantic).

**OmniKB fit:** Core roadmap Phases 2–3. Stub exists at `POST /consolidation/run`; episodic pipeline not wired.

**Near-term action:** Ship L2 persistence → real consolidation job with `score_model_version` + evidence refs → L3 edges. This is the product thesis; retrieval plugins feed it, they do not replace it.

---

## Orchestrator backlog (priority order)

1. **Cross-encoder rerank** (feature-flagged) on existing dense hits  
2. **Neighbor expansion** (`include_neighbors` / `neighbor_window`)  
3. **L2 session capture** (ADR-0001 SQLite CRUD + query/result logging)  
4. **Dreaming / consolidation worker** (replace stub)  
5. **L3 HDBSCAN concepts + consistency edges**  
6. Hybrid named vectors / ColBERT only after benches on `:6334` and ADRs graduate to DECISION  

Mobile thin-client (ADR-0002) does not change this order: clients remain API-only; retrieval improvements stay server-side.

---

## Explicit non-goals (this research pass)

- Swapping production embedding dims without the 6334 benchmark gate  
- Suggesting curation-gate bypass for “better RAG”  
- On-device inference or on-phone Qdrant for v1 thin-client  
- Treating GraphRAG/HyDE as drop-in replacements for L2/L3  

---

## References (in-repo)

| Document | Role |
|----------|------|
| `docs/vision-beyond-rag.md` | Product thesis vs naive RAG |
| `docs/implementation-roadmap-layered-architecture.md` | Phased delivery |
| `docs/decisions/0001-l2-store-schema.md` | L2 SQLite |
| `docs/decisions/0002-mobile-thin-client.md` | API-only clients |
| `docs/architecture-colbert-multivector-proforma.md` | Optional late interaction |
| `docs/research/embedding-model-comparison.md` | Model upgrade gate |
| `docs/research/consolidation-trigger-analysis.md` | Consolidation trigger ADR |
| `docs/research/l2-l3-transfer-protocol.md` | L3 clustering path |
