# Implementation Roadmap: Layered Architecture

This roadmap operationalizes the planned layered model in `docs/layered-knowledge-architecture.md` into phased delivery milestones, draft API contracts, and test acceptance criteria.

Important: this is an implementation plan document. It describes target behavior and does not imply all capabilities are currently implemented.

Visual architecture (Graphviz DOT): [architecture-graphviz.md](architecture-graphviz.md).

## 1) Objectives

- Preserve Layer 1 raw corpus immutability and provenance.
- Add Layer 2 session/cache artifacts without contaminating raw source category.
- Add Layer 3 persistent relationship and consistency graph outputs.
- Expose layer-aware query behavior with explainable drill-down in UI.
- Maintain performance, security, and test quality gates through each phase.

## 2) Layer Boundaries (Contract Baseline)

## Layer 1 (Current + Protected)

- Source documents (`.md`, `.txt`, `.pdf`) remain canonical and read-only.
- Existing ingest and query continue to function as baseline.
- Provenance fields remain mandatory (`source_path`, `chunk_index`, `content_hash`, pipeline metadata).

## Layer 2 (New)

- Session-scoped read/write artifacts (notes, cached interpretations, user-generated summaries, temporary links).
- Promotion path to durable derived documents after session close.
- Durable derived docs are read-only artifacts, but separate from raw corpus category.

## Layer 3 (New)

- Persistent edges and scores produced by background "dreaming" process.
- Aggregation layer for consistency/inconsistency relationships.
- Query-time expansion and drill-down to Layer 1/Layer 2 evidence.

## 3) Phased Milestones

## Phase 0: Readiness and Guardrails

Goals:

- Freeze baseline behavior and establish migration-safe contracts.
- Define IDs and metadata requirements for all future layers.

Deliverables:

- data contract draft (IDs, fields, versions),
- migration strategy and fallback plan,
- initial test matrix updates.

Exit criteria:

- no regression in existing ingest/query flows,
- roadmap and contract reviewed and approved.

## Phase 1: Layer 2 Session/Cache Persistence

Goals:

- Introduce session artifact storage and lifecycle.
- Keep Layer 1 raw corpus untouched.

Deliverables:

- Layer 2 persistence schema (session_id, artifact_id, source references, timestamps),
- CRUD/service endpoints for session artifact operations,
- retention and promotion policy.

Exit criteria:

- session artifacts can be created/read/updated/deleted,
- promoted artifacts become immutable derived records,
- raw corpus remains unchanged by Layer 2 operations.

## Phase 2: Dreaming Orchestration

Goals:

- Trigger background reconciliation at session end.
- Compare Layer 1 chunks with Layer 2 artifacts.

Deliverables:

- background job contract and state machine,
- scoring algorithm versioning model,
- reproducible processing logs and run metadata.

Exit criteria:

- dreaming jobs run reliably with traceable outputs,
- failures are recoverable and auditable,
- scoring outputs are persisted with provenance.

## Phase 3: Layer 3 Relationship Store

Goals:

- Persist graph-like many-to-many edges and consistency scores.
- Support relationship aggregation and traversal metadata.

Deliverables:

- Layer 3 edge schema and indexes,
- aggregate node/materialization strategy,
- read APIs for relationship and score retrieval.

Exit criteria:

- consistent queryable relationship store,
- edge records include score/version/provenance fields,
- aggregate-to-detail traversal is supported in API responses.

## Phase 4: Layer-Aware Query API

Goals:

- Extend query endpoint contracts for layer inclusion and drill-down.
- Keep backward compatibility with existing clients.

Deliverables:

- query request flags for layer selection and drill-down depth,
- response payload with `layer_hits`, `aggregate_nodes`, and `evidence_refs`,
- neighbor/layer traversal implementation aligned to contract.

Exit criteria:

- current clients continue working with default behavior,
- new clients can opt into Layer 2/Layer 3 expansions,
- drill-down references resolve to concrete underlying chunks.

## Phase 5: React Drill-Down UX

Goals:

- Add toggles and pivot-like drill-down experience in web UI.

Deliverables:

- layer selection controls,
- aggregate result cards with expandable detail,
- subquery workflow into Layer 1 and Layer 2 supporting evidence.

Exit criteria:

- users can toggle layer inclusion,
- users can drill from aggregate to evidence details,
- UX remains stable under large result sets.

## Phase 6: Hardening and Scale

Goals:

- production-grade reliability, performance, and security for layered flows.

Deliverables:

- performance benchmarks for dreaming/query expansion,
- security policy gates for layer data handling,
- operational runbooks and SLO tracking.

Exit criteria:

- quality and security gates pass consistently,
- no severe regressions versus baseline latency and stability,
- documented incident response for layered components.

## 4) Draft API Contracts

The following are draft contracts for planning and review.

## 4.1 Session Artifact APIs (Layer 2)

