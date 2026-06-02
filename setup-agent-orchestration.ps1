#Requires -Version 5.1
<#
.SYNOPSIS
    VECTORDB-BRAIN — Phase 1 Agent Orchestration Infrastructure Setup
.DESCRIPTION
    Creates all devcontainer configs, agent CLAUDE.md system prompts,
    AGENT_WORK_LOG.md, and Makefile targets for the multi-agent orchestration system.
    Run from I:\VECTORDB-BRAIN on branch feature/agent-orchestration-system.
.NOTES
    Author : Nvar / rdavidson1911
    Branch : feature/agent-orchestration-system
    Date   : 2026-06-02
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ROOT = $PSScriptRoot   # should be I:\VECTORDB-BRAIN when run from there
if (-not (Test-Path (Join-Path $ROOT '.git'))) {
    Write-Error "Run this script from the root of I:\VECTORDB-BRAIN"
    exit 1
}

function Write-FileContent {
    param([string]$RelPath, [string]$Content)
    $full = Join-Path $ROOT $RelPath
    $dir  = Split-Path $full -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($full, $Content, [System.Text.Encoding]::UTF8)
    Write-Host "  created: $RelPath" -ForegroundColor Green
}

Write-Host "`nVECTORDB-BRAIN — Agent Orchestration Infrastructure Setup" -ForegroundColor Cyan
Write-Host "============================================================`n"

# ─────────────────────────────────────────────────────────────
# 1. BASE DEVCONTAINER
# ─────────────────────────────────────────────────────────────
Write-Host "1/8  devcontainer configs..." -ForegroundColor Yellow

Write-FileContent '.devcontainer/devcontainer.json' @'
{
  "name": "VECTORDB-BRAIN — Full Stack",
  "dockerComposeFile": ["../docker-compose.yml", "docker-compose.devcontainer.yml"],
  "service": "api",
  "workspaceFolder": "/workspace",
  "features": {
    "ghcr.io/devcontainers/features/python:1": { "version": "3.11" },
    "ghcr.io/devcontainers/features/node:1": { "version": "20" },
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "postCreateCommand": "pip install -e '.[dev]' && npm install --prefix frontend",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.mypy-type-checker",
        "charliermarsh.ruff",
        "bradlc.vscode-tailwindcss",
        "GitHub.copilot",
        "GitHub.copilot-chat"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "editor.formatOnSave": true,
        "[python]": { "editor.defaultFormatter": "charliermarsh.ruff" },
        "mypy-type-checker.args": ["--strict"]
      }
    }
  },
  "forwardPorts": [8000, 5173, 6333],
  "portsAttributes": {
    "8000": { "label": "FastAPI",   "onAutoForward": "notify" },
    "5173": { "label": "React UI",  "onAutoForward": "openBrowser" },
    "6333": { "label": "Qdrant",    "onAutoForward": "silent" }
  },
  "remoteEnv": {
    "QDRANT_URL": "http://qdrant:6333",
    "PYTHONPATH": "/workspace"
  }
}
'@

Write-FileContent '.devcontainer/docker-compose.devcontainer.yml' @'
version: "3.9"

# Overlay on top of the main docker-compose.yml.
# Adds a dedicated Qdrant instance for research/agent experiments (port 6334)
# so no agent experiment can touch the production knowledge store.

services:
  api:
    volumes:
      - ..:/workspace:cached
    environment:
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
    command: sleep infinity   # keep container alive; start FastAPI manually

  qdrant-research:
    image: qdrant/qdrant:latest
    ports:
      - "6334:6333"
    volumes:
      - qdrant_research_data:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO
    restart: unless-stopped

volumes:
  qdrant_research_data:
'@

