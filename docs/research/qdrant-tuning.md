# Qdrant Tuning Report — VECTORDB-BRAIN

**Status:** DRAFT — lab rows PLANNED until research Qdrant (port 6334) runs
**Author:** QDRANT AGENT
**Date:** 2026-06-04
**Collection under test:** `learning_lab` on port **6334**
**Embedding dim:** 384 (`all-MiniLM-L6-v2`)

---

## 1. Standard results table (required format)

All experiments use query-time `ef` ∈ {128, 256} unless noted. Fill measured cells after `20260602_hnsw_quantization_lab.py` (6334 only).

| experiment | m | ef_construct | quantization | recall@10 | p50_ms | p95_ms | storage_mb |
|------------|---|--------------|--------------|-----------|--------|--------|------------|
| PLANNED_baseline_m16_ef128_none | 16 | 128 | none | PLANNED | PLANNED | PLANNED | PLANNED |
| PLANNED_scalar_m16_ef128_int8 | 16 | 128 | scalar_int8 | PLANNED | PLANNED | PLANNED | PLANNED |
| PLANNED_pq_m16_ef128_product | 16 | 128 | product | PLANNED | PLANNED | PLANNED | PLANNED |

---

## 2. Experimental design

### 2.1 Objective

Determine optimal `(m, ef_construct)` and quantization for:

- Production-shaped **`omnikb_documents`** (L1)
- Proposed **`omnikb_episodes`** (L2)

### 2.2 Collection under test

- **`learning_lab`** on `http://localhost:6334` (research sidecar; never port 6333 in experiment code).
- Dataset: synthetic 384-dim vectors (default 10k points); ground-truth top-10 via offline brute force.

### 2.3 Metrics

- **recall@10**, **p50_ms**, **p95_ms** (500 queries), **storage_mb**, **index_build_time_s** (see §4)

### 2.4 ef at query time

Each configuration measured at **ef=128** and **ef=256**.

---

## 3. HNSW parameter grid (full factorial — pending lab)

| Parameter | Values |
|-----------|--------|
| `m` | 8, 16, 32 |
| `ef_construct` | 64, 128, 200 |
| Quantization | none, scalar_int8, product |

27 configs × 2 ef levels → 54 rows in the detailed grid (section 3.1 of prior draft). Use the three **PLANNED** rows above for executive summary until the lab completes.

### 3.1 Detailed results table (PENDING)

| experiment | m | ef_construct | quantization | recall@10 | p50_ms | p95_ms | storage_mb |
|------------|---|--------------|--------------|-----------|--------|--------|------------|
| *(run lab script to populate)* | | | | | | | |

---

## 4. HNSW build time table (PENDING)

| m | ef_construct | quantization | index_build_time_s | memory_mb |
|---|--------------|--------------|-------------------|-----------|
| PLANNED | PLANNED | PLANNED | PLANNED | PLANNED |

---

## 5. Payload index optimization (L1)

Filtered fields derived from `src/omnikb/adapters/qdrant_store.py` and `ingestion_service.py`:

| Field | Index type | Rationale |
|-------|------------|-----------|
| `source_path` | keyword | delete, skip_unchanged, search |
| `indexed_at_ts` | float | date range search |
| `file_type`, `document_id`, `content_hash` | keyword | search / skip_unchanged |
| `chunk_strategy`, `embedding_model`, `pipeline_version`, `normalization_profile` | keyword | skip_unchanged |
| `chunk_size`, `chunk_overlap` | integer | skip_unchanged |

---

## 6. L3 graph substrate (prototype notes)

- Payload: `linked_chunks: list[str]` (point IDs).
- Traversal: client-side BFS with batched `retrieve`; target &lt;100 ms for 2-hop at ~100k points with low fan-out (see Qdrant Agent workstream 5).

---

## 7. Preliminary recommendations (pre-lab)

| Collection | m | ef_construct | Quantization |
|------------|---|--------------|--------------|
| `omnikb_documents` (L1) | 16 | 128 | scalar int8 after validation |
| `omnikb_episodes` (L2) | 16 | 128 | same |

**Escalate to Orchestrator** if recall@10 at `m=32, ef_construct=200` beats `16/128` by &gt;5% or if Research changes embedding dimension.

---

## 8. Next steps

1. `make research-qdrant-up` (or devcontainer `qdrant-research` service).
2. `QDRANT_URL=http://localhost:6334 python scripts/migrations/20260602_hnsw_quantization_lab.py`
3. Replace **PLANNED** cells in §1 and §3.
4. Open production migration only after Orchestrator review (indices / HNSW — not via 6334 experiments touching prod).
