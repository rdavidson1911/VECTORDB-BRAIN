# Consolidation Trigger Strategy (ADR)

**Status:** DRAFT — pending Orchestrator acceptance
**Owner:** Research Agent
**Consumers:** L2/L3 Agent, Orchestrator

## Hypothesis

L2 consolidation (episodic buffer → staging promotion → curated re-embed) needs a trigger mechanism that is reliable under FastAPI, testable without a second process, and deployable on Docker Desktop and future cloud without silent failure modes.

## Method

Evaluate three candidates against criteria: **reliability**, **testability**, **coupling to FastAPI event loop**, **cloud-friendliness** (horizontal scale, no duplicate runs), **operational visibility**.


| Approach                       | Mechanism                                            | Reliability                                       | Testability                | Event-loop coupling                         | Cloud-friendly                               |
| ------------------------------ | ---------------------------------------------------- | ------------------------------------------------- | -------------------------- | ------------------------------------------- | -------------------------------------------- |
| **A. APScheduler**             | In-process cron/interval jobs in API container       | Medium — lost on crash unless persisted job store | Medium — need clock mocks  | **High** — shares process with requests     | **Low** — duplicate schedulers per replica   |
| **B. FastAPI BackgroundTasks** | Fire-and-forget after ingest HTTP response           | Low — no retry, dies on worker restart            | High — httpx/pytest        | **High** — same worker                      | Medium — only for post-request work          |
| **C. Explicit API endpoint**   | `POST /consolidation/run` (+ optional internal auth) | **High** — operator or external cron invokes      | **High** — contract-tested | **Low** — short request, work in task queue | **High** — CronJob/K8s/EventBridge calls URL |


**Hybrid (recommended composition):**

- **C** as the *only* authoritative start of a consolidation run (idempotent job id).
- **B** only for *non-critical* follow-ups (e.g., refresh stats) — never for sole consolidation trigger.
- **A** optional later *only* if moved to a **single-worker sidecar** or Redis-backed scheduler (not in-process on N API replicas).

## Results

Structured scoring (1 = poor, 5 = excellent):


| Strategy                       | Reliability | Testability | Loop safety | Cloud | **Total** |
| ------------------------------ | ----------- | ----------- | ----------- | ----- | --------- |
| APScheduler (in API)           | 2           | 3           | 2           | 1     | **8**     |
| BackgroundTasks alone          | 2           | 4           | 2           | 2     | **10**    |
| Explicit API + external cron   | 5           | 5           | 4           | 5     | **19**    |
| Explicit API + Redis/RQ worker | 5           | 4           | 5           | 5     | **19**    |


**Failure modes documented:**

- **BackgroundTasks:** consolidation never runs if ingest path not hit; OOM kills task with no audit trail.
- **In-process APScheduler:** double consolidation when `docker compose scale api=2`; clock skew; hard to unit-test without flakiness.
- **Explicit endpoint:** requires operator discipline unless wired to GitHub Actions / Windows Task Scheduler / K8s CronJob.

## Recommendation

### ADR: L2 consolidation trigger


| Field            | Value                                                                                                                                                                                                                                                             |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DECISION**     | Use an **explicit `POST /consolidation/run` (or `/admin/consolidation`)** endpoint as the sole entry point for consolidation jobs. Trigger via external scheduler or manual operator action. Do **not** rely on BackgroundTasks or in-process APScheduler for v1. |
| **STATUS**       | PROPOSED                                                                                                                                                                                                                                                          |
| **CONTEXT**      | Layer 2 pipeline is not yet implemented; FastAPI already centralizes ingest/query; team runs Docker Desktop single replica today but Codespaces/cloud may scale API later.                                                                                        |
| **CONSEQUENCES** | (+) Clear audit log per run, easy pytest, cloud CronJob friendly. (−) Requires external cron or manual step until automation wired. Future worker queue (Celery/RQ) plugs into same endpoint contract.                                                            |


**Implementation hints for L2/L3 Agent (non-binding):**

- Request body: `{ "reason": "threshold|manual|schedule", "dry_run": true }`.
- Response: `202 Accepted` + `job_id`; poll `GET /consolidation/status/{job_id}`.
- Idempotency-Key header to prevent duplicate merges.

## Open Questions

- Minimum **document/chunk threshold** before auto-suggesting consolidation in UI (product, not infra).
- Whether consolidation runs **in API process** or **dedicated worker container** at scale (Research leans worker once Qdrant Cloud + multi-replica API).
