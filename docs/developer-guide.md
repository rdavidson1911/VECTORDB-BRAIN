# Developer Guide

This guide is the primary engineering entry point for local development in VectorDB-Brain (OmniKB).

Use this together with:

- `README.md` for quick start and command references.
- `docs/user-operations-guide.md` for operator workflows.
- `docs/data-curation-pipeline.md` for canonical data governance and ingest policy.
- `docs/benchmarking-playbook.md` for chunking benchmark procedures.

## 1) What Exists Today

- Backend: FastAPI API in `src/omnikb/api`, service layer in `src/omnikb/services`, adapters in `src/omnikb/adapters`.
- Vector storage: Qdrant via `src/omnikb/adapters/qdrant_store.py`.
- Ingestion: `.md`, `.txt`, `.pdf` ingestion/chunk/embed pipeline via `src/omnikb/services/ingestion_service.py`.
- Query path: HTTP route `POST /query` in `src/omnikb/api/routes.py` calling `QueryService`.
- Frontend: React UI in `web/src/App.tsx`.
- Smoke evidence: `devtools/playwright-smoke.mjs` appends incidents to `devtools/error-tracking-db.md`.

## 2) Local Development Setup

### Python environment

```powershell
python -m pip install -e ".[dev]"
```

### Frontend environment

```powershell
cd web
npm install
```

### Start services

```powershell
docker compose up --build -d
```

### Verify API health

```powershell
Invoke-RestMethod http://localhost:8000/health
```

## 3) Core Engineering Commands

Run from repo root unless noted.

### Quality gates (local)

```powershell
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m bandit -c pyproject.toml -r src
python -m pytest
```

### Hooks

```powershell
python -m pre_commit install
python -m pre_commit run --all-files
```

### Smoke and benchmark workflows

```powershell
.\scripts\smoke-test.ps1
python scripts/benchmark_chunking.py
npm run smoke:playwright
```

For benchmark interpretation, see `docs/benchmarking-playbook.md`.

## 4) Service and Data Boundaries

### Current boundary model

- `data/sources` is treated as the source corpus (mounted read-only in Docker compose).
- Qdrant stores chunk payloads and vectors.
- `data/processed` holds generated local artifacts (benchmarks, manifests, validation outputs).

### Planned layering (documented architecture only)

The planned multi-layer model is described in `docs/layered-knowledge-architecture.md`:

1. Layer 1: raw read-only documents.
2. Layer 2: session/cache read-write artifacts.
3. Layer 3: persistent relationship and consistency scores derived by background processing.

This model is not fully implemented yet.

## 5) Current vs Planned Query Expansion

`src/omnikb/api/schemas.py` includes `include_neighbors` and `neighbor_window` fields in `QueryRequest`. Current route/service implementations do not yet expand results by neighbors or by multi-layer traversal.

Treat neighbor/layer drill-down as planned behavior until implemented in API/service/UI code.

## 6) Pull Request Readiness Checklist

- Confirm no runtime behavior changed unless intended by scope.
- Run local quality gates (ruff/mypy/bandit/pytest).
- If touching web UI, verify `npm run smoke:playwright` (or capture clear reason for skip/failure).
- Link evidence in PR description:
  - test results,
  - smoke outcomes,
  - benchmark notes if retrieval/chunking behavior changed.
- If docs-only, explicitly state "docs-only; no runtime changes."

## 7) Troubleshooting Notes

- A first ingest can be slow due to embedding model warm-up.
- For Playwright smoke ingest timeouts, use `INGEST_TIMEOUT_MS` or pre-seed ingest manually (as noted in `devtools/playwright-smoke.mjs` output).
- Record incidents in `devtools/error-tracking-db.md`.
