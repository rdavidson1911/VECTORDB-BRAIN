# Contributing to OmniKB / VECTORDB-BRAIN

Thank you for helping improve this project. Keep changes focused, tested, and aligned with the existing API-first design so alternate clients (React, scripts, future mobile or desktop UIs) stay decoupled from any single frontend.

## Quick setup

1. **Python (backend):** Python 3.11+ recommended (CI uses 3.11).
   `python -m pip install -e ".[dev]"`

2. **Runtime stack:** See [README.md](README.md) — Docker Compose runs the API, Qdrant, and mounted corpus.

3. **Web app:** From `web/` run `npm install`, `npm run dev`. Copy `web/.env.example` to `web/.env` if you need a non-default API URL.

## Quality gates (run before opening a PR)

Matches CI in [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

**Backend**

```powershell
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m bandit -c pyproject.toml -r src
python -m pytest
```

**Frontend** (`web/`)

```powershell
npm run lint
npm run build
```

Optional coverage: `python -m pytest --cov=src/omnikb --cov-report=term-missing`

Maintainers preparing a **public release** or merge to `main` should also follow [docs/internal/pre-publish-quality-checklist.md](docs/internal/pre-publish-quality-checklist.md) (secrets hygiene, what not to commit, merge/PR flow).

## Smokes (local, with services up)

- API: `.\scripts\smoke-test.ps1` (expects `http://localhost:8000` and Compose stack).
- UI: start `npm run dev` in `web/`, then from repo root `npm run smoke:playwright`.
  Use `SMOKE_SKIP_INGEST=1` when the corpus is already indexed to save time. See [docs/testing-framework.md](docs/testing-framework.md).

## Design pointers

- **Layered knowledge model** (raw vs session vs relationship graph) is described in [docs/layered-knowledge-architecture.md](docs/layered-knowledge-architecture.md) and [docs/vision-beyond-rag.md](docs/vision-beyond-rag.md). Many roadmap items are not yet implemented; treat docs that say “planned” as design targets, not current behavior.
- **Security:** do not commit secrets, `.env`, or credentials. Follow [docs/security-hardening-guide.md](docs/security-hardening-guide.md).

## Licensing

By contributing, you agree your contributions are under the same license as the project ([LICENSE](LICENSE), MIT).