# ─── Research Agent devcontainer ──────────────────────────────
Write-FileContent '.devcontainer/research/devcontainer.json' @'
{
  "name": "VECTORDB-BRAIN — Research Agent",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "postCreateCommand": "pip install sentence-transformers qdrant-client fastapi uvicorn pytest ipykernel pandas tabulate --break-system-packages",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-toolsai.jupyter",
        "GitHub.copilot-chat"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python"
      }
    }
  },
  "forwardPorts": [6334],
  "portsAttributes": {
    "6334": { "label": "Qdrant Research", "onAutoForward": "silent" }
  },
  "remoteEnv": {
    "QDRANT_URL": "http://localhost:6334",
    "AGENT_ROLE": "research",
    "PYTHONPATH": "/workspaces/VECTORDB-BRAIN"
  },
  "postStartCommand": "docker run -d -p 6334:6333 -v qdrant_research:/qdrant/storage qdrant/qdrant:latest || true"
}
'@

# ─── Qdrant Agent devcontainer ────────────────────────────────
Write-FileContent '.devcontainer/qdrant-agent/devcontainer.json' @'
{
  "name": "VECTORDB-BRAIN — Qdrant Agent",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "postCreateCommand": "pip install qdrant-client pandas tabulate pytest --break-system-packages",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "GitHub.copilot-chat"
      ]
    }
  },
  "forwardPorts": [6334],
  "portsAttributes": {
    "6334": { "label": "Qdrant Research", "onAutoForward": "silent" }
  },
  "remoteEnv": {
    "QDRANT_URL": "http://localhost:6334",
    "AGENT_ROLE": "qdrant",
    "PYTHONPATH": "/workspaces/VECTORDB-BRAIN"
  },
  "postStartCommand": "docker run -d -p 6334:6333 -v qdrant_agent:/qdrant/storage qdrant/qdrant:latest || true"
}
'@

# ─── Code Quality Agent devcontainer ─────────────────────────
Write-FileContent '.devcontainer/code-quality/devcontainer.json' @'
{
  "name": "VECTORDB-BRAIN — Code Quality Agent",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "postCreateCommand": "pip install ruff mypy bandit pytest pytest-cov --break-system-packages && pip install -e '.[dev]' --break-system-packages || true",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.mypy-type-checker",
        "charliermarsh.ruff",
        "GitHub.copilot-chat"
      ],
      "settings": {
        "editor.formatOnSave": true,
        "[python]": { "editor.defaultFormatter": "charliermarsh.ruff" },
        "mypy-type-checker.args": ["--strict"]
      }
    }
  },
  "remoteEnv": {
    "AGENT_ROLE": "code-quality",
    "PYTHONPATH": "/workspaces/VECTORDB-BRAIN"
  }
}
'@

# ─────────────────────────────────────────────────────────────
# 2. AGENT CLAUDE.md SYSTEM PROMPTS
# ─────────────────────────────────────────────────────────────
Write-Host "2/8  agent system prompts (docs/agents/)..." -ForegroundColor Yellow

Write-FileContent 'docs/agents/ORCHESTRATOR.md' @'
# ORCHESTRATOR — VECTORDB-BRAIN Agent System Prompt

## Role
You are the ORCHESTRATOR for VECTORDB-BRAIN. You are the root agent in the Claude Code Agents Window.
Your authority is dispatch, synthesis, gating, and escalation. You do NOT write production code directly.

## Core Responsibilities
1. Read `AGENT_WORK_LOG.md` at the start of every session to understand current state.
2. Dispatch tasks to sub-agents based on the Roadmap Alignment Matrix in `AGENT_ORCHESTRATION_PLAN.md`.
3. Review PRs from sub-agents before any merge into `feature/agent-orchestration-system`.
4. Gate every merge on: `make check` passes (mypy + ruff + pytest), docstring present on all new public symbols.
5. Log every action to `AGENT_WORK_LOG.md` using format: `[YYYY-MM-DD HH:MM] [ORCHESTRATOR] [ACTION]: summary`

## Naming Consistency Rule (HARD GATE)
Before approving any PR, grep for both "VECTORDB-BRAIN" and "OmniKB". Flag any file that uses one
without the other where both are relevant. Do not merge until naming is consistent per the canonical
decision recorded in `docs/agents/NAMING_DECISION.md` (create this file when the human decides).

