# OmniKB runtime logs

Structured logs for **UI interactions**, **API timing**, and **client→server** diagnostics.

## Layout

| File pattern | Source | Contents |
|--------------|--------|----------|
| `api-requests-YYYY-MM-DD.jsonl` | FastAPI middleware | Method, path, status, `duration_ms`, optional `client_correlation_id` header |
| `ui-client-YYYY-MM-DD.jsonl` | React overlay → `POST /dev/ui-logs` | Clicks, handlers, fetch timings, errors, correlation ids |

Files are **append-only JSONL** (one JSON object per line). They are gitignored; only this README and `.gitkeep` are tracked.

## Enable / disable

**Backend** (`.env` or environment):

- `OMNIKB_UI_LOGGING_ENABLED=true` (default in dev)
- `OMNIKB_REQUEST_LOGGING_ENABLED=true`
- `OMNIKB_LOGS_DIR=logs` (relative to process cwd, or absolute path)

**Frontend** (`web/.env`):

- `VITE_UI_LOGGING=true` — overlay + instrumentation (default on in Vite `import.meta.env.DEV`)
- `VITE_UI_LOG_TO_SERVER=true` — batch POST to `/dev/ui-logs`

## Usage

1. Start API and `cd web && npm run dev`.
2. In the browser, open the **UI Log** panel (bottom-right).
3. Click **Search** or **Ingest Path**; watch handler start/end and API rows with **ms** timings.
4. Inspect repo `logs/*.jsonl` while reproducing issues.

## Correlation

Each user action (e.g. search) gets a `correlation_id` (`ui-…`) attached to related API calls via the `X-Correlation-Id` header so you can join overlay lines with `api-requests` lines.
