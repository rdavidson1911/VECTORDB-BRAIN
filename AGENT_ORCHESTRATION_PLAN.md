# VECTORDB-BRAIN — Multi-Agent Orchestration System Plan

**Branch:** `feature/agent-orchestration-system`
**Carved from:** `main` (most current commit)
**Date:** 2026-06-02
**Author:** Nvar / rdavidson1911

---

## 0. Branch Creation — Run These Commands First

```bash
# In your I:\VECTORDB-BRAIN terminal
cd I:\VECTORDB-BRAIN

# Pull latest main to ensure you're on the freshest base
git checkout main
git pull origin main

# Create and switch to the orchestration branch
git checkout -b feature/agent-orchestration-system

# Push the branch upstream so Codespaces can see it
git push -u origin feature/agent-orchestration-system
```

---

## 1. North Star Alignment

VECTORDB-BRAIN's goal is a **layered episodic-memory RAG architecture** where retrieval is governed by consolidation events rather than raw search. The multi-agent system must serve that goal directly — not just accelerate development in general, but specifically advance:

| Layer | Description |
|---|---|
| **L1 — Working Memory** | In-flight ingest, raw embedding, staging buffer |
| **L2 — Episodic Store** | Qdrant collections with structured metadata, consolidation-gated |
| **L3 — Semantic Consolidation** | Cross-document relationship graph, concept-level abstraction |
| **API/UI Layer** | FastAPI + React/Vite serving retrieval and curation UI |
| **Ingest Gate** | Frontmatter validation, three-zone staging, quality enforcement |

Every agent defined below maps to at least one of these layers.

---

## 2. Agent Roster — Specialized Roles

### 2.1 ORCHESTRATOR (Claude Opus 4.6)
**Responsibility:** Dispatch, synthesis, conflict resolution, roadmap gating.
**Does NOT write code directly.** Reads PR diffs, routes tasks to sub-agents, aggregates findings, makes architecture decisions. Runs in the Claude Code Agents Window as the root agent.

**System prompt key directives:**
- Maintain a `AGENT_WORK_LOG.md` in the repo root tracking all agent actions per session
- Gate any sub-agent PR merge on a checklist: tests pass, mypy clean, no naming regressions (VECTORDB-BRAIN / OmniKB consistency), docstring present
- Escalate to human (Nvar) on any decision touching the L3 consolidation model or public API contract

**Model:** `claude-opus-4-6`

---

### 2.2 RESEARCH AGENT (Claude Opus 4.6)
**Responsibility:** Architecture research, scenario analysis, and benchmarking to determine the optimal structure of VECTORDB-BRAIN.

**Active research workstreams:**
1. **Embedding model comparison** — Benchmark `all-MiniLM-L6-v2` (384-dim, current) vs `all-mpnet-base-v2` (768-dim) vs `bge-m3` (1024-dim) on VECTORDB-BRAIN's retrieval quality metrics. Output: scored comparison table + recommendation.
2. **Qdrant collection schema evaluation** — Test sparse vs dense vs hybrid vector strategies in `learning_lab`. Produce scenario analysis: storage cost vs retrieval quality vs latency triangle.
3. **Consolidation event architecture** — Research event-driven vs polling vs webhook consolidation trigger strategies. Align with FastAPI event loop constraints.
4. **L2 → L3 transfer protocol** — Prototype candidate algorithms for the episodic-to-semantic consolidation pass (clustering, graph traversal, summarization pipelines). Produce a formal comparison in Knuth-style structured notation.

**Output artifacts:** Research reports in `docs/research/`, each with a structured Decision Record (ADR format).

**Runs in:** GitHub Codespaces devcontainer, isolated from production Qdrant. Uses a dedicated `research_lab` collection.

**Model:** `claude-opus-4-6`

---

### 2.3 CODE QUALITY AGENT (Claude Sonnet 4.6)
**Responsibility:** Continuous codebase hygiene — linting, refactoring, dead code elimination, type annotation coverage, and naming consistency enforcement.

