# Private Cloud Thin Client Runbook

Deploy VECTORDB-BRAIN / OmniKB so **web and (later) Android clients** talk only to FastAPI. Embeddings and Qdrant stay on a private host. See ADR-0002.

## Topology

```
[Web / Android] --VPN/TLS--> [FastAPI :8000] --> [Qdrant :6333 internal]
                                |
                                +--> bind-mount data/sources (curated/staging/_samples)
```

- Do **not** publish Qdrant `6333` to the public internet.
- Prefer Tailscale, WireGuard, or a private VPC; terminate TLS at a reverse proxy if exposing beyond localhost.

## Local baseline (unchanged)

```bash
docker compose up --build -d
# API http://localhost:8000  Qdrant http://localhost:6333  Web npm run dev :5173
```

## Private host: API + local Qdrant (recommended)

On the private VM/NAS:

1. Clone the repo; copy `.env.example` → `.env`.
2. Set durable paths, e.g.:

   ```bash
   DATA_SOURCES_PATH=/var/lib/omnikb/sources
   QDRANT_STORAGE_PATH=/var/lib/omnikb/qdrant
   PROCESSED_DATA_PATH=/var/lib/omnikb/processed
   CORS_ALLOWED_ORIGINS=https://kb.example.ts.net,http://localhost:5173
   ```

3. Start the default compose stack (`api` + `qdrant`). Firewall so only VPN peers reach `:8000`.
4. Point the web app at the API:

   ```bash
   # web/.env
   VITE_API_BASE_URL=https://kb.example.ts.net
   ```

5. Future Android clients use the same HTTPS base URL (no Qdrant URL in the app).

## Private host: API against a remote Qdrant

When Qdrant already runs elsewhere on the private network:

```bash
# .env on the API host
QDRANT_URL=http://qdrant.internal:6333

docker compose -f docker-compose.yml -f docker-compose.private-cloud.yml \
  up --build --no-deps -d api
```

The override file makes `QDRANT_URL` from `.env` win over the base compose pin to `http://qdrant:6333`. Use `--no-deps` so Compose does not also start the unused local `qdrant` service.

## Operator checklist

| Check | Command / action |
|-------|------------------|
| Health | `curl -sS "$API/health"` |
| Validate curated | `python scripts/validate_corpus.py --gate-root curated` or `POST /curation/validate` |
| Ingest | `POST /ingest/path` with container/host paths under `DATA_SOURCES_PATH` |
| Gate | Keep `CURATION_GATE_ENABLED=true`; never enable `CURATION_ALLOW_OVERRIDE` on production without dual control |

## Mobile ingest (next)

Path ingest assumes a host/container filesystem. Phones need a follow-up API (multipart or sync into `data/sources/staging/`), then validate → promote → curated ingest. Owned by the `mobile-data-pipeline` Cursor subagent; UI shell by `android-ui-ux`.

## Security notes

- Never commit real `.env` or API keys.
- Restrict CORS to known web origins; native Android apps are not browser CORS clients but still need TLS + auth when you add it.
- Curation secret regexes still apply to curated content (`CLAUDE.md` §4.5).
