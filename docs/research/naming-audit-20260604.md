# Naming audit — OmniKB vs VECTORDB-BRAIN

**Date:** 2026-06-04
**Branch:** `agent/code-quality-naming-audit`
**Canonical policy:** [docs/agents/NAMING_DECISION.md](../agents/NAMING_DECISION.md)
**Scope:** `*.py`, `*.ts`, `*.tsx`, `*.md`, `*.yml` under repo root (`.claude/worktrees` excluded from search paths).

## Policy summary (recommended wording)

| Context | Use |
|--------|-----|
| GitHub repo, operator docs, PR titles, web UI product name | **VECTORDB-BRAIN** |
| Python package, import path, Docker Compose service names, Qdrant collection defaults | **omnikb** / **omnikb-*** (unchanged) |
| Narrative “product” alias in prose | **OmniKB** only when paired or subordinated, e.g. “VECTORDB-BRAIN (OmniKB)” on first mention in public-facing pages |
| Host path examples | `I:/VECTORDB-BRAIN/...` (repo directory name) |

**Do not rename** the `omnikb` package or `omnikb_documents` collection without a dedicated migration ADR.

---

## Scan statistics

| Metric | Count |
|--------|------:|
| Files with ≥1 match (any of OmniKB / VECTORDB-BRAIN / VectorDB-Brain, case-insensitive) | **72** |
| Files with `OmniKB` (case-sensitive) | **36** |
| Files with `VECTORDB-BRAIN` | **28** |
| Files with `VectorDB-Brain` (mixed case) | **6** |
| `src/omnikb/**/*.py` with branding strings | **2** (path examples only; correct) |
| `web/src/*.{ts,tsx}` | **4** (all use VECTORDB-BRAIN for UI; consistent) |

---

## Category A — Correct / no change (technical identifiers)

These are intentional aliases per NAMING_DECISION.md.

- **Python imports:** `from omnikb...` throughout `src/omnikb/`, `tests/`, `scripts/`.
- **Docker / compose:** service names `omnikb-api`, `omnikb-qdrant`, `omnikb-mailcatcher` (see `scripts/generate_docker_resource_model.py`, `docs/dev-mailcatcher.md`).
- **Settings / env:** `OMNIKB_*` in `logs/README.md`, `src/omnikb/config/settings.py` (field names, not public title).
- **Qdrant:** collection `omnikb_documents` in `tests/test_ui_logging.py`.
- **Path literals in code/tests:** `I:/VECTORDB-BRAIN/data/sources/...` in `src/omnikb/config/settings.py:30`, `src/omnikb/domain/path_safety.py:88`, `tests/test_path_safety.py:23–41`, `web/src/App.tsx:293`.

---

## Category B — Public-facing: prefer VECTORDB-BRAIN (inconsistencies)

### B1 — Primary entry docs use OmniKB-only titles

| File | Line | Issue | Recommended wording |
|------|-----:|-------|---------------------|
| `README.md` | 1 | H1 `# OmniKB Local Vector Knowledge Base` | `# VECTORDB-BRAIN` with subtitle “local vector knowledge base (OmniKB stack)” |
| `docs/data-curation-pipeline.md` | 1 | Title `(OmniKB)` only | `# Data Curation Pipeline Strategy (VECTORDB-BRAIN)`; body: “OmniKB vector store” → “VECTORDB-BRAIN ingest” or “omnikb stack” |
| `docs/obsidian-vault-conventions.md` | 1 | `(OmniKB-aligned)` | `(VECTORDB-BRAIN / OmniKB-aligned)` |
| `logs/README.md` | 1 | `# OmniKB runtime logs` | `# VECTORDB-BRAIN runtime logs` |

### B2 — Operator / internal docs: OmniKB as sole product name

| File | Lines (sample) | Issue |
|------|----------------|-------|
| `docs/dev-mailcatcher.md` | 5, 40–42, 51, 74 | “OmniKB” without repo name in several paragraphs |
| `docs/internal/docker-desktop-wsl2-resources.md` | multiple | “OmniKB” in headings and tables |
| `docs/internal/qdrant-wal-disk-space-troubleshooting.md` | multiple | Mixed; some sections OmniKB-only |
| `docs/internal/pre-publish-quality-checklist.md` | multiple | Mostly VECTORDB-BRAIN; verify remaining OmniKB-only bullets |
| `devtools/error-tracking-db.md` | multiple | Historical “OmniKB” incident titles |

**Recommended pattern:** First sentence: “VECTORDB-BRAIN (OmniKB)” then “the API container (`omnikb-api`)” for technical steps.

### B3 — Mixed case: `VectorDB-Brain`

