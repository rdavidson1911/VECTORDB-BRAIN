# L2 Layer Schema Draft (L2/L3 Agent)

**Status:** DRAFT — implementation blocked until Research ADRs reach DECISION.

This document is a **design placeholder** only. It does not authorize changes under `src/omnikb/` until `docs/research/consolidation-trigger-analysis.md` contains an approved **DECISION** section (and related research outputs are available as noted below).

---

## Dependencies (gate before code)

| Prerequisite | Path | Required for |
|--------------|------|----------------|
| Consolidation trigger ADR | `docs/research/consolidation-trigger-analysis.md` (**DECISION**) | `omnikb/consolidation/trigger.py`, scheduling, thresholds |
| Embedding model choice | `docs/research/embedding-model-comparison.md` | Ingest + consolidation embedding consistency |
| Qdrant tuning | `docs/research/qdrant-tuning.md` | Ingest `m`, `ef_construct`, collection params |

Until the consolidation-trigger ADR exists, workstream **L2 consolidation trigger** remains **BLOCKED**. Workstream **three-zone ingest gate** can be specified here but should align with existing curation docs and `validate_corpus` / API gate behavior already documented for `curated/`.

---

## Three-zone ingest gate (design sketch)

Zones under `data/sources/` (never mix):

| Zone | Path | Routine ingest | Gate |
|------|------|----------------|------|
| Samples | `_samples/` | Smoke/fixtures only | Exempt from production hard gate |
| Staging | `staging/` | No | Pre-validation; Obsidian export target |
| Curated | `curated/` | **Yes** | Template 2.0.0 hard gate |

**Promotion flow (intended L2 package: `omnikb/ingest/staging.py`):**

1. Files land in `staging/` after vault export.
2. Operator runs corpus validation (`validate_corpus` / `POST /curation/validate`) against staging or pre-promotion paths.
3. On zero ERROR codes, promote copy/move into `curated/`.
4. Routine ingest (`POST /ingest/path`, etc.) indexes **only** from `curated/`.

**Gate conditions (errors — block ingest on `main`):**

- `kb_ingest: true`
- `note_finalized: true`
- `kb_status: "curated"`
- If `ai_assisted: true` then `ai_summary_verified: true`

**Integration points:**

- Tie promotion to `omnikb/curation/validate.py` (or equivalent validator module): promotion fails if any ERROR code is returned.
- Override policy: `allow_quality_override` in request **and** `CURATION_ALLOW_OVERRIDE=true` env — neither alone; not for committed `main` defaults.

**Tests (acceptance when implemented):** full pytest coverage for promotion success/failure paths; denylist and secret-scan behavior unchanged from data quality charter.

---

## L2 consolidation trigger (placeholder)

**Blocked on:** `consolidation-trigger-analysis.md` → **DECISION** (mechanism: APScheduler vs FastAPI `BackgroundTasks` vs explicit API endpoint vs external worker).

**Intended module:** `omnikb/consolidation/trigger.py`

**Config (draft keys — names subject to ADR):**

- Thresholds and intervals in `omnikb/config.py` with env overrides (e.g. min new chunks, idle window, max runs per day).
- Must be unit-testable **without** a live Qdrant (mock vector store client).

**Downstream consumers (same L2 pass, later):**

- `omnikb/manifest/updater.py` — refresh `corpus-manifest-latest.json` after consolidation (flat JSON for PowerQuery).
- `omnikb/retrieval/reranker.py` — cross-encoder rerank (model per Research ADR).
- `omnikb/consolidation/concept_extractor.py` — L3 prototype (clustering choice per Research ADR).

---

## L3 prototype scope (minimal, post-L2 trigger)

- Single collection type (notes), single manual run, no scheduler.
- Input: curated chunk embeddings from Qdrant.
- Pipeline sketch: cluster → label → concept node → back-links to source chunks.
- Clustering algorithm (e.g. HDBSCAN) **not** fixed in this draft — follow Research ADR when published.

---

## Workstream order (when unblocked)

1. Three-zone ingest gate (`feat(l2):` staging promotion + tests)
2. L2 consolidation trigger (after consolidation-trigger **DECISION**)
3. Cross-encoder reranker
4. L3 concept extraction prototype
5. Corpus manifest automation

---

## References

- `docs/agents/L2_L3_AGENT.md` — agent workstreams and PR rules
- `docs/ingestion-and-curation-architecture.md` — gate fields and flows
- `CLAUDE.md` §4 — data quality charter (zones, gate, secrets)
- `docs/research/README.md` — research file lifecycle (PENDING → DRAFT → DECISION)