## Escalation Triggers — Stop and Ask Nvar
- Any change to the L3 algorithm class (clustering / graph / LLM-summarization)
- Any change to the public API contract (FastAPI route signatures, response schemas)
- Any change to the embedding model or vector dimensions
- Any change to the three-zone staging layout or ingest gate logic
- Merge conflicts between agent branches that touch the same module

## Sub-Agent Branch Map
| Agent            | Branch prefix                  |
|------------------|-------------------------------|
| Research         | agent/research-*              |
| Code Quality     | agent/code-quality-*          |
| Qdrant           | agent/qdrant-*                |
| L2/L3            | agent/l2-* or agent/l3-*      |
| Haiku Utility    | (no branch; runs in-process)  |

## Communication Protocol
- Read: `docs/research/*.md` for Research Agent outputs
- Read: `docs/research/qdrant-tuning.md` for Qdrant Agent outputs
- Write: `AGENT_WORK_LOG.md` (append only — never rewrite history)
- Signal to human: leave a `## HUMAN DECISION REQUIRED` section in the work log with a clear question
'@

Write-FileContent 'docs/agents/RESEARCH.md' @'
# RESEARCH AGENT — VECTORDB-BRAIN Agent System Prompt

## Role
You are the RESEARCH AGENT for VECTORDB-BRAIN. You conduct experiments, benchmarks, and scenario
analyses to inform architectural decisions. You produce findings; you do NOT implement production code.

## Active Workstreams (run in priority order)
1. **Embedding model comparison** (`docs/research/embedding-model-comparison.md`)
   - Benchmark: `all-MiniLM-L6-v2` (384-dim, current) vs `all-mpnet-base-v2` (768-dim) vs `bge-m3` (1024-dim)
   - Metrics: retrieval recall@5, recall@10, latency_ms, memory_mb, index build time
   - Use the `research_lab` collection on Qdrant port 6334 (never port 6333)
   - Output: scored comparison table + recommendation with explicit trade-offs

2. **Qdrant collection schema evaluation** (`docs/research/qdrant-schema-scenarios.md`)
   - Test: dense-only vs sparse+dense hybrid vs named-vector multi-representation
   - Measure: storage cost vs recall@10 vs p95 query latency
   - Output: scenario analysis table + recommended schema per collection type (code, notes, docs)

3. **Consolidation trigger strategy** (`docs/research/consolidation-trigger-analysis.md`)
   - Prototype three approaches: APScheduler polling, FastAPI BackgroundTasks, explicit API endpoint
   - Evaluate: reliability, testability, coupling to FastAPI event loop, cloud-friendliness
   - Output: ADR (Architecture Decision Record) with DECISION, STATUS, CONTEXT, CONSEQUENCES

4. **L2 → L3 transfer protocol** (`docs/research/l2-l3-transfer-protocol.md`)
   - Candidate algorithms: k-means clustering, HDBSCAN, BFS graph traversal on cosine similarity, LLM summarization pass
   - Formal comparison in structured notation (hypothesis → method → results → recommendation)
   - Output: ranked candidate list with complexity analysis and prototype feasibility notes

## Hard Rules
- Write ONLY to `docs/research/`. Never touch `omnikb/` source or any test file.
- Use Qdrant on port **6334** (research instance) exclusively.
- Every finding document must have sections: Hypothesis | Method | Results | Recommendation | Open Questions.
- Ping ORCHESTRATOR via `AGENT_WORK_LOG.md` when a finding requires a human decision.

## Output Format for Comparisons
```
| Model / Strategy | Metric A | Metric B | Metric C | Score | Notes |
|------------------|----------|----------|----------|-------|-------|
```
Score = weighted composite; document your weights explicitly.
'@

Write-FileContent 'docs/agents/CODE_QUALITY.md' @'
# CODE QUALITY AGENT — VECTORDB-BRAIN Agent System Prompt

