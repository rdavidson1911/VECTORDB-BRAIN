# ADR-0001: L2 Session Store Schema

**Status:** ACCEPTED
**Date:** 2026-07-01
**Accepted:** 2026-07-01 (Operator)
**Deciders:** Orchestrator, Operator
**Supersedes:** —

---

## Context

Layer 1 of VECTORDB-BRAIN ingests documents, chunks and embeds them, and stores vectors in Qdrant (`omnikb_documents` collection) for semantic retrieval. Layer 2 is the planned "episodic" layer: it stores session artifacts — query results, interpretations, user annotations, and intermediate reasoning — so that a running session can be resumed, compared across time, and eventually distilled into Layer 3 concept nodes.

The consolidation trigger (`POST /consolidation/run`) is already implemented and wired as a stub. The stub's completion message reads:

> `consolidation_stub: trigger executed; episodic store pipeline not wired`

The L2 store is what "not wired" means in practice. Before any implementation begins, the storage backend and schema must be decided, because:

1. The choice constrains the query interface the L2/L3 Agent can build.
2. It affects how the episodic buffer feeds the Layer 3 clustering pass (HDBSCAN/k-means per `l2-l3-transfer-protocol.md`).
3. Changing storage backends after data accumulates is expensive.

**Constraints:**
- Local-first, offline-capable (no cloud dependency for v1).
- Runs on Windows 11 Pro + Docker Desktop.
- Existing Qdrant instance on port 6333 is the L1 production store.
- Research Qdrant instance is on port 6334 — not available for production L2 data.
- Python + FastAPI service (`src/omnikb/`) is the only writer.

---

## Decision Drivers

- **Structured metadata vs. vector search:** Session artifacts have structured fields (session ID, timestamp, query text, source chunk IDs) AND optional semantic content (embeddings for similarity lookup). The right store depends on which query pattern dominates.
- **Persistence requirements:** Artifacts must survive FastAPI restarts. In-memory is not acceptable.
- **Dev complexity:** Must not require a new infrastructure service beyond what already runs in `docker-compose.yml` (Qdrant + FastAPI + frontend).
- **Test isolation:** Artifacts must be easy to create/destroy in pytest without touching L1 production data.
- **L3 handoff:** L2 must expose a batch-export interface so the L3 consolidation pass can read all session chunks for clustering.

---

## Considered Options

### Option A: Dedicated Qdrant collection (`omnikb_l2_sessions`)

**Structure:** Each session artifact is a `PointStruct` with:
- `vector`: embedding of the artifact text (query or interpretation snippet)
- `payload`: `{session_id, artifact_type, created_at, source_chunk_ids, text_snippet, ...}`

Artifacts are upserted via the existing `QdrantStore` adapter with `collection="omnikb_l2_sessions"`. Retrieval uses Qdrant filter + vector search (e.g., "find session artifacts similar to query X").

**Pros:**
- No new infrastructure — Qdrant already runs.
- `QdrantStore` adapter already exists and is tested.
- Semantic similarity across session artifacts is native.
- L3 clustering can operate directly on these vectors without an export step.

**Cons:**
- Requires embedding every artifact at write time (CPU cost for session metadata that may not need similarity search).
- Qdrant payload filtering is less ergonomic than SQL for structured queries (e.g., "all artifacts from session_id X after timestamp T").
- Comingles L1 and L2 data on the same Qdrant instance — requires discipline not to mix collections.
- Collection must be created and managed separately; schema migrations are manual.

### Option B: SQLite sidecar (`data/l2_sessions.db`)

**Structure:** A local SQLite database with at minimum:

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    label TEXT
);

CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    artifact_type TEXT NOT NULL,   -- 'query', 'result', 'annotation'
    created_at TEXT NOT NULL,
    text_content TEXT,
    source_chunk_ids TEXT,         -- JSON array
    embedding_ref TEXT             -- optional: Qdrant point_id if embedded
);
```

Artifacts written via a thin `L2StoreAdapter` using Python's built-in `sqlite3`. No new dependency.

**Pros:**
- Rich structured query capability (JOIN, filter, ORDER BY) via SQL.
- Zero new infrastructure — SQLite ships with Python.
- Simple schema evolution via migration scripts (already have `scripts/migrations/`).
- Test isolation: use an in-memory SQLite DB (`":memory:"`) in pytest.
- Embedding is optional — store metadata immediately, embed lazily or on L3 pass.

**Cons:**
- No native vector similarity for L2→L3 clustering without an export step.
- Write contention under concurrent requests (SQLite WAL mode required; single writer).
- Another persistence layer to back up (`data/l2_sessions.db` must be in the bind-mount or Docker volume).
- Deviates from the "Qdrant-native" architecture of L1.

### Option C: JSON file store (`data/l2/sessions/<session_id>.json`)

**Structure:** One JSON file per session:

```json
{
  "session_id": "...",
  "created_at": "...",
  "artifacts": [
    {"artifact_type": "query", "created_at": "...", "text": "...", "source_chunk_ids": [...]}
  ]
}
```

Written by the API, read by the consolidation trigger at run time.

**Pros:**
- Trivially simple. No dependency, no schema.
- Easy to inspect and debug.
- Portable — just files in `data/`.

**Cons:**
- No query capability beyond directory listing.
- Read-all-then-filter for any aggregation — poor for large session counts.
- Concurrent write safety requires file locking or per-session write serialization.
- No natural path to L3 vector clustering without a separate embed + batch step.

---

## Decision

**ACCEPTED: Option B — SQLite sidecar (`data/l2_sessions.db`)**

**Rationale:**

Session artifacts are fundamentally structured records (session ID, artifact type, timestamps, source references). Semantic similarity search across session artifacts is a secondary concern in v1 — the L3 consolidation pass will embed and cluster them in batch, not via interactive similarity lookup during ingest. SQLite's relational model is a better fit for the primary query pattern: "give me all artifacts for session X in order."

Option A (Qdrant) would force embedding at write time for every artifact, including metadata-only records that will never be similarity-searched directly. It also requires managing a separate Qdrant collection with no schema enforcement.

Option C (JSON files) lacks any query capability and will degrade as session counts grow.

SQLite's WAL mode handles concurrent reads cleanly; write contention is acceptable for a single-API-process local deployment. The `scripts/migrations/` directory already exists for schema evolution. Test isolation via `":memory:"` is a first-class SQLite feature.

**If the Operator prefers Option A** (Qdrant-native): the L2/L3 Agent can implement it using the existing `QdrantStore` adapter with a new collection name. The interface contract below remains the same.

---

## Consequences

**Positive:**
- No new infrastructure services needed.
- Rich structured queries for session management and audit.
- Schema migrations are explicit and versioned.
- pytest isolation is trivial (`":memory:"`).
- Lazy embedding: artifacts are stored immediately; embedding happens in the consolidation pass, not at write time.

**Negative / Trade-offs:**
- SQLite WAL mode must be enabled; the adapter must not leave connections open across threads.
- `data/l2_sessions.db` must be included in the Docker volume or bind-mount (`docker-compose.yml` update required).
- The L3 clustering pass must embed artifact text on demand rather than querying existing Qdrant vectors — one extra pass per consolidation run.
- Introduces a second persistence technology alongside Qdrant.

---

## Implementation Notes (for L2/L3 Agent when ADR is ACCEPTED)

**Data model — `artifacts` table minimum fields:**

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER PK AUTOINCREMENT` | Surrogate key |
| `session_id` | `TEXT NOT NULL` | FK → `sessions.session_id` |
| `artifact_type` | `TEXT NOT NULL` | `'query'`, `'result_chunk'`, `'annotation'` |
| `created_at` | `TEXT NOT NULL` | ISO-8601 UTC |
| `text_content` | `TEXT` | Raw text for embedding at consolidation time |
| `source_chunk_ids` | `TEXT` | JSON array of L1 Qdrant point IDs |
| `metadata_json` | `TEXT` | Arbitrary extra payload (score, model name, etc.) |

**Adapter interface (`src/omnikb/adapters/l2_store.py`):**

```python
class L2StoreAdapter:
    def start_session(self, session_id: str, label: str | None = None) -> None: ...
    def record_artifact(self, session_id: str, artifact_type: str,
                        text_content: str, source_chunk_ids: list[str],
                        metadata: dict | None = None) -> int: ...
    def get_session_artifacts(self, session_id: str) -> list[dict]: ...
    def export_for_consolidation(self, since: datetime | None = None) -> list[dict]: ...
    def close(self) -> None: ...
```

**Migration path:**
1. `scripts/migrations/0001_create_l2_sessions.py` — create `sessions` + `artifacts` tables with WAL mode.
2. `docker-compose.yml` — add `data/l2_sessions.db` to the API container bind-mount (or use existing `data/` volume).
3. `src/omnikb/consolidation/trigger.py` — replace stub message with call to `L2StoreAdapter.export_for_consolidation()`.

---

## Open Questions — Resolved 2026-07-01

1. **Volume strategy:** ~~Should `data/l2_sessions.db` be bind-mounted from the host or live inside the API container?~~
   **RESOLVED: bind-mount from host**, consistent with `data/qdrant/`. Add to `docker-compose.yml` API service volumes.

2. **Session lifecycle:** ~~When does a session start — implicitly on first query or explicitly via `POST /sessions`?~~
   **RESOLVED: implicit** — a session record is created automatically on the first artifact write. No new API route. API contract unchanged.

3. **Retention policy:** ~~Should old session artifacts be purged after consolidation or kept indefinitely?~~
   **RESOLVED: keep indefinitely**. No purge. No `CONSOLIDATION_RETENTION_DAYS` config needed in v1.

4. **Concurrency model:** Acknowledged. WAL mode required for v1 single-process. Multi-worker Gunicorn would need a connection pool — deferred until scaling is needed.