**Standing tasks (run in parallel loops):**
1. **Naming audit** — Scan all Python, TypeScript, markdown, and YAML files for the VECTORDB-BRAIN / OmniKB inconsistency. Produce a diff resolving the canonical name per the decision on file.
2. **Type annotation sweep** — Fill `mypy --strict` gaps across `omnikb/`. Target 100% typed public API surface.
3. **Ruff + black compliance** — Ensure all new files introduced by other agents pass pre-commit hooks before committing.
4. **Docstring coverage** — Add Google-style docstrings to all public functions/classes missing them. Auto-generate from context, flag ambiguous ones for human review.
5. **Test skeleton generation** — For any new module without a `test_*.py` counterpart, generate a pytest skeleton with parametrized fixtures and TODO stubs.

**Constraint:** This agent never merges — it only opens PRs tagged `chore/code-quality` for Orchestrator review.

**Model:** `claude-sonnet-4-6`

---

### 2.4 QDRANT AGENT (Claude Sonnet 4.6)
**Responsibility:** Knowledge graph optimization — collection schema, indexing strategy, payload indexing, quantization, and retrieval pipeline tuning.

**Active workstreams:**
1. **Collection schema audit** — Review existing collections against the L2 episodic store spec. Propose schema migrations (payload fields, sparse indices, named vectors).
2. **Quantization experiments** — Test scalar quantization (int8) vs product quantization on the `learning_lab` collection. Measure memory reduction vs recall tradeoff at `ef=128` and `ef=256`.
3. **Payload index optimization** — Identify which metadata fields are used in filter expressions and add appropriate payload indices. Profile query plans before/after.
4. **HNSW parameter tuning** — Systematically vary `m` and `ef_construct` parameters and record recall@10 vs build time. Produce a tuning table for each collection type (code, notes, documents).
5. **Graph relationship layer** — Prototype Qdrant-native approach to storing cross-document links (via payload arrays of point IDs) as the L3 semantic graph substrate.

**Runs in:** Dedicated Codespace with Qdrant sidecar container. Never touches production collection.

**Model:** `claude-sonnet-4-6`

---

### 2.5 L2/L3 MODEL AGENT (Claude Sonnet 4.6)
**Responsibility:** Implement and iterate the consolidation pipeline — the core intellectual differentiator of VECTORDB-BRAIN.

**Active workstreams:**
1. **L2 consolidation trigger** — Implement the event-driven trigger in FastAPI using a background task queue (APScheduler or Celery, TBD by Research Agent). Gated on: document count threshold, time-since-last-consolidation, or explicit API call.
2. **L2 → staging buffer protocol** — Implement the three-zone ingest gate in code: `_samples/` → `staging/` → `curated/` promotion logic tied to frontmatter validation.
3. **L3 concept extraction pipeline** — Prototype: extract key concepts from curated chunks via sentence-transformers → cluster → build concept node → link back to source chunks in Qdrant payload.
4. **Retrieval reranker** — Implement a cross-encoder reranking step on top of L2 vector search to improve precision. Candidate models: `cross-encoder/ms-marco-MiniLM-L-6-v2`.
5. **Consolidation manifest** — Design and implement `corpus-manifest-latest.json` update logic so Excel/PowerQuery integration stays current after each consolidation run.

**Model:** `claude-sonnet-4-6`

---

### 2.6 HAIKU UTILITY AGENT (Claude Haiku 4.5)
**Responsibility:** High-frequency, low-cost utility tasks — file scanning, frontmatter parsing, JSON validation, log summarization, search-index updates.

**Standing tasks:**
- Parse and validate frontmatter on all `.md` files in `data/sources/` on commit
- Summarize AGENT_WORK_LOG.md into a daily digest
- Run the eight-code frontmatter validation (`omnikb/curation/validate.py`) on new staging files
- Generate corpus statistics (token counts, embedding coverage %, collection sizes) on demand

