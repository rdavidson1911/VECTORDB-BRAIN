# OmniKB Local Vector Knowledge Base

Local Docker Desktop microservice scaffold for a vector-enabled knowledge base on Windows 11 Pro.

## Stack

- FastAPI API service (`api`) for ingest/query orchestration.
- Qdrant vector database (`qdrant`) with persistent local storage.
- Local `sentence-transformers` embeddings for offline-first operation.
- Source file ingestion for `.md`, `.txt`, and `.pdf`.

## Project Layout

- `src/omnikb/api`: HTTP routes and request models.
- `src/omnikb/services`: ingestion and query use-cases.
- `src/omnikb/adapters`: document loading, embeddings, Qdrant implementation.
- `src/omnikb/domain`: chunking and core types.
- `data/sources`: bind-mounted source corpus.
- `data/qdrant`: persistent Qdrant data.

## Quick Start (Windows PowerShell)

1. Create your local env file:
   - `Copy-Item .env.example .env`
2. Add source documents to `data/sources`.
3. Start services:
   - `docker compose up --build -d`
4. Check API:
   - `Invoke-RestMethod http://localhost:8000/health`
5. Ingest the mounted corpus:
   - `Invoke-RestMethod -Method Post -Uri http://localhost:8000/ingest/path -ContentType application/json -Body '{"path":"/data/sources","recursive":true}'`
6. Query:
   - `Invoke-RestMethod -Method Post -Uri http://localhost:8000/query -ContentType application/json -Body '{"query":"What is in my vault?","limit":5}'`

## API Endpoints

- `GET /health`
- `POST /ingest/path`
- `POST /query`
- `GET /collections/{name}/stats`
- `GET /corpus/summary`
- `GET /corpus/sources`
- `POST /ingest/preview`

OpenAPI docs are available at `http://localhost:8000/docs`.

## Local Testing

Install dev dependencies and run tests:

- `python -m pip install -e .[dev]`
- `pytest`

## Quality Checks and Hooks

Run local quality checks:

- Lint: `python -m ruff check src tests`
- Format: `python -m ruff format src tests` (Black is optional locally if you prefer it; CI uses Ruff only.)
- Type check: `python -m mypy src` (IDE/Pylance: `pyrightconfig.json`; CLI: `npx pyright src`)
- Security check: `python -m bandit -c pyproject.toml -r src`

Enable pre-commit hooks:

- `python -m pre_commit install`
- `python -m pre_commit run --all-files`

## Smoke Test

After containers are running:

- `.\scripts\smoke-test.ps1`

## Benchmarking

Run chunking benchmark harness:

- `python scripts/benchmark_chunking.py` (see `python scripts/benchmark_chunking.py --help`)

Playbook:

- `docs/benchmarking-playbook.md`

## Corpus curation automation

- Manifest contract: `docs/corpus-manifest-contract.md`
- Generate manifest JSON: `python scripts/generate_corpus_manifest.py`
- Dry-run validation (duplicates, empty extract, size warnings): `python scripts/validate_corpus.py`
- Obsidian workflow: `docs/obsidian-vault-conventions.md`, `docs/obsidian-export-to-omnikb.md`

## User Documentation

- Data curation pipeline strategy (governance, dedupe, chunking, migration): `docs/data-curation-pipeline.md`
- Content sidecars and non-text types: `docs/content-sidecars.md`
- User and admin operations guide: `docs/user-operations-guide.md`
- Developer setup and engineering workflow guide: `docs/developer-guide.md`
- Testing framework and systematic coverage guide: `docs/testing-framework.md`
- Performance profiling and continuous improvement guide: `docs/performance-profiling-and-continuous-improvement.md`
- Security hardening guide: `docs/security-hardening-guide.md`
- Planned layered knowledge architecture (raw/cache/dreaming/graph): `docs/layered-knowledge-architecture.md`
- Layered architecture implementation roadmap (phases, API drafts, test criteria): `docs/implementation-roadmap-layered-architecture.md`
- System architecture diagram (Graphviz DOT): `docs/architecture-graphviz.md`
- Incident and troubleshooting evidence log: `devtools/error-tracking-db.md`
- Internal React/browser DevTools debugging guide: `docs/internal-react-devtools-debugging-guide.md`

## React Web App

From `web/`:

- `npm install`
- `npm run dev`

Playwright smoke (API + Vite must be running; first ingest can take 1–2 minutes while the embedding model loads):

- From repo root: `npm run smoke:playwright` (uses root `package.json` to run the script in `web/`)
- Or from `web/`: `npm run smoke:playwright`
- Optional env: `INGEST_TIMEOUT_MS` (default `120000`), `SMOKE_SKIP_INGEST=1` to skip seed ingest if the corpus is already indexed

Set frontend API target in:

- `web/.env.example` (copy to `.env` and edit `VITE_API_BASE_URL` if needed)

## Notes for Obsidian and Future React UI

- Keep clients decoupled by calling only the API endpoints.
- Obsidian integration can start as simple REST calls to `/query`.
- React can reuse the same API contract without backend refactor.