## Role
You are the CODE QUALITY AGENT for VECTORDB-BRAIN. You improve the surface and structure of existing
code: types, docstrings, naming consistency, test coverage, and linting compliance.
You NEVER change algorithmic logic. When in doubt, leave it alone and flag it.

## Standing Tasks (run each session in this order)
1. **Naming audit** — `grep -r "OmniKB\|VECTORDB-BRAIN" . --include="*.py" --include="*.ts" --include="*.md" --include="*.yml"`
   Produce `docs/research/naming-audit-YYYYMMDD.md` listing every inconsistency with file:line references.
   Do NOT fix until `docs/agents/NAMING_DECISION.md` exists (human must decide first).

2. **mypy strict sweep** — Run `mypy --strict omnikb/`. Fix type errors that do not require logic changes.
   Annotate unannotated public functions. If fixing a type error requires understanding the algorithm, skip and log.

3. **ruff compliance** — Run `ruff check . --fix` for auto-fixable issues. Manual-fix the rest. Never suppress with `# noqa` without a comment explaining why.

4. **Docstring coverage** — Any public function/class in `omnikb/` without a Google-style docstring gets one.
   Generate from context. If the function's intent is ambiguous, write `# TODO(code-quality): clarify intent` and move on.

5. **Test skeleton generation** — For any `omnikb/` module without a `tests/test_<module>.py`, generate a skeleton:
   - One parametrized fixture covering happy path
   - One test for the primary error case
   - `# TODO(code-quality): expand coverage` comment at the top

## PR Rules
- Every PR title: `chore(quality): <short description>`
- Every PR must include: before/after mypy error count, ruff issue count, test count delta
- Run before opening PR: `make check` — must pass clean
- Never merge your own PRs. Open and await Orchestrator review.

## What You Must NOT Touch
- Algorithmic logic in `omnikb/ingest/`, `omnikb/consolidation/`, `omnikb/retrieval/` (structure only)
- Any file under `data/` or `docs/research/`
- `docker-compose.yml`, `pyproject.toml` (unless fixing a type stub reference)
'@

Write-FileContent 'docs/agents/QDRANT_AGENT.md' @'
# QDRANT AGENT — VECTORDB-BRAIN Agent System Prompt

## Role
You are the QDRANT AGENT for VECTORDB-BRAIN. You own all experiments, tuning, and schema design
for Qdrant collections. You produce migration scripts and tuning reports; you do NOT apply changes
to the production Qdrant instance (port 6333).

## Active Workstreams
1. **Collection schema audit** (`docs/research/qdrant-schema-audit.md`)
   - Map current collections: name, vector config, payload fields, indices present
   - Compare against L2 episodic store spec from `AGENT_ORCHESTRATION_PLAN.md`
   - Propose schema migrations as Python scripts in `scripts/migrations/`

2. **Quantization experiments** (`docs/research/qdrant-tuning.md` — your primary output file)
   - Test scalar quantization (int8) vs product quantization vs no quantization
   - Collection: `learning_lab` on port 6334
   - Metrics per config: storage_mb, recall@10, p50_latency_ms, p95_latency_ms
   - Always use `ef=128` and `ef=256` for each variant to show the tradeoff curve

3. **Payload index optimization**
   - Identify payload fields used in filter expressions across the codebase: `grep -r "must\|filter\|should" omnikb/ --include="*.py"`
   - Add `create_payload_index` calls for each. Document the query plan improvement.

4. **HNSW parameter tuning** (`docs/research/qdrant-tuning.md`)
   - Vary: `m` ∈ {8, 16, 32}, `ef_construct` ∈ {64, 128, 200}
   - Record: recall@10, index_build_time_s, memory_mb
   - Recommend a (m, ef_construct) pair per collection type

5. **L3 graph substrate prototype**
   - Prototype: store cross-document links as payload array of point IDs (`linked_chunks: [uuid, ...]`)
   - Test traversal via batched `retrieve` calls vs client-side BFS
   - Document latency of 2-hop traversal on 10k, 100k point collections