### POST `/sessions/{session_id}/artifacts`

Request:

```json
{
  "artifact_type": "note",
  "text": "User insight about chunk consistency",
  "source_refs": [
    {
      "source_path": "/data/sources/doc-a.md",
      "chunk_index": 12,
      "content_hash": "abc123..."
    }
  ],
  "metadata": {
    "author_role": "user",
    "tags": ["analysis", "consistency"]
  }
}
```

Response:

```json
{
  "artifact_id": "art_01J...",
  "session_id": "sess_01J...",
  "status": "active",
  "created_at": "2026-05-05T04:00:00Z"
}
```

### POST `/sessions/{session_id}/finalize`

Purpose:

- closes session,
- triggers dreaming process,
- locks/promotes configured artifacts.

## 4.2 Dreaming Job APIs

### POST `/dreaming/jobs`

Request:

```json
{
  "session_id": "sess_01J...",
  "mode": "consistency_reconcile_v1",
  "priority": "normal"
}
```

Response:

```json
{
  "job_id": "dream_01J...",
  "status": "queued",
  "submitted_at": "2026-05-05T04:01:00Z"
}
```

### GET `/dreaming/jobs/{job_id}`

Response:

```json
{
  "job_id": "dream_01J...",
  "status": "completed",
  "score_model_version": "consistency_v1",
  "outputs": {
    "edges_created": 132,
    "edges_updated": 29
  }
}
```

## 4.3 Layer-Aware Query API Draft

### POST `/query` (extended)

Draft request extension:

```json
{
  "query": "Find stable definitions of term X",
  "limit": 10,
  "include_layer2": false,
  "include_layer3": true,
  "drilldown": {
    "enabled": true,
    "max_depth": 2,
    "include_evidence_refs": true
  }
}
```

Draft response extension:

```json
{
  "matches": [],
  "analytics": {
    "latency_ms": 18.2,
    "returned_count": 10,
    "unique_sources": 7,
    "top_score": 0.87,
    "average_score": 0.66
  },
  "layer_hits": {
    "layer1": 6,
    "layer2": 0,
    "layer3": 4
  },
  "aggregate_nodes": [
    {
      "aggregate_id": "agg_01J...",
      "consistency_score": 0.91,
      "evidence_refs": [
        {
          "layer": "layer1",
          "source_path": "/data/sources/doc-a.md",
          "chunk_index": 8
        },
        {
          "layer": "layer2",
          "artifact_id": "art_01J..."
        }
      ]
    }
  ]
}
```

## 5) Phase-by-Phase Test Acceptance Criteria

## Phase 0

- all existing tests pass unchanged,
- smoke passes on baseline commands,
- documentation clearly marks planned vs implemented behavior.

## Phase 1

- unit tests for artifact lifecycle and validation,
- API tests for session artifact CRUD and error mapping,
- integration tests proving Layer 1 immutability during Layer 2 operations.

## Phase 2

- unit tests for dreaming trigger logic and job state transitions,
- integration tests for recoverable retries and idempotent job handling,
- evidence logs include job_id and source provenance.

## Phase 3

- schema tests for edge payload validity and version fields,
- integration tests for edge write/read and traversal accuracy,
- regression tests for duplicate edge suppression rules.

## Phase 4

- API contract tests for backward compatibility with legacy `/query` request,
- tests for layer flags and drill-down depth handling,
- tests for evidence reference integrity to Layer 1/Layer 2 entities.

## Phase 5

- UI tests for layer toggles and aggregate expansion behavior,
- E2E tests validating drill-down from Layer 3 aggregate to evidence details,
- performance checks for large result rendering.

## Phase 6

- benchmark comparisons meet defined latency/throughput guardrails,
- security checks pass for new endpoints/data flows,
- incident runbook drills completed and documented.

## 6) Quality Gates Per Phase

Every implementation phase should meet:

- `ruff` clean,
- `mypy` clean for touched backend scope,
- `bandit` clean (or explicit documented waiver),
- `pytest` pass for impacted areas,
- smoke/E2E evidence for user-facing changes.

## 7) Risks and Mitigations

- Contract drift between API and UI.
  - Mitigation: versioned API schemas and contract tests.
- Layer coupling causing raw corpus mutation.
  - Mitigation: explicit write-path guardrails and tests.
- Dreaming job cost or latency spikes.
  - Mitigation: queue controls, batching, and benchmark gates.
- Explainability gaps in aggregate scoring.
  - Mitigation: mandatory provenance and evidence references in Layer 3 outputs.

## 8) Suggested Delivery Cadence

- Sprint 1: Phase 0 + Phase 1
- Sprint 2: Phase 2
- Sprint 3: Phase 3
- Sprint 4: Phase 4 + Phase 5
- Sprint 5: Phase 6 hardening and readiness review

This cadence is adjustable based on observed complexity and quality gate outcomes.
