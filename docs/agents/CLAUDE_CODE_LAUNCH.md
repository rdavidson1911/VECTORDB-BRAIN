# Claude Code Agents Window — Launch Manifest

Use this file when starting each sub-agent in **Claude Code → Agents Window**. Point each agent at its system prompt file and git worktree branch.

**Orchestrator prompt:** `docs/agents/ORCHESTRATOR.md`
**Integration branch:** `feature/agent-orchestration-system` (merge target: `main` after gates)
**Session close:** `docs/agents/reports/README.md`, `scripts/Invoke-AgentWorktreeTeardown.ps1`
**Quality gate before merge:** `make check` from repo root (or `python -m ruff check src tests`, `python -m mypy src`, `python -m pytest`)

---

## 1. Research Agent (Claude Opus 4.6)

| Field | Value |
|--------|--------|
| System prompt | `docs/agents/RESEARCH.md` |
| Git worktree | `I:\VECTORDB-BRAIN\.claude\worktrees\research-consolidation-trigger` |
| Branch to create/use | `agent/research-embedding-bench` |
| Qdrant | Port **6334** only (`make research-qdrant-up` from repo root) |

**First message to paste:**

```
You are the RESEARCH AGENT. Read docs/agents/RESEARCH.md and AGENT_WORK_LOG.md.
Work only under docs/research/. Priority: (1) embedding-model-comparison.md DRAFT with method + table skeleton,
(2) consolidation-trigger-analysis.md ADR with DECISION aligned to NAMING_DECISION.md (explicit API first).
Append progress to AGENT_WORK_LOG.md as [RESEARCH] COMPLETE or BLOCKED.
Do not edit src/omnikb/.
```

---

## 2. Code Quality Agent (Claude Sonnet 4.6)

| Field | Value |
|--------|--------|
| System prompt | `docs/agents/CODE_QUALITY.md` |
| Git worktree | `I:\VECTORDB-BRAIN\.claude\worktrees\code-quality-naming-audit` |
| Branch | `agent/code-quality-naming-audit` |

**First message to paste:**

```
You are the CODE QUALITY AGENT. Read docs/agents/CODE_QUALITY.md and docs/agents/NAMING_DECISION.md.
Task 1: Produce docs/research/naming-audit-20260604.md with file:line hits for OmniKB vs VECTORDB-BRAIN.
Then run ruff/mypy on src/omnikb — fix surface-only issues. PR title must start with chore(quality):.
Log to AGENT_WORK_LOG.md. Never change algorithmic logic.
```

---

## 3. Qdrant Agent (Claude Sonnet 4.6)

| Field | Value |
|--------|--------|
| System prompt | `docs/agents/QDRANT_AGENT.md` |
| Git worktree | `I:\VECTORDB-BRAIN\.claude\worktrees\qdrant-agent-workstreams` |
| Branch | `agent/qdrant-schema-v2` |

**First message to paste:**

```
You are the QDRANT AGENT. Read docs/agents/QDRANT_AGENT.md.
Deliver docs/research/qdrant-schema-audit.md (collections map vs L2 spec) and extend docs/research/qdrant-tuning.md with experiment table headers + planned rows.
Port 6334 only. Propose migrations under scripts/migrations/ as stubs, do not run against 6333.
Log [QDRANT] entries to AGENT_WORK_LOG.md.
```

---

## 4. L2/L3 Model Agent (Claude Sonnet 4.6)

| Field | Value |
|--------|--------|
| System prompt | `docs/agents/L2_L3_AGENT.md` |
| Git worktree | `I:\VECTORDB-BRAIN\.claude\worktrees\l2-l3-agent-blocked-log` |
| Branch | `agent/l2-consolidation-trigger` |

**First message to paste:**

```
You are the L2/L3 MODEL AGENT. Read docs/agents/L2_L3_AGENT.md and check docs/research/consolidation-trigger-analysis.md for DECISION.
If ADR missing: log BLOCKED in AGENT_WORK_LOG.md and write docs/research/l2-layer-schema-draft.md only (no omnikb/ code).
If ADR present: implement feat(l2) in small PRs with tests. Never touch ingest gate or embedding dims without ESCALATE.
```

---

## 5. Haiku Utility Agent (Claude Haiku 4.5)

| Field | Value |
|--------|--------|
| System prompt | `docs/agents/HAIKU_UTILITY.md` |
| Context | Main repo `I:\VECTORDB-BRAIN` (no separate branch) |

**First message to paste:**

```
You are the HAIKU UTILITY AGENT. Read docs/agents/HAIKU_UTILITY.md.
Run: digest of AGENT_WORK_LOG.md → docs/digests/digest-2026-06-04.md.
Validate one sample under data/sources/_samples/ if present. Append [HAIKU] lines to AGENT_WORK_LOG.md only.
Stay under cost budget; use COST-ALERT if needed.
```

---

## Orchestrator checklist (each review)

1. `git diff` scoped to agent branch prefix
2. `make check` green (or `poetry run` equivalents in CLAUDE.md)
3. Naming grep: public-facing docs use VECTORDB-BRAIN; OmniKB allowed as product alias per NAMING_DECISION.md
4. Append review line to `AGENT_WORK_LOG.md`
5. End of cycle: write `docs/agents/reports/ORCHESTRATION_SESSION_REPORT-YYYY-MM-DD.md`, run `.\scripts\Invoke-AgentWorktreeTeardown.ps1` then `-ForceRemove -AllowDirty -DeleteMergedBranches`