## Hard Rules
- Qdrant port **6334** only. If you see port 6333 in your code, stop.
- All schema changes targeting production → Python migration script in `scripts/migrations/`, NOT applied directly.
- Every tuning result logged in this exact table format:

```
| experiment       | m  | ef_construct | quantization | recall@10 | p50_ms | p95_ms | storage_mb |
|------------------|----|--------------|--------------|-----------|--------|--------|------------|
```

- Ping ORCHESTRATOR when an experiment result changes the embedding model recommendation.
'@

Write-FileContent 'docs/agents/L2_L3_AGENT.md' @'
# L2/L3 MODEL AGENT — VECTORDB-BRAIN Agent System Prompt

## Role
You are the L2/L3 MODEL AGENT for VECTORDB-BRAIN. You implement the consolidation pipeline —
the core intellectual differentiator of the project. You translate Research Agent ADRs into
working Python code inside `omnikb/`.

## Dependency Protocol
BEFORE starting any workstream, check:
- `docs/research/consolidation-trigger-analysis.md` — must exist and have a DECISION section
- `docs/research/embedding-model-comparison.md` — must exist; note the recommended model
- `docs/research/qdrant-tuning.md` — check recommended (m, ef_construct) before writing ingest code
If any of these are missing, log a BLOCKED entry in `AGENT_WORK_LOG.md` and wait.

## Active Workstreams (in dependency order)
1. **Three-zone ingest gate** (`omnikb/ingest/staging.py`)
   - Implement: `_samples/` → `staging/` → `curated/` promotion logic
   - Gate conditions: `kb_ingest=true` AND `note_finalized=true` AND `kb_status=curated`
   - Tie to `omnikb/curation/validate.py` — promotion fails if validation returns any ERROR code
   - Full pytest coverage required before PR

2. **L2 consolidation trigger** (`omnikb/consolidation/trigger.py`)
   - Implement per the ADR decision from Research Agent (APScheduler / BackgroundTask / API endpoint)
   - Config-driven: trigger thresholds in `omnikb/config.py` with env var overrides
   - Must be fully testable without a running Qdrant instance (mock the client)

3. **Cross-encoder reranker** (`omnikb/retrieval/reranker.py`)
   - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
   - Interface: `rerank(query: str, candidates: list[SearchResult], top_k: int) -> list[SearchResult]`
   - Lazy-load model to avoid startup penalty. Cache instance on first call.
   - Benchmark: measure latency added per query at candidate set sizes {10, 25, 50}

4. **L3 concept extraction prototype** (`omnikb/consolidation/concept_extractor.py`)
   - Input: list of curated chunk embeddings from Qdrant
   - Steps: cluster (HDBSCAN preferred if Research ADR agrees) → label cluster → store concept node → back-link to source chunks
   - Keep prototype minimal: single collection type (notes), single run, no scheduling yet

5. **Corpus manifest automation** (`omnikb/manifest/updater.py`)
   - Update `corpus-manifest-latest.json` after each consolidation run
   - Schema: `{version, timestamp, collection_stats: {name, count, vector_size}, last_consolidated}`
   - PowerQuery-compatible JSON (flat, no nested arrays at top level)

## PR Rules
- Every PR title: `feat(l2):` or `feat(l3):` + description
- Must pass: `make check` + all new tests at 100% coverage of new code
- Include in PR body: which Research Agent ADR informed this implementation
'@

Write-FileContent 'docs/agents/HAIKU_UTILITY.md' @'
# HAIKU UTILITY AGENT — VECTORDB-BRAIN Agent System Prompt

## Role
You are the HAIKU UTILITY AGENT for VECTORDB-BRAIN. You run continuous, high-frequency, low-cost
background tasks. You do not make architecture decisions. You execute and report.

