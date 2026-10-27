# ADR-0002: Mobile Thin Client (API-Only)

**Status:** ACCEPTED  
**Date:** 2026-10-27  
**Accepted:** 2026-10-27 (Operator via foundation plan 1A + 2B)  
**Deciders:** Operator, Orchestrator  
**Supersedes:** —

---

## Context

VECTORDB-BRAIN / OmniKB today runs as a local Docker stack: FastAPI + sentence-transformers embeddings + Qdrant + a React operator console. The product goal expands to web **and** Android clients that ingest personal curated data and query a private knowledge base.

Two competing shapes were considered:

1. **Thin client** — phone/browser talks only to FastAPI; embeddings and Qdrant stay on a private host (VPN/TLS).
2. **On-device first** — run embeddings (and possibly Qdrant or a synced snapshot) on the phone.

On-device inference and local vector DB on Android add model packaging, thermal/battery cost, sync conflict complexity, and a second security surface — before Layer 2/3 are even complete.

---

## Decision

**Adopt thin client for v1.**

- Web and Android clients use `VITE_API_BASE_URL` / equivalent HTTPS base URL only.
- Clients **never** open Qdrant ports or load embedding models locally in v1.
- Private cloud host runs Compose (`api` + `qdrant`) with persistent volumes; expose **API** to VPN clients, keep Qdrant internal (or firewalled).
- Path-based ingest remains for desktop/operators; **multipart upload / device → `staging/` → gate → `curated/`** is the next API contract for `mobile-data-pipeline` (not required to accept this ADR).

See runbook: `docs/private-cloud-thin-client.md`. Compose helper: `docker-compose.private-cloud.yml`.

---

## Consequences

**Positive**

- One inference + storage plane; curation gate and secret scanning stay server-side.
- Android UI work (`android-ui-ux` subagent) can wrap or call the same REST API as the web console.
- Matches existing env knobs (`QDRANT_URL`, `CORS_ALLOWED_ORIGINS`, curation flags).

**Negative / follow-ups**

- Offline query on the phone is out of scope until a later hybrid cache ADR.
- Mobile ingest UX is blocked on an upload/staging API (owned by `mobile-data-pipeline`).
- Operators must place the API behind VPN or mutual TLS; CORS must list real client origins.

**Non-goals of this ADR**

- Choosing Capacitor vs Kotlin/Compose
- Changing embedding model or Qdrant schema
- Implementing L2/L3

---

## Related

- `docs/research/rag-improvement-strategies-2026.md` — server-side retrieval backlog
- `.cursor/agents/android-ui-ux.md` / `.cursor/agents/mobile-data-pipeline.md`
- ADR-0001 — L2 SQLite (still server-side)
