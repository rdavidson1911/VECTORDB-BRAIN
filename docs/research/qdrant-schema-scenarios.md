# Qdrant Collection Schema Scenarios

**Status:** DRAFT
**Owner:** Research Agent
**Qdrant:** port **6334**, collection prefix `research_lab`

## Hypothesis

For OmniKB document collections, a **dense-only cosine** schema (current production shape) is sufficient at small scale; **sparse+dense hybrid** or **named vectors** help only when lexical mismatch (code symbols, rare tokens) dominates failure cases.

## Method

| Scenario | Schema | When to use |
|----------|--------|-------------|
| **S1 Dense-only** | Single vector, COSINE, dim = embedding model | Notes, prose, general RAG (current `QdrantStore.ensure_collection`) |
| **S2 Sparse + dense hybrid** | Dense embedding + sparse BM25/SPLADE vector | Keyword-heavy queries, SKU/code tokens |
| **S3 Named vectors** | e.g. `dense`, `sparse`, `code` representations | Multi-modal or multi-encoder per point |

**Measurement plan (Qdrant Agent + Research joint):**

1. Index same chunk set three ways on **6334** (`learning_lab` per Qdrant Agent charter).
2. Record **storage MB/point**, **recall@10** (same query set as embedding benchmark), **p95 query latency**.
3. Tune `ef`, `m`, `ef_construct` only after schema choice (see `qdrant-tuning.md` — Qdrant Agent).

**S1 baseline (executable today):** matches production adapter — no code change in `omnikb/` for research; use `embedding_eval` collections as dense-only reference.

## Results

| Model / Strategy | Storage / point | recall@10 | p95 latency (ms) | Score | Notes |
|------------------|-----------------|-----------|------------------|-------|-------|
| S1 Dense-only | Lowest | Baseline | Lowest | TBD | **Implemented** in research harness |
| S2 Hybrid | ~1.3–2× | TBD | TBD | TBD | Requires sparse vector config in Qdrant 1.7+ |
| S3 Named vectors | Highest | TBD | TBD | TBD | Operational complexity |

*Populate numeric cells after Qdrant Agent runs hybrid indexing on `learning_lab`.*

## Recommendation

| Collection type | Recommended schema | Rationale |
|-----------------|-------------------|-----------|
| **Curated notes / docs** | **S1 Dense-only** | Matches sentence-transformer pipeline; simplest ops |
| **Code snippets** | **S2 or S3** (pilot) | Lexical mismatch; evaluate with Qdrant Agent |
| **L3 concept nodes** | **S1** + rich payload (`source_chunk_ids`, `concept_label`) | Graph in payload, not extra vector |

**Per collection naming:** keep production `omnikb_documents` dense-only until hybrid pilot proves **≥10% recall@10 gain** at **< 2×** storage.

## Open Questions

- Quantization (int8) impact on recall — Qdrant Agent workstream 2.
- Whether WordNet/structured lexicon data needs a **separate collection** vs payload tags on prose chunks.