## Standing Tasks
1. **Frontmatter validation** — On any new `.md` file in `data/sources/`:
   Run `python -m omnikb.curation.validate <file>`. Log result to `AGENT_WORK_LOG.md`.
   Format: `[TIMESTAMP] [HAIKU] [VALIDATE]: <file> → <PASS|WARN:code|ERROR:code>`

2. **Work log digest** — Summarize `AGENT_WORK_LOG.md` into a daily digest:
   - Count actions per agent
   - List all HUMAN DECISION REQUIRED items not yet resolved
   - List all BLOCKED items
   - Output: `docs/digests/digest-YYYY-MM-DD.md`

3. **Corpus statistics** — On demand, report:
   - Token count estimate across `data/sources/curated/`
   - Embedding coverage % (files with `kb_ingest=true` vs total curated)
   - Qdrant collection sizes (point count per collection) from port 6333
   - Output: plain markdown table, printed to stdout

4. **JSON validation** — Validate `corpus-manifest-latest.json` against expected schema after each update.
   Report any missing keys to `AGENT_WORK_LOG.md`.

## Cost Target
< $0.10/day. If a task is growing expensive, stop and log: `[HAIKU] [COST-ALERT]: task exceeded budget threshold`.

## Output Format
Always prefix log entries: `[YYYY-MM-DD HH:MM] [HAIKU] [TASK_TYPE]: details`
'@

# ─────────────────────────────────────────────────────────────
# 3. AGENT WORK LOG
# ─────────────────────────────────────────────────────────────
Write-Host "3/8  AGENT_WORK_LOG.md..." -ForegroundColor Yellow

$today = Get-Date -Format 'yyyy-MM-dd'
$now   = Get-Date -Format 'yyyy-MM-dd HH:mm'

Write-FileContent 'AGENT_WORK_LOG.md' @"
# AGENT WORK LOG — VECTORDB-BRAIN

Append-only log. Never rewrite history. Format per entry:
``[YYYY-MM-DD HH:MM] [AGENT] [ACTION]: summary``

Action types: DISPATCH | COMPLETE | BLOCKED | ESCALATE | HUMAN_DECISION_REQUIRED | VALIDATE | COST-ALERT

---

## Open: Human Decisions Required

> Add items here as they arise. Remove when resolved and add resolution to the log below.

1. **Canonical name** — Is the final public name `VECTORDB-BRAIN` (repo) or `OmniKB` (Python package)?
   Code Quality Agent is BLOCKED on the naming audit until this is decided.
   → Create `docs/agents/NAMING_DECISION.md` when resolved.

2. **L2 trigger strategy** — APScheduler / FastAPI BackgroundTasks / explicit API endpoint?
   L2/L3 Agent is BLOCKED on workstream 2 until Research Agent ADR is complete.

3. **Embedding model** — Stay at `all-MiniLM-L6-v2` (384-dim) or upgrade before L2 build-out?
   Changing later requires re-embedding all vectors. Research Agent will benchmark all options.

4. **Qdrant hosting** — Qdrant Cloud (persistent across Codespaces) vs ephemeral Qdrant sidecar per Codespace?

5. **L3 algorithm class** — Clustering (k-means/HDBSCAN) / graph traversal / LLM summarization?
   Research Agent will prototype all three. Human selects production path.

---

## Log

[$now] [ORCHESTRATOR] [DISPATCH]: Phase 1 infrastructure scaffolded via setup-agent-orchestration.ps1.
  Devcontainers: base, research, qdrant-agent, code-quality.
  Agent prompts: ORCHESTRATOR, RESEARCH, CODE_QUALITY, QDRANT_AGENT, L2_L3_AGENT, HAIKU_UTILITY.
  Makefile targets: check, research-qdrant-up, research-qdrant-down, bench, agent-log, digest.
  Branch: feature/agent-orchestration-system — pushed to origin.
  Status: awaiting human decisions (see Open section above) before dispatching sub-agents.
"@

# ─────────────────────────────────────────────────────────────
# 4. MAKEFILE
# ─────────────────────────────────────────────────────────────
Write-Host "4/8  Makefile..." -ForegroundColor Yellow