**Model:** `claude-haiku-4-5-20251001`
**Cost target:** < $0.10/day for continuous background scanning.

---

## 3. Parallel Execution Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLAUDE CODE                          │
│                  Agents Window                          │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │          ORCHESTRATOR (Opus 4.6)                  │  │
│  │   - Reads AGENT_WORK_LOG.md                       │  │
│  │   - Routes tasks, reviews PRs, gates merges       │  │
│  │   - Escalates to Nvar on L3 / API decisions       │  │
│  └──────┬───────────┬───────────┬───────────┬───────┘  │
│         │           │           │           │           │
│   ┌─────▼──┐  ┌─────▼──┐  ┌────▼───┐  ┌───▼────┐      │
│   │RESEARCH│  │  CODE  │  │QDRANT  │  │ L2/L3  │      │
│   │ Opus   │  │QUALITY │  │ Agent  │  │ Agent  │      │
│   │        │  │Sonnet  │  │Sonnet  │  │Sonnet  │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│                                                         │
│   ┌──────────────────────────────────────────────┐     │
│   │         HAIKU UTILITY (continuous)            │     │
│   └──────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘

Communication Protocol:
  - Shared: AGENT_WORK_LOG.md (append-only, per-session)
  - Handoffs: feature sub-branches → PR → Orchestrator review
  - Research outputs: docs/research/*.md → read by L2/L3 Agent
  - Qdrant Agent findings: docs/research/qdrant-tuning.md → read by L2/L3
```

### Branch Strategy for Parallel Agents

```
main
└── feature/agent-orchestration-system    ← YOU ARE HERE
    ├── agent/research-embedding-bench     ← Research Agent
    ├── agent/code-quality-naming-audit    ← Code Quality Agent
    ├── agent/qdrant-quantization-exp      ← Qdrant Agent
    └── agent/l2-consolidation-trigger     ← L2/L3 Agent
```

Each agent works in its own `agent/*` sub-branch. Orchestrator cherry-picks or merges completed work into `feature/agent-orchestration-system` after review.

---

## 4. Cloud Devcontainer Architecture

### 4.1 Base `.devcontainer/devcontainer.json`

```jsonc
// .devcontainer/devcontainer.json
{
  "name": "VECTORDB-BRAIN Dev",
  "dockerComposeFile": ["../docker-compose.yml", "docker-compose.devcontainer.yml"],
  "service": "api",
  "workspaceFolder": "/workspace",
  "features": {
    "ghcr.io/devcontainers/features/python:1": { "version": "3.11" },
    "ghcr.io/devcontainers/features/node:1": { "version": "20" },
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "postCreateCommand": "pip install -e '.[dev]' --break-system-packages && npm install --prefix frontend",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.mypy-type-checker",
        "charliermarsh.ruff",
        "bradlc.vscode-tailwindcss",
        "GitHub.copilot"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "editor.formatOnSave": true,
        "[python]": { "editor.defaultFormatter": "charliermarsh.ruff" }
      }
    }
  },
  "forwardPorts": [8000, 5173, 6333],
  "portsAttributes": {
    "8000": { "label": "FastAPI", "onAutoForward": "notify" },
    "5173": { "label": "React UI", "onAutoForward": "openBrowser" },
    "6333": { "label": "Qdrant", "onAutoForward": "silent" }
  }
}
```

### 4.2 Specialized Agent Devcontainers

Create variant configs per agent role:

```
.devcontainer/
├── devcontainer.json           ← default (full stack)
├── research/
│   └── devcontainer.json       ← Python + Jupyter + sentence-transformers + benchmarking deps
├── qdrant-agent/
│   └── devcontainer.json       ← Python + Qdrant client + isolated Qdrant sidecar
└── code-quality/
    └── devcontainer.json       ← Python + ruff + mypy + bandit only (lightweight)
```

The research and Qdrant agent containers use a **separate Qdrant instance** (different port, ephemeral volume) so no experiment can corrupt the main knowledge store.

### 4.3 docker-compose.devcontainer.yml (overlay)

```yaml
# .devcontainer/docker-compose.devcontainer.yml
version: "3.9"
services:
  qdrant-research:
    image: qdrant/qdrant:latest
    ports:
      - "6334:6333"      # research Qdrant on different host port
    volumes:
      - qdrant_research_data:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO

volumes:
  qdrant_research_data:
```

---

## 5. Agent CLAUDE.md Configuration

Each agent requires a scoped `CLAUDE.md` (or system prompt file) that constrains its authority:

### `docs/agents/ORCHESTRATOR.md`
```markdown
You are the ORCHESTRATOR for VECTORDB-BRAIN.
- You dispatch tasks and review PRs from sub-agents.
- You NEVER write production code directly.
- Before approving any merge: run `make check` (mypy + ruff + pytest).
- Check that no file introduces the name "OmniKB" without also aliasing "VECTORDB-BRAIN" consistently.
- Log every action to AGENT_WORK_LOG.md in format: `[YYYY-MM-DD HH:MM] [AGENT] [ACTION]: summary`
- Escalate to human on: L3 algorithm selection, public API contract changes, embedding model changes.
```

### `docs/agents/RESEARCH.md`
```markdown
You are the RESEARCH AGENT for VECTORDB-BRAIN.
- You conduct experiments, benchmarks, and scenario analyses.
- You write to docs/research/ only. Never touch omnikb/ source code directly.
- All findings must include: hypothesis, method, results table, recommendation.
- Use the research_lab Qdrant collection (port 6334) only.
- Structure recommendations as ADRs (Architecture Decision Records).
```

### `docs/agents/CODE_QUALITY.md`
```markdown
You are the CODE QUALITY AGENT for VECTORDB-BRAIN.
- You improve existing code: types, docstrings, naming, test coverage.
- You never change algorithmic logic — only surface/structure.
- Every PR you open must pass: ruff check ., mypy --strict omnikb/, pytest -x.
- Flag any file where VECTORDB-BRAIN / OmniKB naming is inconsistent.
- PR titles must start with: chore(quality):
```

### `docs/agents/QDRANT_AGENT.md`
```markdown
You are the QDRANT AGENT for VECTORDB-BRAIN.
- You optimize Qdrant collections, schemas, and indexing.
- You run all experiments against Qdrant on port 6334 (research instance).
- You document tuning results in docs/research/qdrant-tuning.md.
- Schema changes targeting production must be proposed as migration scripts, never applied directly.
- Your output format for tuning results: markdown table with columns: parameter | value | recall@10 | latency_ms | memory_mb
```

---

## 6. Communication Protocol Between Agents

| Channel | Format | Writer | Reader |
|---|---|---|---|
| `AGENT_WORK_LOG.md` | Timestamped append-only log | All agents | Orchestrator + Human |
| `docs/research/*.md` | ADR-format research docs | Research Agent | L2/L3 Agent, Orchestrator |
| `docs/research/qdrant-tuning.md` | Tuning parameter tables | Qdrant Agent | L2/L3 Agent, Orchestrator |
| Git PRs (agent/* branches) | Code diff + summary | Code Quality, L2/L3 Agents | Orchestrator |
| `corpus-manifest-latest.json` | JSON, updated after consolidation | L2/L3 Agent | Haiku Utility, Excel/PowerQuery |

---

## 7. Roadmap Alignment Matrix

| Roadmap Item | Primary Agent | Supporting Agent | Branch |
|---|---|---|---|
| Resolve VECTORDB-BRAIN/OmniKB naming | Code Quality | Orchestrator | `agent/code-quality-naming-audit` |
| Embedding model selection | Research | Qdrant | `agent/research-embedding-bench` |
| Frontmatter validation (pytest) | Code Quality | Haiku | `agent/code-quality-validation-tests` |
| L2 consolidation trigger | L2/L3 | Research | `agent/l2-consolidation-trigger` |
| Qdrant collection schema v2 | Qdrant | Research | `agent/qdrant-schema-v2` |
| Quantization experiments | Qdrant | Research | `agent/qdrant-quantization-exp` |
| L3 concept extraction prototype | L2/L3 | Research | `agent/l3-concept-extraction` |
| Cross-encoder reranker | L2/L3 | Qdrant | `agent/l2-reranker` |
| Corpus manifest automation | Haiku + L2/L3 | — | `agent/corpus-manifest-automation` |
| devcontainer setup | Code Quality | — | `agent/devcontainer-setup` |

---

## 8. Launch Sequence (Step-by-Step)

### Phase 1: Infrastructure (this branch) — Week 1
```
1. git checkout -b feature/agent-orchestration-system
2. Create .devcontainer/ base config
3. Create docs/agents/ CLAUDE.md files for each agent
4. Create AGENT_WORK_LOG.md template
5. Add Makefile targets: make check, make research-qdrant-up, make bench
6. Push and open PR to main for review
```

### Phase 2: Research Parallel Sprint — Week 2
```
Spin up in Agents Window simultaneously:
- Research Agent → agent/research-embedding-bench
- Qdrant Agent → agent/qdrant-quantization-exp
- Code Quality Agent → agent/code-quality-naming-audit
Orchestrator monitors AGENT_WORK_LOG.md, reviews PRs end of day
```

### Phase 3: Consolidation Build — Week 3–4
```
Research Agent findings feed L2/L3 Agent:
- L2/L3 Agent implements consolidation trigger (informed by Research ADRs)
- Qdrant Agent provides schema migration scripts
- Code Quality Agent covers test skeletons for new modules
```

### Phase 4: Integration — Week 5
```
Orchestrator merges agent/* branches into feature/agent-orchestration-system
Full integration test run
Human (Nvar) reviews, signs off on L3 algorithm selection
Merge feature branch to main
```

---

## 9. Model Selection Rationale

| Agent | Model | Reasoning |
|---|---|---|
| Orchestrator | Opus 4.6 | Highest context retention, best at multi-source synthesis and judgment calls |
| Research | Opus 4.6 | Complex multi-step reasoning, scenario analysis, formal algorithm notation |
| Code Quality | Sonnet 4.6 | Sufficient for linting/refactoring, high throughput, cost-effective |
| Qdrant | Sonnet 4.6 | Strong at structured parameter experimentation and table-format outputs |
| L2/L3 | Sonnet 4.6 | Implementation-focused, iterative, needs speed more than peak reasoning |
| Haiku Utility | Haiku 4.5 | Sub-second file scanning, JSON parsing, log summarization at near-zero cost |

---

## 10. Open Questions for Human Decision (Nvar)

These require your judgment before agents proceed:

1. **Canonical name decision**: Is the final public name `VECTORDB-BRAIN` (keeping the repo name) or `OmniKB` (Python package name)? Code Quality Agent is blocked on this.
2. **L2 trigger strategy**: Event-driven (APScheduler) vs explicit API call vs count threshold? Research Agent will prototype all three, but you choose the production path.
3. **Embedding model**: Stay at `all-MiniLM-L6-v2` (speed, 384-dim) or upgrade to higher-dim model before L2 is built out? Changing after L2 is costly (re-embed all vectors).
4. **Qdrant Cloud vs self-hosted**: For cloud Codespaces agents — do they hit a hosted Qdrant Cloud instance or run ephemeral Qdrant sidecars? Qdrant Cloud adds cost but enables persistence across Codespace sessions.
5. **L3 algorithm class**: Clustering-based (k-means / HDBSCAN), graph-traversal (BFS on semantic similarity), or LLM-summarization pass? Research Agent will produce benchmarks, but this is a foundational architectural choice you own.
