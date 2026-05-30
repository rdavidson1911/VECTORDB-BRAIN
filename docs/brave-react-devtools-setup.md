# Brave browser — React DevTools & debugging setup

Use this guide when configuring **Brave** for OmniKB frontend work (`web/`, `http://localhost:5173`) and when React DevTools shows **“Profiling not supported”** or component errors (e.g. `Multivariate3DTemplate`).

Related: [internal-react-devtools-debugging-guide.md](./internal-react-devtools-debugging-guide.md), `internal_docs/react-cheatsheet-and-debug.md`.

---

## 1. Install React Developer Tools in Brave

1. Open Brave → **Extensions** (`brave://extensions`) or Chrome Web Store (Brave is Chromium-based).
2. Install **[React Developer Tools](https://chromewebstore.google.com/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)** (official Meta extension).
3. Pin the extension; confirm the **⚛** icon appears on `http://localhost:5173`.
4. Optional: enable **“Allow access to file URLs”** only if you debug `file://` pages (not needed for Vite dev server).

---

## 2. Open DevTools the way React expects

| Action | Shortcut (Windows) |
|--------|---------------------|
| DevTools | `F12` or `Ctrl+Shift+I` |
| Console | `Ctrl+Shift+J` |
| Reload (hard) | `Ctrl+Shift+R` |

After install you should see extra tabs: **Components** and **Profiler** (may appear under `>>` if the window is narrow).

---

## 3. Fix “Profiling not supported”

Message: *Profiling support requires either a development or profiling build of React v16.5+.*

| Cause | Fix |
|--------|-----|
| Running **production** bundle | Use **`npm run dev`** in `web/`, not `npm run preview` or a static `dist/` folder. |
| Stale Vite prebundle | From `web/`: **`npm run dev:fresh`** (clears `node_modules/.vite`, starts dev server). |
| Wrong `NODE_ENV` in optimized deps | Repo `vite.config.ts` forces `process.env.NODE_ENV = "development"` in dev + `resolve.dedupe` for `react` / `react-dom`. Restart dev after pulling config changes. |
| Duplicate React | In Components tab, if hook state looks wrong, check for two copies of `react` (dedupe is configured in Vite). |

**Profiler workflow**

1. `cd web` → `npm run dev:fresh`
2. Open `http://localhost:5173` in Brave.
3. DevTools → **Profiler** → record (blue circle) → interact with UI → stop → Flamegraph / Ranked.

---

## 4. Component errors (e.g. Multivariate3DTemplate)

If the console shows: *An error occurred in the \<Multivariate3DTemplate\> component*:

1. **Console** — read the **first red error** above the boundary warning (often Plotly chunk load or layout).
2. **Components** — select `Multivariate3DTemplate` or `ChartErrorBoundary`; inspect props and state.
3. **Network** — confirm `react-plotly-*.js` chunk loads (200).
4. UI — `ChartErrorBoundary` shows a red panel with **Retry** so the rest of the dashboard still works.

---

## 5. Recommended dev loop (OmniKB)

```powershell
# Terminal 1 — API
docker compose up --build -d

# Terminal 2 — frontend (from repo root or web/)
cd web
npm run dev:fresh
```

Optional: `scripts/open-brave-react-dev.ps1` opens Brave to the dev URL and prints this checklist.

Smoke after changes:

```powershell
cd web
$env:INGEST_TIMEOUT_MS = "120000"
$env:QUERY_TIMEOUT_MS = "120000"
npm run smoke:playwright
```

If smoke fails on `.result-card`, see **`internal_docs/playwright-smoke-VDB-SMOKE-2026-05-25-FAIL.md`** and **`internal_docs/debugging-playwright-and-devtools-breakpoints.md`** (local, gitignored).

---

## 6. Brave-specific notes

- **Shields**: for localhost, shields are usually fine; if API calls fail, check **Network** for blocked requests (rare on `127.0.0.1`).
- **Same DevTools as Chrome**: breakpoints, Network, Sources, and React tabs behave like Chrome/Edge.
- **Multiple profiles**: install React DevTools per Brave profile you use for development.

---

## 7. Quick checklist

- [ ] React Developer Tools installed and enabled on `localhost:5173`
- [ ] `npm run dev` or `dev:fresh` (not preview-only)
- [ ] Profiler records without “Profiling not supported”
- [ ] Components tab shows `App` → charts → `ChartErrorBoundary` when 3D chart fails
- [ ] Console has no uncaught errors before profiling a slow interaction
