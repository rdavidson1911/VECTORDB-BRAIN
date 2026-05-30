Local smoke-test incident log (Playwright and similar). Entries are appended over time. Contains localhost URLs only; no secrets expected here.

**Qdrant storage / disk:** See `docs/internal/qdrant-wal-disk-space-troubleshooting.md` for `WAL buffer size exceeds available disk space` (capture commands, theories, prevention).

## Incident QDRANT-WAL-DISK (reference)

- **Error (example):** `Service internal error: No space left on device: WAL buffer size exceeds available disk space`
- **Typical trigger:** Bulk ingest / upsert while filesystem backing `/qdrant/storage` is full or Docker/WSL disk image is full
- **Not:** Per-collection Docker allow-list for `omnikb_documents`
- **Confirmed at rest (2026-05-25):** Container `df` showed ~478 GB avail on `I:\` bind mount; ~0.9 GB used � failure likely **at-time** or **Docker disk pool**, not current host `I:` space
- **When it happens again:** Run capture kit in that doc; append a dated subsection below with pasted `df`, `docker system df`, and operation (ingest path/file)

## Incident VDB-SMOKE-2026-05-15-PASS

- Timestamp: `2026-05-15T00:03:38.546Z`
- Type: `playwright-smoke`
- Status: `PASS`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - PASS | Seed ingest | status=200 timeout_ms=120000
  - PASS | Dashboard load | Heading and status badge rendered.
  - PASS | Query run | result_cards=10


## Incident VDB-SMOKE-2026-05-15-FAIL

- Timestamp: `2026-05-15T19:20:32.009Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `Ingest failed: status=500 Internal Server Error. If this was a timeout, increase INGEST_TIMEOUT_MS or run ingest once manually after model download.`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - FAIL | Seed ingest | status=500 timeout_ms=120000


## Incident VDB-SMOKE-2026-05-15-FAIL

