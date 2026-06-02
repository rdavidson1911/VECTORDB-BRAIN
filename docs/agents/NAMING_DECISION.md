# Human Architecture Decisions — VECTORDB-BRAIN

_These answers supersede Section 10 of AGENT_ORCHESTRATION_PLAN.md._
_Date decided: 2026-06-02_

---

## Decision 1: Canonical Name
**DECISION:** VECTORDB-BRAIN
**Rationale:** (one sentence — e.g. "repo name is already public, OmniKB becomes internal package alias only")

---

## Decision 3: Embedding Model
**DECISION:** Stay at all-MiniLM-L6-v2 (384-dim) until Research Agent benchmark completes
**Rationale:** Defer upgrade decision to Research Agent findings. L2 build proceeds with 384-dim assumption.

---

## Decision 2: L2 Trigger Strategy
**DECISION:** Start with explicit API endpoint (Option C), wrap with BackgroundTasks (Option B) later. Research Agent confirms before B is implemented.

---

## Decision 4: Qdrant Hosting (Codespaces)
**DECISION:** Ephemeral sidecars for Phase 2. Revisit for Phase 3 when persistent cross-session state is needed.

---

## Decision 5: L3 Algorithm Class
**DECISION:** HDBSCAN clustering first, then build graph within clusters. Research Agent prototypes and returns evidence before production implementation.
