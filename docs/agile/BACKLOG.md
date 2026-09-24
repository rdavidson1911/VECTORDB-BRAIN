# VECTORDB-BRAIN — Agile Backlog

Tracking home for epics, stories, and append-only time accounting.
Owned by the **agile-coordinator** agent. Orchestrator records architecture decisions in
`AGENT_WORK_LOG.md`; this file tracks delivery status only.

**Do not** invent progress or historical hours. **Do not** copy contents from `docs/internal/`.

---

## Epics

### E1 — Layered memory (L1 / L2 / L3)

North star: layered memory for Learn2EarnDAO as a curated source of truth.

| Layer | Meaning (canonical) | Status |
|---|---|---|
| **L1** | Unmodified source corpus | Gate + ingest done |
| **L2** | Interaction memory (`interactions.db`, boost fusion) | **In PR #20** (Design A / ADR 0002) |
| **L3** | Dreaming relationship edges | Edges + consolidation wired; UI surface in progress; HDBSCAN Phase 2 |

**L2 design fork — RESOLVED 2026-09-24:** Design A (interaction/boost/dreaming) won.
PR #11 closed. BM25 deferred into future fusion — not a second store/API.
ADRs: published `0001-l2-store-schema.md` (session artifacts, future); `0002` interaction/dreaming;
`0003` memory_tier.

### E2 — Cursor orchestration

Extend the existing Cursor control plane (thin `.cursor/agents/*` wrappers + `docs/agents/` heritage).
Roster: orchestrator, research, qdrant, l2-l3, frontend, code-writer, code-reviewer, agile-coordinator
(plus legacy code-quality alias).

| Status | Notes |
|---|---|
| In progress | Heritage docs + wrappers; backlog this file |

### E3 — Learn2EarnDAO source of truth

Curated Layer-1 corpus alignment for Learn2EarnDAO.

| Status | Notes |
|---|---|
| Planning note | Path only: `docs/internal/learn2earndao-layer1-source-of-truth.md` (do not copy contents here) |

---

## Stories

| ID | Epic | Story | Status |
|---|---|---|---|
| S1 | E1 | Reconcile L2 design: Design A vs PR #11 | **Done** — Design A / PR #20; #11 closed |
| S2 | E1 | Surface Layer 3 edges in API/UI (no HDBSCAN) | In progress on `feature/orchestration-and-layer3-edges` |
| S3 | E2 | Land Cursor roster (frontend, code-writer, code-reviewer, agile-coordinator) | In progress |
| S4 | E2 / arch | ADR mapping MMVM → hexagonal + three-tier (no MMVM invent) | Open |
| S5 | ops | Reconcile git remotes (`github` vs `origin`) | Decision needed — do not execute in agent sessions |
| S6 | E3 | Use Learn2EarnDAO L1 SoT note as planning input (path only) | Open |

---

## Time log

Append-only. Entry format (one row per entry):

`date | role | story id | minutes | note`

| date | role | story id | minutes | note |
|------|------|----------|---------|------|
| 2026-09-24 | orchestrator | S1 | not measured | Published PR #20; closed #11 |
| 2026-09-24 | orchestrator | S2/S3 | not measured | Layer 3 UI + agent roster commit |

<!-- FORMAT SAMPLE (not real time — do not treat as logged work):
| 2026-01-01 | agile-coordinator | S0 | 0 | format sample; not measured work |
-->
