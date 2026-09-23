# ADR 0002: Interaction Boost and Idle Dreaming

**Status:** Accepted
**Date:** 2026-08-10
**Context:** Multi-layer memory phase (Layer 1–3, 1-based numbering)
**Related:** Does not replace [ADR 0001: L2 Session Store Schema](0001-l2-store-schema.md). Session artifacts (interpretations, export-for-consolidation) remain a separate concern; this ADR covers interaction boosts and relationship edges.

## Decision

1. Layer 1 (`omnikb_documents`) remains immutable provenance. Interaction counters and relationship edges live in a local SQLite store (`data/processed/interactions.db`) that references Layer 1 point IDs.
2. Human web-console retrievals emit `POST /interactions/events` (`query_impression`, `result_click`, `result_expand`). Aggregates update `chunk_boosts`.
3. Query fusion: `fused = (1 - w) * cosine + w * boost_norm` with `boost_norm = log1p(hit_count) / log1p(hit_count_max)` and default `w = 0.25` (`INTERACTION_BOOST_WEIGHT`).
4. `QueryResponse` returns `matches` (= Layer 1 cosine, backward compatible), `layer1_matches`, `layer2_boosted_matches`, and optional `layer3_relations` when `include_layer3=true`.
5. Idle dreaming extends `POST /consolidation/run`: when no interaction events in `DREAMING_IDLE_MINUTES` (default 30), or on explicit run, build pairwise cosine edges among recently boosted chunks above `DREAMING_EDGE_MIN_SCORE` (default 0.72).

## Deferred (not this change)

BM25 lexical score and query-term coverage (explored in draft PR #11 `/query/enhanced`) may be added later as **additional fusion signals** inside the interaction boost path. They must not introduce a second SQLite L2 store or a parallel query API in this phase.

## Consequences

- React UI shows Layer 1 and Layer 2 result sections separately.
- HDBSCAN concept nodes remain Phase 2.
- Samples (`memory_tier=samples`) never receive boost promotions (see ADR 0003).