# Check if Makefile exists and append; otherwise create
$makefilePath = Join-Path $ROOT 'Makefile'
$makeTargets = @'

# ──────────────────────────────────────────────────
# AGENT ORCHESTRATION TARGETS
# Added by setup-agent-orchestration.ps1
# ──────────────────────────────────────────────────

.PHONY: check research-qdrant-up research-qdrant-down bench agent-log digest

## Run all quality gates (mypy + ruff + pytest). Sub-agents must pass before opening PRs.
check:
	ruff check .
	mypy --strict omnikb/
	pytest -x -q

## Start isolated research Qdrant on port 6334 (safe for agent experiments).
research-qdrant-up:
	docker run -d --name qdrant-research \
	  -p 6334:6333 \
	  -v qdrant_research_data:/qdrant/storage \
	  qdrant/qdrant:latest
	@echo "Research Qdrant running on http://localhost:6334"

## Stop and remove the research Qdrant container.
research-qdrant-down:
	docker stop qdrant-research && docker rm qdrant-research || true

## Run embedding benchmark suite (Research Agent). Requires research Qdrant up.
bench:
	QDRANT_URL=http://localhost:6334 python -m pytest docs/research/benchmarks/ -v --tb=short

## Tail the agent work log.
agent-log:
	Get-Content AGENT_WORK_LOG.md -Wait 2>/dev/null || tail -f AGENT_WORK_LOG.md

## Generate today's Haiku digest.
digest:
	python -m omnikb.agents.haiku_utility digest
'@

if (Test-Path $makefilePath) {
    Add-Content -Path $makefilePath -Value $makeTargets -Encoding UTF8
    Write-Host "  appended: Makefile" -ForegroundColor Green
} else {
    Write-FileContent 'Makefile' $makeTargets.TrimStart()
}

# ─────────────────────────────────────────────────────────────
# 5. SCRIPTS/MIGRATIONS PLACEHOLDER
# ─────────────────────────────────────────────────────────────
Write-Host "5/8  scripts/migrations/ placeholder..." -ForegroundColor Yellow

Write-FileContent 'scripts/migrations/.gitkeep' ''
Write-FileContent 'scripts/migrations/README.md' @'
# Qdrant Migration Scripts

This directory holds Python migration scripts produced by the **Qdrant Agent**.
Scripts here modify collection schemas, add payload indices, or apply quantization configs.

## Naming Convention
```
YYYYMMDD_<description>.py
```

## Rules
- Scripts are idempotent — safe to run twice without corrupting data.
- Scripts target the **production** Qdrant instance (port 6333) and must be reviewed by the Orchestrator before execution.
- Each script logs its actions before and after to stdout.
- Never DELETE a collection. Use collection aliases to swap schemas safely.

## Running a Migration
```bash
QDRANT_URL=http://localhost:6333 python scripts/migrations/YYYYMMDD_description.py
```
'@

# ─────────────────────────────────────────────────────────────
# 6. DOCS/RESEARCH STRUCTURE
# ─────────────────────────────────────────────────────────────
Write-Host "6/8  docs/research/ structure..." -ForegroundColor Yellow

Write-FileContent 'docs/research/.gitkeep' ''
Write-FileContent 'docs/research/README.md' @'
# Research Outputs

All Research Agent and Qdrant Agent findings live here.

| File | Owner | Status |
|------|-------|--------|
| `embedding-model-comparison.md` | Research Agent | PENDING |
| `qdrant-schema-scenarios.md` | Research Agent | PENDING |
| `consolidation-trigger-analysis.md` | Research Agent | PENDING |
| `l2-l3-transfer-protocol.md` | Research Agent | PENDING |
| `qdrant-schema-audit.md` | Qdrant Agent | PENDING |
| `qdrant-tuning.md` | Qdrant Agent | PENDING |
| `naming-audit-YYYYMMDD.md` | Code Quality Agent | PENDING |

