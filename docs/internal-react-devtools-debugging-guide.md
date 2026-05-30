# Internal Guide: Debugging React + Web App with Browser DevTools

This internal guide explains how to debug the OmniKB React frontend and API interaction flows using browser DevTools (Chrome/Edge), including breakpoints, locals, watches, click events, and line-by-line stepping.

## 1) Scope and Use Cases

Use this guide when you need to:

- debug button click behavior (`Search`, `Ingest Path`, `Clear`)
- inspect API request/response issues (`/health`, `/corpus/summary`, `/corpus/sources`, `/query`, `/ingest/path`)
- diagnose CORS, empty dashboard, no-result search, or broken metadata filters
- inspect React state transitions (`queryForm`, `matches`, `analytics`, `loading`, `error`)

Primary frontend files:

- `web/src/App.tsx`
- `web/src/lib/api.ts`
- `web/src/types.ts`

## 2) Debugging Setup Checklist

1. Start backend:

```powershell
docker compose up --build -d
```

2. Start frontend:

```powershell
cd web
npm run dev
```

3. Open app:

- `http://localhost:5173`

4. Open DevTools:

- `F12` or `Ctrl+Shift+I`

5. Useful panels:

- **Elements**
- **Console**
- **Sources**
- **Network**

## 3) Fast Debug Triage Flow

When something breaks:

1. **Console first**: check stack traces, CORS errors, and runtime exceptions.
2. **Network second**: inspect failing requests and payloads.
3. **Sources third**: set breakpoints where handlers or API calls originate.
4. **State verification**: confirm `queryForm`, `loading`, `matches`, and `error`.

## 4) Button Click Event Debugging

### Search button (`runSearch`)

File path:

- `web/src/App.tsx`

Relevant function:

- `runSearch()`

Steps:

1. Open **Sources**.
2. Open `src/App.tsx` (Vite source map path).
3. Set breakpoint on:
   - request construction (`const request: QueryRequest = ...`)
   - API call (`const response = await api.query(request)`)
   - state updates (`setMatches`, `setAnalytics`)
4. Click **Search** in UI.
5. Use debugger controls:
   - Resume (`F8`)
   - Step over (`F10`)
   - Step into (`F11`)
   - Step out (`Shift+F11`)
6. Verify local values:
   - `queryForm`
   - `request`
   - `response`

### Ingest Path button (`runIngest`)

Set breakpoints in `runIngest()`:

- before `api.ingestPath(...)`
- after response assignment
- before `await loadDashboardData()`

Validate:

- `ingestPath` value is expected (`/data/sources` by default)
- response counters are nonzero for valid corpus

### Clear button

Breakpoint inside the `onClick` block for **Clear** button:

- verify `setQueryForm(INITIAL_QUERY)`
- verify `setMatches([])` and `setAnalytics(null)`

## 5) Breakpoints at Specific Points

## A) Line breakpoints

Click left gutter in **Sources** next to target line.

Best lines for this codebase:

- `loadDashboardData()` Promise.all API calls in `App.tsx`
- `runSearch()` request assembly and API call in `App.tsx`
- `requestJson()` fetch call in `api.ts`
- `if (!response.ok)` branch in `api.ts`

## B) Conditional breakpoints

Right-click breakpoint -> **Edit breakpoint** and add expression.

Examples:

- break only on empty result:
  - `response.matches.length === 0`
- break only on specific file type filter:
  - `request.file_type === "pdf"`
- break only on errors:
  - `!response.ok`

## C) XHR/fetch breakpoints

In **Sources** -> right sidebar -> **XHR/fetch Breakpoints** -> add path snippet:

- `/query`
- `/ingest/path`
- `/corpus/summary`

Debugger pauses whenever matching request is made.

## D) Event listener breakpoints

In **Sources** -> **Event Listener Breakpoints**:

- `Mouse > click`

Useful when you do not know where a click handler lives.

## 6) Locals, Scope, and Watches

When paused on a breakpoint:

- **Scope/Local** pane shows local variables
- **Call Stack** shows execution path
- **Watch** pane lets you track custom expressions

Recommended watches for OmniKB:

- `queryForm`
- `loading`
- `error`
- `matches.length`
- `analytics?.returned_count`
- `response.status`
- `request`

Tip: add deep watches for payload checks:

- `response.matches?.[0]?.payload`

## 7) Step Line-by-Line Through Frontend Code

Start at `runSearch()`:

1. step over validation check (`if (!queryForm.query.trim())`)
2. step over request object population
3. step into `api.query(...)`
4. step into `requestJson(...)`
5. step over `fetch(...)`
6. inspect `response.ok` and returned JSON
7. step out back into `runSearch()`
8. inspect `setMatches` and `setAnalytics` arguments

Repeat for `runIngest()` and `loadDashboardData()` to validate full dashboard refresh flow.

## 8) Network Panel Workflow (VectorDB-Specific)

For each request, inspect:

- **General**:
  - URL, method, status code
- **Headers**:
  - request/response headers
  - CORS headers (`access-control-allow-origin`, etc.)
- **Payload**:
  - JSON body sent to `/query` or `/ingest/path`