- Timestamp: `2026-05-15T19:56:34.917Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `apiRequestContext.fetch: Timeout 120000ms exceeded.
Call log:
[2m  - ? POST http://localhost:8000/ingest/path[22m
[2m    - user-agent: Playwright/1.59.1 (x64; windows 10.0) node/24.12[22m
[2m    - accept: */*[22m
[2m    - accept-encoding: gzip,deflate,br[22m
[2m    - content-type: application/json[22m
[2m    - content-length: 41[22m
`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}


## Incident VDB-SMOKE-2026-05-15-FAIL

- Timestamp: `2026-05-15T20:55:40.659Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `apiRequestContext.fetch: Timeout 120000ms exceeded.
Call log:
[2m  - ? POST http://localhost:8000/ingest/path[22m
[2m    - user-agent: Playwright/1.59.1 (x64; windows 10.0) node/24.12[22m
[2m    - accept: */*[22m
[2m    - accept-encoding: gzip,deflate,br[22m
[2m    - content-type: application/json[22m
[2m    - content-length: 41[22m
`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}


## Incident VDB-SMOKE-2026-05-16-PASS

- Timestamp: `2026-05-16T03:48:18.533Z`
- Type: `playwright-smoke`
- Status: `PASS`
- Web URL: `http://127.0.0.1:5173`
- API URL: `http://localhost:8000`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://127.0.0.1:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - PASS | Seed ingest | skipped (SMOKE_SKIP_INGEST=1)
  - PASS | Dashboard load | Heading and status badge rendered.
  - PASS | Query run | result_cards=10


## Incident VDB-SMOKE-2026-05-19-FAIL

- Timestamp: `2026-05-19T18:37:34.033Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `apiRequestContext.fetch: Timeout 120000ms exceeded.
Call log:
[2m  - ? POST http://localhost:8000/ingest/path[22m
[2m    - user-agent: Playwright/1.59.1 (x64; windows 10.0) node/24.12[22m
[2m    - accept: */*[22m
[2m    - accept-encoding: gzip,deflate,br[22m
[2m    - content-type: application/json[22m
[2m    - content-length: 41[22m
`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}


## Incident VDB-SMOKE-2026-05-19-FAIL

- Timestamp: `2026-05-19T19:11:53.051Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `apiRequestContext.fetch: Timeout 120000ms exceeded.
Call log:
[2m  - ? POST http://localhost:8000/ingest/path[22m
[2m    - user-agent: Playwright/1.59.1 (x64; windows 10.0) node/24.12[22m
[2m    - accept: */*[22m
[2m    - accept-encoding: gzip,deflate,br[22m
[2m    - content-type: application/json[22m
[2m    - content-length: 41[22m
`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}


## Incident VDB-SMOKE-2026-05-20-FAIL

- Timestamp: `2026-05-20T05:19:33.580Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `apiRequestContext.fetch: Timeout 120000ms exceeded.
Call log:
[2m  - ? POST http://localhost:8000/ingest/path[22m
[2m    - user-agent: Playwright/1.59.1 (x64; windows 10.0) node/24.12[22m
[2m    - accept: */*[22m
[2m    - accept-encoding: gzip,deflate,br[22m
[2m    - content-type: application/json[22m
[2m    - content-length: 41[22m
`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}


## Incident VDB-SMOKE-2026-05-25-FAIL

- Timestamp: `2026-05-25T19:02:06.828Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `locator.waitFor: Timeout 20000ms exceeded.
Call log:
[2m  - waiting for locator('.result-card').first() to be visible[22m
`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - PASS | Seed ingest | status=200 timeout_ms=120000
  - PASS | Dashboard load | Heading and status badge rendered.
- Resolution: see `internal_docs/playwright-smoke-VDB-SMOKE-2026-05-25-FAIL.md` (cause: 20s UI wait vs slow/empty query; smoke harness updated).


## Incident VDB-SMOKE-2026-05-25-FAIL

- Timestamp: `2026-05-25T20:52:06.510Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `UI query did not produce result cards (http=200, cards=0). Body: {"matches":[],"analytics":{"latency_ms":9.198,"returned_count":0,"unique_sources":0,"top_score":0.0,"average_score":0.0}}`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - PASS | Seed ingest | status=200 timeout_ms=120000
  - PASS | Dashboard load | Heading and status badge rendered.
  - PASS | Query warm-up (API) | status=200 timeout_ms=120000
  - FAIL | Query run (UI) | http=200 result_cards=0 error_panel=false body={"matches":[],"analytics":{"latency_ms":9.198,"returned_count":0,"unique_sources":0,"top_score":0.0,"average_score":0.0}

## Incident VDB-SMOKE-2026-05-28-FAIL

- Timestamp: `2026-05-28T23:59:32.394Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `Ingest failed: status=400 {"detail":"Path must stay under the configured sources directory."}. If this was a timeout, increase INGEST_TIMEOUT_MS or run ingest once manually after model download.`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - FAIL | Seed ingest | status=400 timeout_ms=120000


## Incident VDB-SMOKE-2026-05-29-FAIL

- Timestamp: `2026-05-29T01:06:00.912Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `Ingest failed: status=400 {"detail":"Path must stay under the configured sources directory."}. If this was a timeout, increase INGEST_TIMEOUT_MS or run ingest once manually after model download.`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - FAIL | Seed ingest | status=400 timeout_ms=120000


## Incident VDB-SMOKE-2026-05-29-FAIL

- Timestamp: `2026-05-29T10:57:40.366Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `Ingest failed: status=400 {"detail":"Path must stay under the configured sources directory."}. If this was a timeout, increase INGEST_TIMEOUT_MS or run ingest once manually after model download.`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - FAIL | Seed ingest | status=400 timeout_ms=120000

## Incident VDB-SMOKE-2026-05-29-FAIL

- Timestamp: `2026-05-29T19:06:56.937Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `Ingest failed: status=400 {"detail":"Path must stay under the configured sources directory."}. If this was a timeout, increase INGEST_TIMEOUT_MS or run ingest once manually after model download.`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - FAIL | Seed ingest | status=400 timeout_ms=120000


## Incident VDB-SMOKE-2026-05-29-FAIL

- Timestamp: `2026-05-29T20:50:06.107Z`
- Type: `playwright-smoke`
- Status: `FAIL`
- Web URL: `http://localhost:5173`
- API URL: `http://localhost:8000`
- Error: `Ingest failed: status=400 {"detail":"Path must stay under the configured sources directory."}. If this was a timeout, increase INGEST_TIMEOUT_MS or run ingest once manually after model download.`
- Checks:
  - PASS | CORS preflight | status=200 acao=http://localhost:5173
  - PASS | API health (GET) | status=200 body={"service":"ok","qdrant":"ok","collection":"omnikb_documents"}
  - FAIL | Seed ingest | status=400 timeout_ms=120000