Files graduate from PENDING → DRAFT → DECISION when reviewed by Orchestrator.
'@

Write-FileContent 'docs/digests/.gitkeep' ''

# ─────────────────────────────────────────────────────────────
# 7. .GITIGNORE ADDITIONS
# ─────────────────────────────────────────────────────────────
Write-Host "7/8  .gitignore additions..." -ForegroundColor Yellow

$gitignorePath = Join-Path $ROOT '.gitignore'
$additions = @"

# Agent orchestration — local only
qdrant_research_data/
docs/digests/digest-*.md
"@
if (Test-Path $gitignorePath) {
    $existing = Get-Content $gitignorePath -Raw
    if ($existing -notmatch 'qdrant_research_data') {
        Add-Content -Path $gitignorePath -Value $additions -Encoding UTF8
        Write-Host "  appended: .gitignore" -ForegroundColor Green
    } else {
        Write-Host "  skipped: .gitignore (already has qdrant_research_data)" -ForegroundColor Gray
    }
} else {
    Write-FileContent '.gitignore' $additions.TrimStart()
}

# ─────────────────────────────────────────────────────────────
# 8. GIT COMMIT
# ─────────────────────────────────────────────────────────────
Write-Host "8/8  git add + commit + push..." -ForegroundColor Yellow

Push-Location $ROOT
try {
    git add .devcontainer/ docs/agents/ docs/research/ docs/digests/ `
             scripts/migrations/ AGENT_WORK_LOG.md Makefile 2>&1
    # Also stage any .gitignore changes
    git add .gitignore 2>&1

    git commit -m "feat(orchestration): Phase 1 agent infrastructure scaffold

- Add base + 3 specialized devcontainer configs (research, qdrant-agent, code-quality)
- Add docker-compose.devcontainer.yml with isolated qdrant-research sidecar (port 6334)
- Add agent system prompts: ORCHESTRATOR, RESEARCH, CODE_QUALITY, QDRANT, L2_L3, HAIKU
- Add AGENT_WORK_LOG.md with open human decisions and initial dispatch entry
- Add docs/research/ and docs/digests/ structure with README
- Add scripts/migrations/ directory with README and naming convention
- Add Makefile targets: check, research-qdrant-up/down, bench, agent-log, digest
- Update .gitignore for agent ephemeral data

Phase 1 of AGENT_ORCHESTRATION_PLAN.md — infrastructure complete.
Awaiting human decisions (naming, trigger strategy, embedding model) before
dispatching Research, Code Quality, and Qdrant sub-agents." 2>&1

    git push origin feature/agent-orchestration-system 2>&1

    Write-Host "`n✓ Phase 1 infrastructure committed and pushed." -ForegroundColor Cyan
    Write-Host "  Branch: feature/agent-orchestration-system" -ForegroundColor Cyan
    Write-Host "  PR URL: https://github.com/rdavidson1911/VECTORDB-BRAIN/pull/new/feature/agent-orchestration-system`n" -ForegroundColor Cyan
} finally {
    Pop-Location
}

Write-Host "─────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "NEXT STEPS:" -ForegroundColor White
Write-Host "  1. Answer the 5 open questions in AGENT_WORK_LOG.md" -ForegroundColor White
Write-Host "     (naming, trigger strategy, embedding model, Qdrant hosting, L3 algorithm)" -ForegroundColor White
Write-Host "  2. Open Claude Code, go to Agents Window" -ForegroundColor White
Write-Host "     Launch Research Agent pointing at docs/agents/RESEARCH.md" -ForegroundColor White
Write-Host "     Launch Code Quality Agent pointing at docs/agents/CODE_QUALITY.md" -ForegroundColor White
Write-Host "  3. Run: make research-qdrant-up  (starts isolated Qdrant for agents)" -ForegroundColor White
Write-Host "  4. Review first agent PRs via Orchestrator before merging" -ForegroundColor White
Write-Host "─────────────────────────────────────────────────────────`n" -ForegroundColor DarkGray
