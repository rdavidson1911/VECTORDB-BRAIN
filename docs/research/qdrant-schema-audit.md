# Qdrant Schema Audit — VECTORDB-BRAIN

**Status:** DRAFT
**Author:** QDRANT AGENT
**Date:** 2026-06-04
**Branch:** `agent/qdrant-schema-v2`
**Reviewed by:** PENDING — Orchestrator

---

## 1. Scope

This audit covers:

- Production Layer 1 collection used by OmniKB (`omnikb_documents`, settings default)
- All collections present under `data/qdrant/collections/` on the host volume
- Gaps versus the **L2 Episodic Store** spec in `AGENT_ORCHESTRATION_PLAN.md` §1 / §2.4
- Proposed payload indices and L2 collection shape (migrations as stubs only)

Research-only collections (`learning_lab`, `research_lab`) are **not** on the production volume; they are created on port **6334** by benchmark/tuning scripts.

---

## 2. Collections on disk (`data/qdrant/collections/`)

Snapshot taken 2026-06-04 from local Qdrant storage (Docker bind mount). These coexist with the single collection referenced in `src/omnikb/`.

| Collection | Vector config | HNSW (m / ef_construct) | Sparse | OmniKB code reference |
|------------|---------------|-------------------------|--------|------------------------|
| `omnikb_documents` | 384, Cosine | 16 / 100 | — | **Yes** — `settings.qdrant_collection` default |
| `qdrant-website-docs-snapshot` | 384, Cosine | 16 / 100 | — | No |
| `switchy` | 384, Cosine | 16 / 100 | — | No |
| `midjourneydata` | 512, Cosine | 16 / 100 | — | No (dim mismatch vs current embedder) |
| `central_library` | 4, Dot | 16 / 100 | — | No; payload index artifacts include `group_id` on disk |
| `star_charts` | 4, Dot | 16 / 100 | — | No |
| `terraforming` | 4, Dot | 16 / 100 | — | No |
| `multivector_collection` | 4, Dot + multivector max_sim | 16 / 100 | — | No |
| `terraforming_plans` | 4, Cosine + named sparse `keywords` | 16 / 100 | hybrid | No |
| `sparse_charts` | sparse-only (`keywords`) | 16 / 100 | yes | No |

**Implication:** Only `omnikb_documents` is governed by `QdrantStore` / ingest today. Other collections are legacy or experimental data on the same Qdrant process; L2 work must not assume they share payload schema or dimensionality.

---

## 3. Current L1 collection: `omnikb_documents` (code + on-disk)

### 3.1 Vector configuration

| Parameter | On-disk (`config.json`) | Created by code | Notes |
|-----------|-------------------------|-----------------|-------|
| Vector size | 384 | `ensure_collection(vector_size)` | `all-MiniLM-L6-v2` |
| Distance | Cosine | `Distance.COSINE` | |
| HNSW m | 16 | Qdrant default when collection created via client | Not set in `ensure_collection` |
| HNSW ef_construct | 100 | Qdrant default | Tuning doc targets 128 after lab |
| Quantization | null | None | |
| Named / sparse vectors | None | None | Hybrid search is future Research scope |

**Source:** `data/qdrant/collections/omnikb_documents/config.json`, `src/omnikb/adapters/qdrant_store.py` (`ensure_collection`).

### 3.2 Payload schema (per chunk point)

| Field | Filter usage | Payload index on disk |
|-------|--------------|------------------------|
| `document_id` | search, skip_unchanged | **No** |
| `chunk_index` | display | — |
| `source_path` | delete, skip_unchanged, search | **No** |
| `file_type` | search | **No** |
| `content_hash` | skip_unchanged, search | **No** |
| `source_size_bytes` | — | — |
| `content_preview`, `text` | display / client filter | — |
| `updated_at`, `indexed_at` | display | — |
| `updated_at_ts` | future range | **No** |
| `indexed_at_ts` | search date range | **No** |
| `chunk_strategy`, `chunk_size`, `chunk_overlap` | skip_unchanged | **No** |
| `embedding_model`, `pipeline_version`, `normalization_profile` | skip_unchanged | **No** |

**Sources:** `src/omnikb/services/ingestion_service.py` (payload build), `src/omnikb/adapters/qdrant_store.py` (filters).

### 3.3 Impact of missing indices

