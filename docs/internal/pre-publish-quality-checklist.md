# Pre-publish quality checklist (VECTORDB-BRAIN / OmniKB)

Use this before merging to `main` and making the repository public on GitHub.

---

## 1. Local gates (match [CI](../../.github/workflows/ci.yml))

From repo root:

```powershell
Set-Location I:\VECTORDB-BRAIN
python -m pip install -e ".[dev]"
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m bandit -c pyproject.toml -r src
python -m pytest -q
```

Web:

```powershell
Set-Location I:\VECTORDB-BRAIN\web
npm ci
npm run lint
npm run build
```

Optional (recommended):

```powershell
Set-Location I:\VECTORDB-BRAIN
pre-commit run --all-files
```

---

## 2. Secrets and hygiene (not in CI today)

| Check | Command / action |
|--------|------------------|
| **No `.env` committed** | `git status` must not list `.env`; only `.env.example` / `web/.env.example` |
| **No API keys in tree** | Search staged diff; avoid tokens in `devtools/error-tracking-db.md` |
| **Large / runtime data** | Do not commit `data/qdrant/*`, `data/sources/*` (except samples), `logs/*.jsonl`, `internal_docs/`, `*.har` |
| **Personal notes** | Keep `my-REMINDERS.md` local (untracked) |
| **Local tooling** | Skip `ollama/`, `poetry.lock` unless the project officially adopts Poetry |

---

## 3. What to stage for a public release PR

**Include:**

- Application code (`src/`, `web/`, `tests/`)
- `docker-compose.yml`, `Dockerfile`, `pyproject.toml`, `package.json` (root scripts)
- Docs: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `docs/` (including `docs/internal/` ops guides)
- Dev tooling intended for contributors: `devtools/playwright-smoke.mjs`, `scripts/*.ps1` (smoke/dev)
- `.github/workflows/ci.yml`, `.env.example`, `web/.env.example`

**Exclude (typical):**

- `my-REMINDERS.md`, `internal_docs/`, `data/qdrant/`, `.env`
- Scratch: `docs/typescript-debug.py`, `scan-vectordb-staging.sh`, `devtools/*.har`, `devtools/*.tree`
- `poetry.lock` if install path is `pip install -e ".[dev]"` (current standard)

---

## 4. Commit and merge workflow

```powershell
Set-Location I:\VECTORDB-BRAIN
git branch --show-current   # e.g. chore/brave-react-devtools-debug

# Stage intentionally (example — adjust paths)
git add src tests web docs devtools/playwright-smoke.mjs devtools/error-tracking-db.md
git add scripts .github CONTRIBUTING.md SECURITY.md LICENSE README.md
git add .env.example docker-compose.yml pyproject.toml package.json logs/.gitkeep logs/README.md
# Add other docs you intend to ship; do NOT git add -A blindly

git status
git commit -m "feat: VECTORDB-BRAIN web UI, ingest path safety, and publish-ready docs"

git fetch origin
git checkout main
git pull origin main
git merge chore/brave-react-devtools-debug   # or merge via PR on GitHub
git push origin main
```

**Preferred for collaboration:** open a **Pull Request** on GitHub instead of merging locally, so CI runs on the remote and reviewers can join.

```powershell
git push -u origin chore/brave-react-devtools-debug
gh pr create --base main --title "Release: VECTORDB-BRAIN dashboard and hardened ingest" --body "..."
```

---

## 5. After merge (public repo)

- [ ] Confirm **GitHub Actions** green on `main`
- [ ] Repository **Description** + topics: `vector-database`, `qdrant`, `rag`, `knowledge-base`, `fastapi`, `streamlit` (if applicable)
- [ ] Enable **Issues** and link `CONTRIBUTING.md` / `SECURITY.md`
- [ ] Add **branch protection** on `main` (require CI, no force-push)
- [ ] Optional: Dependabot, secret scanning (GitHub Advanced Security or third-party)

---

## 6. Finding collaborators

- Tag the repo with clear **README** “looking for collaborators” and **good first issue** labels
- Link architecture docs (`docs/layered-knowledge-architecture.md`, ColBERT pro-forma) so others see the vision
- Post in communities aligned with **local-first RAG**, **Qdrant**, **Obsidian/knowledge bases** (respect each forum’s rules)

---

## Last run log

| Date | Branch | Python | Web | Notes |
|------|--------|--------|-----|-------|
| 2026-05-26 | `chore/brave-react-devtools-debug` | ruff/mypy/bandit/pytest OK (28 tests) | lint OK, build OK | ESLint `UiLogOverlay` revision dep fixed |
