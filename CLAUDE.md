# CLAUDE.md — OmniKB / VECTORDB-BRAIN

## 1. Project Identity

OmniKB (repo: VECTORDB-BRAIN) is a local, offline-first vector knowledge base running on Windows 11 Pro via Docker Desktop. The backend is a **FastAPI** service (`src/omnikb/`) that ingests `.md`, `.txt`, and `.pdf` documents, chunks and embeds them using **sentence-transformers**, and stores vectors in **Qdrant** for semantic retrieval. A **React/Vite** single-page app (`web/`) provides an interactive query console. All services are wired together with **Docker Compose** and bind-mount the corpus from the host into the API container. The system is designed to evolve beyond naive RAG toward a layered knowledge architecture (raw corpus → session artifacts → relationship graph), though only Layer 1 (ingest + query) is currently implemented.

---

## 2. Repo Layout

```
src/omnikb/           Python package (src layout)
  api/                FastAPI routes and Pydantic request/response schemas
  services/           Ingestion and query use-cases
  adapters/           Document loader, embeddings, Qdrant store implementation
  domain/             Chunking strategies and core domain types
  config/             Settings (pydantic-settings), host path helpers
  middleware/         Request timing and other middleware
  infra/              File log writer and infrastructure utilities

web/                  React/Vite frontend (npm workspace)
  src/                App.tsx, charts/, branding, theme

data/
  sources/            Bind-mounted corpus (three zones — see §4.1)
  qdrant/             Persistent Qdrant data volume
  processed/          Generated local artifacts (benchmarks, manifests) — gitignored content

docs/                 Architecture, vision, runbooks, ADRs, obsidian workflow
  decisions/          Architecture Decision Records (ADRs)
  internal/           Internal-only operational docs

devtools/             Playwright smoke runner, error-tracking DB
scripts/              Corpus validation, manifest generation, benchmark CLI, dev helpers
tests/                pytest test suite
logs/                 Runtime log output (gitignored content, .gitkeep tracked)
```

---

## 3. Engineering Standards (non-negotiable)

- All code must pass **ruff check**, **ruff format**, **mypy**, **bandit**, and **pytest** before commit.
- **pre-commit hooks** are installed and must stay green (`python -m pre_commit run --all-files`).
- **Never commit** secrets, `.env` files, or API keys — see §4.5 for blocking patterns.
- **Star schema only** in any data model work; use integer surrogate keys.
- **Type-cast everything** in PowerQuery M before it enters any data model.
- Frontend PRs must pass `npm run lint` and `npm run build` in `web/`.
- Any deviation from these standards requires an ADR in `docs/decisions/` before the code is committed (see §6).

---

## 4. Data Quality Charter (standing instructions for all CLI sessions)

### 4.1 Staging Layout

`data/sources/` has three zones — **never mix them**:

| Zone | Path | Purpose |
|------|------|---------|
| Samples | `data/sources/_samples/` | Smoke/test fixtures only — **EXEMPT** from hard gate |
| Staging | `data/sources/staging/` | Obsidian export target — pre-validation only, not indexed by routine ingest |
| Curated | `data/sources/curated/` | **Only** zone routine ingest indexes — hard gate always applies |

### 4.2 Hard Gate Policy

- **Never write code** that ingests from `data/sources/curated/` without running frontmatter validation first.
- **Never set** `allow_quality_override=true` in any code committed to `main`.
- Override requires **both**: `allow_quality_override=true` in the request body **AND** `CURATION_ALLOW_OVERRIDE=true` env var — neither alone is sufficient.
- If the gate fails, **fix the source note** — never add exemptions without a dated ADR entry in `docs/decisions/`.

### 4.3 Template 2.0.0 Lifecycle (the human preventive control)

Notes must reach **ALL THREE** of these states before export to `data/sources/curated/`:

1. `kb_status: curated`
2. `note_finalized: true`
3. `kb_ingest: true`

**Never set `kb_ingest: true` at note creation time.**

### 4.4 Frontmatter Gate Fields

**ERRORS — block ingest, no exceptions on `main`:**

- `kb_ingest` must be `true`
- `note_finalized` must be `true`
- `kb_status` must be `"curated"`
- if `ai_assisted: true` then `ai_summary_verified` must also be `true`

**WARNINGS — logged, do not block:**

- `summary` field empty
- `kb_reviewed_at` not set on curated notes

### 4.5 Secret Scanning

These regex patterns **always block ingest** regardless of gate settings:

```
AKIA[0-9A-Z]{16}          → AWS access key
ghp_[a-zA-Z0-9]{36}       → GitHub personal access token
sk-[a-zA-Z0-9]{20,}       → OpenAI / generic secret key
password\s*=\s*\S+         → plaintext password assignment
api_key\s*=\s*\S+          → plaintext API key assignment
```

These patterns apply to `data/sources/curated/` content only — not to `.env.example`, `settings.py`, or `pyproject.toml` config files.

### 4.6 Corrective SOP (when bad data reaches Qdrant)

Fix path — always in this order:

1. Fix the source note in Obsidian (unfinalize → edit → re-verify → refinalize)
2. Re-export to `data/sources/staging/`
3. Run: `python scripts/validate_corpus.py --gate-root curated`
4. Promote (move) to `data/sources/curated/`
5. Re-ingest via `POST /ingest/path`
6. Use `DELETE /corpus/sources/{source_path}` for true removal (no replacement file)
7. Record dated entry in `devtools/error-tracking-db.md`

### 4.7 Agent Behavior Rules

- Always run `validate_corpus` before suggesting an ingest command.
- Always check `gate_enabled` in settings before writing ingest code.
- **Never suggest bypassing the gate** for convenience or speed.
- When in doubt about a data quality decision: **STOP and ask the operator**.

---

## 5. Common Commands (quick reference)

**Backend quality gates** (run from repo root):

```powershell
python -m ruff check src tests
python -m ruff format src tests
python -m mypy src
python -m bandit -c pyproject.toml -r src
python -m pytest
python -m pre_commit run --all-files
```

**Services:**

```powershell
docker compose up -d
docker compose down
Invoke-RestMethod http://localhost:8000/health
```

**Corpus operations:**

```powershell
python scripts/validate_corpus.py --root data/sources
python scripts/generate_corpus_manifest.py
python scripts/validate_corpus.py --gate-root curated
```

**Frontend** (from `web/`):

```powershell
cd web && npm run dev
npm run smoke:playwright          # from repo root
```

**Smoke and benchmark:**

```powershell
.\scripts\smoke-test.ps1
python scripts/benchmark_chunking.py
```

---

## 6. Architecture Decisions Log

Any significant decision that deviates from the standards in §3 or the data quality charter in §4 must be recorded in `docs/decisions/` as an ADR (Architecture Decision Record) **before** the code is committed.

Format: `docs/decisions/NNNN-short-title.md`

---

## 7. Current Roadmap State

| Layer | Status |
|-------|--------|
| **Layer 1** — raw corpus, ingest pipeline, query API, React console | **IMPLEMENTED** |
| **Layer 2** — session artifacts, interpretations, cache | **PLANNED** — not built |
| **Layer 3** — relationship graph, consistency scoring, audit trails | **PLANNED** — not built |
| **Dreaming process** — background reconciliation job | **PLANNED** — not built |

Note: `QueryRequest` in `src/omnikb/api/schemas.py` already includes `include_neighbors` and `neighbor_window` fields, but the route/service implementations do not yet expand results by neighbors or perform multi-layer traversal. Treat these as planned behavior until implemented.

See `docs/implementation-roadmap-layered-architecture.md` for phased delivery plans and test criteria.
