# Layered Knowledge Architecture (Planned)

This document defines the planned multi-layer architecture for VectorDB-Brain so the system can evolve beyond a single vector index and support richer recursive relationships, consistency scoring, and drill-down retrieval.

Important: this is an architecture target. It includes planned capabilities that are not fully implemented yet.

For a **Graphviz** representation of this model alongside the current runtime, see [architecture-graphviz.md](architecture-graphviz.md).

## 1) Why Layering

Current architecture is primarily:

- raw documents -> ingest/chunk/embed -> Qdrant -> query API -> React UI.

Planned layering adds:

- a mutable interaction/cache plane,
- a background reconciliation plane ("dreaming"),
- a persistent relationship graph/score plane.

This supports explainability, recursive insight, and reusable data across multiple frontends.

## 2) Layer Definitions

## Layer 1: Raw Read-Only Source Layer

Purpose:

- canonical source documents (`.md`, `.txt`, `.pdf`) and baseline metadata.
- immutable reference corpus for provenance and repeatability.

Rules:

- read-only semantics in operations and deployment.
- no session writes back into raw corpus.

## Layer 2: Session and Cache Layer (Read/Write)

Purpose:

- temporary or intermediate artifacts from user sessions.
- derived notes, summaries, interaction metadata, and intermediate chunk relationships.

Rules:

- read/write during active workflows.
- after session closure, selected artifacts may be promoted to durable derived documents.
- promoted artifacts become read-only historical evidence, but remain separate from raw corpus category.

## Layer 3: Persistent Relationship and Consistency Layer

Purpose:

- graph-like many-to-many relationships across chunks/documents.
- consistency/inconsistency scores derived from Layer 1 + Layer 2 comparisons.
- aggregation layer for query-time insight and drill-down.

Rules:

- persisted independently from raw corpus files.
- versioned scoring logic and metadata fields for reproducibility.

## 3) Dreaming Process (Planned Background Job)

The dreaming process runs after user session completion.

Inputs:

- Layer 1 raw chunks + metadata.
- Layer 2 session/cache artifacts.
- existing relationship history (if present).

Tasks:

1. Compare chunk-level semantic and metadata consistency.
2. Create or update edges between related nodes.
3. Assign consistency metrics (for example, strongly consistent, mixed, inconsistent).
4. Persist scores and provenance references to Layer 3.

Outputs:

- edge records with score/version metadata,
- aggregated relationship summaries,
- trace links back to source chunks in Layer 1 and Layer 2.

## 4) Query and UI Behavior (Planned)

The React UI should provide:

- optional toggles for including Layer 3 results,
- drill-down from Layer 3 aggregate nodes to underlying Layer 1/Layer 2 chunks,
- subquery flow similar to pivot-table detail expansion.

The backend should support:

- layer-aware query flags,
- layer-specific filters,
- provenance payload fields needed for drill-down detail.

Note:

`src/omnikb/api/schemas.py` already includes `include_neighbors` and `neighbor_window` fields in `QueryRequest`, but current route/service logic does not yet provide full neighbor/layer traversal behavior.

## 5) Data Contract Considerations

For stable interoperability across future frontends (React, Streamlit, mobile, desktop):

- keep canonical IDs stable across layers,
- keep provenance fields explicit (`source_path`, chunk index, content hash, pipeline version),
- separate raw-data ownership from derived-data ownership,
- record scoring model/version for Layer 3 outputs.

## 6) Extensibility Goals

This layered model is intended to support future domain datasets (science, mathematics, physics, chemistry, psychology, finance, and more) while preserving:

- source integrity,
- explainability of derived knowledge,
- cross-interface API portability.

## 7) Delivery Phases (Planned)

1. Document contract and metadata schema.
2. Implement Layer 2 persistence model and lifecycle.
3. Implement dreaming job orchestration and score persistence.
4. Add layer-aware API query options.
5. Add UI toggles and drill-down detail views.
6. Add coverage and performance/security gates for layered paths.