`skip_unchanged` calls `count_points` with up to eight keyword/integer conditions plus pipeline fields — full payload scan per check. `delete_by_source_path` and filtered `search` have the same cost profile. Acceptable at small scale; degrades past ~50k points.

**Migration priority:** HIGH — `source_path`, `indexed_at_ts`; MEDIUM — remaining keyword fields used in filters.

---

## 4. L2 episodic store — gap analysis (`AGENT_ORCHESTRATION_PLAN.md`)

North star: **L2 — Episodic Store** = Qdrant collections with **structured metadata**, **consolidation-gated** (not raw open ingest). Layer 1 remains the curated corpus index (`omnikb_documents`).

| L2 requirement (plan) | Current state | Gap |
|----------------------|---------------|-----|
| Consolidation-gated writes | Ingest gate is filesystem (`curated/` + frontmatter); vectors written on ingest | No `consolidation_event_id` / episode lifecycle in Qdrant |
| Structured episodic metadata | Rich L1 chunk payload | No `episode_id`, `session_id`, `episode_type` |
| Separate collection or named vectors | Single L1 collection | No `omnikb_episodes` (or equivalent) |
| L3 graph substrate | — | No `linked_chunks` on points; `include_neighbors` in API schema unused |

Aligned with `docs/research/l2-layer-schema-draft.md`: L2 implementation remains **blocked** on consolidation-trigger ADR; vector size remains **blocked** on embedding-model decision.

### 4.1 Proposed `omnikb_episodes` collection (target)

```
Collection: omnikb_episodes
Vector size: 384 (until embedding ADR — same blocker as L2/L3 draft)
Distance: COSINE
HNSW: m=16, ef_construct=128 (post-tuning)
Quantization: scalar int8 (post-tuning, research port 6334 only)
```

### 4.2 Proposed L2 payload fields

| Field | Type | Purpose | Index |
|-------|------|---------|-------|
| `episode_id` | keyword | Stable episode UUID | keyword |
| `layer` | keyword | `"l2"` | keyword |
| `episode_type` | keyword | `raw_chunk` / `summary` / `concept` | keyword |
| `session_id` | keyword | Session or ingest batch | keyword |
| `consolidation_event_id` | keyword | Consolidation run | keyword |
| `consolidation_at_ts` | float | When consolidated | float |
| `source_chunk_ids` | list[str] | L1 point IDs | — |
| `source_paths` | list[str] | Provenance | keyword (multi) |
| `text`, `content_preview` | text | Retrieval body | — |
| `embedding_model`, `pipeline_version` | keyword | Reproducibility | keyword |
| `linked_chunks` | list[str] | L3 prototype edges | — |

### 4.3 Research collections (port 6334 only)

| Name | Owner | Purpose | On production volume? |
|------|-------|---------|------------------------|
| `learning_lab` | Qdrant Agent | HNSW / quantization grid | No |
| `research_lab` | Research Agent | Embedding model bench (`embedding_eval.py`) | No |

---

## 5. Recommended L1 payload indices (production migration)

See comment-only template `scripts/migrations/20260604_payload_index_readme.py` and (when approved) executable migration under `scripts/migrations/`.

Priority: `source_path`, `indexed_at_ts`, `file_type`, `document_id`, `content_hash`, then skip_unchanged keyword fields.

---

## 6. Schema migration plan

| Artifact | Target | Purpose |
|----------|--------|---------|
| `20260604_payload_index_readme.py` | doc / stub | Idempotent index checklist (no auto-run) |
| `20260602_add_payload_indices.py` | production (orchestrator-reviewed) | Apply L1 indices |
| `20260602_l2_episodic_store.py` | production | Create `omnikb_episodes` — blocked on ADRs |
| `20260602_hnsw_quantization_lab.py` | **6334 only** | Populate `docs/research/qdrant-tuning.md` |

---

## 7. Summary of findings

| Finding | Severity | Action |
|---------|----------|--------|
| Ten collections on disk; only `omnikb_documents` wired in code | INFO | Do not migrate unrelated collections; document ownership |
| No payload indices on L1 filter fields | HIGH | Payload index migration after review |
| `ensure_collection` minimal VectorParams | MEDIUM | Tune on 6334; then ADR + production migration |
| No L2 episodic collection | PLANNED | After consolidation + embedding decisions |
| `learning_lab` / `research_lab` absent on prod volume | EXPECTED | Use `make research-qdrant-up` for experiments |