| File | Line | Issue |
|------|-----:|-------|
| `docs/developer-guide.md` | 3 | “VectorDB-Brain (OmniKB)” |
| `docs/testing-framework.md` | 3 | “VectorDB-Brain” |
| `docs/security-hardening-guide.md` | — | “VectorDB-Brain” |
| `docs/performance-profiling-and-continuous-improvement.md` | — | “VectorDB-Brain” |
| `docs/layered-knowledge-architecture.md` | — | “VectorDB-Brain” |
| `docs/architecture-graphviz.md` | — | Both forms in same doc |

**Fix:** Replace with `VECTORDB-BRAIN` in all operator-facing markdown.

### B4 — Agent / orchestration docs (mostly aligned; minor drift)

| File | Note |
|------|------|
| `AGENT_ORCHESTRATION_PLAN.md` | Uses VECTORDB-BRAIN consistently; still references “OmniKB” as inconsistency to fix (lines 274–295) — meta, not wrong |
| `docs/agents/CODE_QUALITY.md` | Correct policy text |
| `docs/agents/NAMING_DECISION.md` | Canonical source of truth |
| `docs/agents/CLAUDE_CODE_LAUNCH.md` | Correct dispatch wording |

### B5 — Sample / demo content

| File | Line | Note |
|------|-----:|------|
| `data/sources/sample-note.md` | — | “OmniKB” in body (fixture; low priority) |
| `data/sources/sample-rag.md` | — | Query text mentions OmniKB |
| `docs/sample-data-evidence.md` | 23 | Example query string “OmniKB retrieval…” |

---

## Category C — Already consistent (reference)

| File | Lines | Usage |
|------|-------|--------|
| `web/src/branding.ts` | 1–2 | `PRODUCT_NAME = 'VECTORDB-BRAIN'` + comment |
| `web/src/main.tsx` | 9 | Boot log uses VECTORDB-BRAIN |
| `web/src/logging/UiLogOverlay.tsx` | 61 | UI label VECTORDB-BRAIN |
| `CLAUDE.md` | 1, 5 | “OmniKB (repo: VECTORDB-BRAIN)” |
| `docs/ingestion-and-curation-architecture.md` | 3 | “VECTORDB-BRAIN / OmniKB” |
| `docs/architecture-colbert-multivector-proforma.md` | 20 | VECTORDB-BRAIN in architecture prose |
| `CONTRIBUTING.md` | — | Repo-oriented naming |

---

## Category D — Scripts and generated artifacts

| File | Count | Note |
|------|------:|------|
| `scripts/generate_docker_resource_model.py` | 25 | Workbook strings “OmniKB”; sheet `OmniKB_Expected` — acceptable as **internal** Excel labels; add README cell “Project: VECTORDB-BRAIN” on cover sheet when regenerated |
| `scripts/benchmark_chunking.py` | — | Comment “OmniKB” |
| `scripts/generate_corpus_manifest.py` | — | No branding conflict |

---

## Category E — Duplicate path variants (Windows)

Some hits appear under both `docs/agents/` and `docs\agents\` in tooling output; content is the same on disk. No separate fix required.

---

## Recommended doc wording templates

1. **README lead:**
   `# VECTORDB-BRAIN`
   Local, offline-first vector knowledge base (FastAPI **omnikb** service + Qdrant). Former working name: OmniKB.

2. **Architecture doc opening:**
   “This document describes how **VECTORDB-BRAIN** processes sources through the **omnikb** ingestion pipeline…”

3. **Obsidian / curation:**
   “Export from Obsidian into `data/sources/staging/`; after validation, promote to `curated/` for **VECTORDB-BRAIN** ingest (see `omnikb` curation gate).”

4. **Docker runbooks:**
   “Start the stack: `docker compose up` (services `omnikb-api`, `omnikb-qdrant`). Project directory: `VECTORDB-BRAIN`.”

---

## Fix priority (for follow-up PRs)

| Priority | Action |
|----------|--------|
| P0 | `README.md` H1 + first paragraph alias |
| P1 | Replace `VectorDB-Brain` → `VECTORDB-BRAIN` in six docs (Category B3) |
| P1 | Retitle `docs/data-curation-pipeline.md` and `docs/obsidian-vault-conventions.md` |
| P2 | Pass over `docs/internal/*` and `devtools/error-tracking-db.md` for first-mention pairing |
| P3 | Sample corpus markdown under `data/sources/` (optional) |

**This audit did not apply renames** — documentation-only deliverable per task scope.

---

## Ruff (code quality gate)

Command: `python -m ruff check src tests`
**Result:** All checks passed (0 issues). No `src/omnikb` edits required.