- **Response**:
  - returned `matches`, `analytics`, ingest counters
- **Timing**:
  - slow request diagnosis

Common endpoint checks:

- `GET /health` -> should return `service: ok`, `qdrant: ok`
- `GET /corpus/summary` -> summary counters
- `GET /corpus/sources` -> indexed source list
- `POST /query` -> `matches` + `analytics`
- `POST /ingest/path` -> ingest counters

## 9) CORS and Preflight Debugging

Symptoms:

- `blocked by CORS policy` in console
- `net::ERR_FAILED` in fetch call

Debug steps:

1. In Network, filter by `OPTIONS`.
2. Inspect preflight status and headers.
3. If preflight fails, run:

```powershell
powershell -ExecutionPolicy Bypass -File devtools/cors-repl.ps1
```

4. Rebuild/restart API if stale:

```powershell
docker compose up --build -d api
```

Related incident log:

- `devtools/error-tracking-db.md`

## 10) React State and Render Debugging Tips

- Use `console.log` temporarily in handlers when needed; remove after fix.
- Check StrictMode double-invocation behavior in dev (effects may run twice).
- Validate controlled inputs:
  - every filter input maps to expected `queryForm` key
- Confirm UI assumptions:
  - query must be non-empty
  - results panel handles empty arrays

## 11) Breakpoint Recipe Library

### Recipe A: "Search returns empty unexpectedly"

1. Breakpoint in `runSearch()` before API call.
2. Verify request filters are not over-constrained.
3. Step into `api.requestJson`.
4. Inspect response JSON in Network panel.
5. Watch `response.matches.length`.

### Recipe B: "Dashboard cards show zeros"

1. Breakpoint in `loadDashboardData()`.
2. Step through Promise.all responses.
3. Inspect `summaryResp` and `sourceResp`.
4. Confirm `/corpus/summary` and `/corpus/sources` return non-empty data.

### Recipe C: "Ingest appears successful but search still misses content"

1. Break in `runIngest()`.
2. Verify `ingestPath` and response counters.
3. Run `/query` directly in Network with minimal filters.
4. Check source files are supported types and contain text.

## 12) Backend + Frontend Combined Debugging

When frontend looks fine but behavior is wrong:

1. verify backend health:
   - `Invoke-RestMethod http://localhost:8000/health`
2. verify corpus visibility:
   - `Invoke-RestMethod http://localhost:8000/corpus/summary`
3. verify ingest:
   - `Invoke-RestMethod -Method Post -Uri http://localhost:8000/ingest/path -ContentType application/json -Body '{"path":"/data/sources","recursive":true}'`
4. compare API output in terminal vs browser Network panel.

## 13) Repeatable Debug Validation

Use automated smoke after fixes:

From `web/`:

```powershell
npm run smoke:playwright
```

This verifies:

1. CORS preflight
2. dashboard render
3. query execution
4. incident log append to `devtools/error-tracking-db.md`

## 14) Internal Best Practices

- Prefer conditional breakpoints over excessive `console.log`.
- Keep request payloads minimal during triage.
- Capture evidence (console + network + repro steps) in `devtools/error-tracking-db.md`.
- When fixing, always validate both:
  - targeted scenario
  - core smoke flow (`npm run smoke:playwright`)

## 15) Brave + React DevTools (Profiler & Components)

**Canonical setup:** [brave-react-devtools-setup.md](./brave-react-devtools-setup.md)

### Install

1. Brave → `brave://extensions` → install **React Developer Tools**.
2. Dev server: `cd web` → `npm run dev` or `npm run dev:fresh` (clears Vite cache).
3. Open `http://localhost:5173` → `F12` → tabs **Components** / **Profiler**.

### “Profiling not supported”

- You are almost certainly on a **production** React bundle (`vite preview`, old prebundle, or `dist/`).
- Fix: stop preview; run `npm run dev:fresh`; hard reload (`Ctrl+Shift+R`).
- Repo `web/vite.config.ts` sets development `NODE_ENV` for dev prebundling and dedupes `react` / `react-dom`.

### Component error in `Multivariate3DTemplate`

1. Console: read the **root** exception (Plotly import/layout), not only the boundary warning.
2. Components tree: look for `ChartErrorBoundary` → child `Multivariate3DTemplate`.
3. Network: verify lazy chunk `react-plotly-*.js` returns 200.

### Helper script

```powershell
.\scripts\open-brave-react-dev.ps1
```

## 16) UI interaction & timing logs

**Repo logs directory:** `logs/` (see `logs/README.md`)

- **Overlay:** bottom-right **UI Log** panel in dev (`web/`); records clicks, handler start/end, API `duration_ms`, correlation ids.
- **Disk:** `logs/ui-client-*.jsonl` (browser batches via `POST /dev/ui-logs`) and `logs/api-requests-*.jsonl` (FastAPI middleware).
- **Headers:** `X-Correlation-Id` on requests; response `X-Request-Duration-Ms` for server time.

Disable server ingest: `OMNIKB_UI_LOGGING_ENABLED=false`. Disable overlay: `VITE_UI_LOGGING=false` in `web/.env`.
