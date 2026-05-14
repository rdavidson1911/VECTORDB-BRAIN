# Testing Framework and Coverage Strategy

This document defines systematic testing coverage for VectorDB-Brain across backend, data pipeline, frontend, performance, and security workflows.

Companion docs:

- `docs/developer-guide.md`
- `docs/user-operations-guide.md`
- `docs/benchmarking-playbook.md`
- `docs/security-hardening-guide.md`
- `devtools/error-tracking-db.md`

## 1) Coverage Model

Use a layered test pyramid:

1. Unit tests (fast, deterministic, pure logic first).
2. API tests with fakes/mocks (route/service behavior).
3. Adapter/integration tests (filesystem, Qdrant, ingestion edge cases).
4. Smoke tests (containerized happy path).
5. UI E2E smoke (Playwright).
6. Performance and security checks (non-functional gates).

## 2) Current Coverage Baseline

Current tracked test modules:

- `tests/test_chunking.py`
- `tests/test_api_health.py`
- `tests/test_ingestion_idempotency.py`
- `tests/test_curation.py`

Current CI (`.github/workflows/ci.yml`) runs:

- Ruff check
- Ruff format check
- Mypy (`src`)
- Bandit (`src`)
- Pytest

## 3) Recommended Coverage Matrix

### Unit

- chunking strategies and overlap boundaries
- metadata transforms and schema validation
- query analytics calculations
- deterministic ID/hash derivation

### API (with fakes)

- request validation and error mapping
- ingest/query response contracts
- filter behavior (`source_path`, `file_type`, time range, score threshold)

### Adapter/Integration

- document loading edge cases (encoding, pdf extraction failures, empty extracts)
- Qdrant adapter read/write and filtering behavior
- idempotent re-ingestion behavior by `source_path`

### Smoke

- API health checks
- ingest path success/failure semantics
- query viability after ingest

### E2E (Playwright)

- dashboard loads and health badges render
- search interaction returns results
- ingest path action in UI (when enabled in smoke flow)

## 4) Command Reference

### Backend quality and tests

```powershell
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m bandit -c pyproject.toml -r src
python -m pytest
```

### Optional coverage report

```powershell
python -m pytest --cov=src/omnikb --cov-report=term-missing
```

### Web smoke

```powershell
npm run smoke:playwright
```

## 5) Playwright Smoke Triage Workflow

When `npm run smoke:playwright` fails:

1. Identify the failing phase (`CORS preflight`, `API health`, `Seed ingest`, `Dashboard load`, `Query run`).
2. Verify API availability (`GET /health`).
3. If failing at seed ingest:
   - expect slow cold start from embedding model load,
   - increase `INGEST_TIMEOUT_MS`,
   - or run a manual ingest once and retry with `SMOKE_SKIP_INGEST=1`.
4. Confirm incident entry appended to `devtools/error-tracking-db.md`.
5. Log root cause and follow-up action in PR notes or issue tracker.

## 6) Quality Gate Policy

Minimum merge expectations:

- lint and format checks pass,
- type check passes for backend scope,
- security check passes,
- tests pass for touched functionality.

For docs-only changes:

- no runtime code modifications,
- docs should remain accurate with explicit "planned" labeling where behavior is not implemented yet.

## 7) Planned Enhancements (Not Implemented Yet)

- CI coverage threshold enforcement (e.g., pytest-cov gate).
- dedicated frontend CI job (lint/build/test).
- marker-based integration suite for containerized components.
- scheduled or pre-release full smoke matrix.
