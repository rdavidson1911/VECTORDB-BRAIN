# OmniKB User Operations Guide

This guide is for end users and operators who want to ingest files, search effectively, troubleshoot issues, and inspect the database beyond one-off queries.

For **why** we curate data, identity and dedupe rules, chunk policy vs benchmarks, compression and filesystem migration guidance, and where each doc fits, see the canonical strategy: [data-curation-pipeline.md](data-curation-pipeline.md).

### Curation automation (local)

- Generate a corpus manifest (paths, sizes, mtimes, content hashes): `python scripts/generate_corpus_manifest.py`
- Validate a tree before ingest (dry-run): `python scripts/validate_corpus.py --root data/sources`
- Chunk benchmarks with options: `python scripts/benchmark_chunking.py --help`
- Obsidian staging conventions: [obsidian-export-to-omnikb.md](obsidian-export-to-omnikb.md)

## 1) Before You Start

Prerequisites:

- Docker Desktop running
- Backend API available at `http://localhost:8000`
- React UI available at `http://localhost:5173` (optional but recommended)

Quick health checks:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response includes:

- `service: ok`
- `qdrant: ok`

## 2) Prepare Files for Upload/Ingestion

Current supported source types:

- `.md`
- `.txt`
- `.pdf`

### Recommended preparation checklist

1. **UTF-8 encoding** for text-based files.
2. **Clean structure**:
   - Markdown: use headings (`#`, `##`) to preserve semantic structure.
   - TXT: use paragraph breaks where topics change.
3. **Stable filenames**:
   - Use descriptive names (`network-runbook.md`, `incident-2026-05-01.txt`).
4. **Reduce noise**:
   - Remove boilerplate repeated content where possible.
5. **Content quality**:
   - Keep each file focused on one topic or domain area.

### Where to place files

Default ingest path:

- `data/sources`

Example:

```powershell
Copy-Item .\my-notes\* .\data\sources\ -Recurse
```

## 3) Ingest Files into the Vector Database

### Option A: From React UI

1. Open `http://localhost:5173`.
2. In the **Ingestion** panel, set source path (default `/data/sources`).
3. Click **Ingest Path**.
4. Confirm returned counters:
   - files seen
   - files indexed
   - chunks indexed

### Option B: API command

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/ingest/path -ContentType application/json -Body '{"path":"/data/sources","recursive":true,"skip_unchanged":false}'
```

### Preview chunking before ingest (recommended)

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/ingest/preview -ContentType application/json -Body '{"path":"/data/sources","recursive":true,"limit_files":10}'
```

Use this to validate chunk structure before full indexing.

## 4) Search for Specific Text and Metadata

### Search in React UI

Use the **Search and Refinement Criteria** panel:

- Query text
- Source path
- File type
- Date range (`date_from`, `date_to`)
- Minimum score
- Document ID
- Content hash
- Chunk strategy
- Text contains

Run search, then review:

- score
- source path
- chunk index
- content preview
- full text + metadata (expandable)

### Search via API

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/query -ContentType application/json -Body '{
  "query":"Find network troubleshooting steps",
  "limit":10,
  "file_type":"md",
  "min_score":0.3,
  "date_from":"2026-05-01",
  "date_to":"2026-05-31",
  "text_contains":"firewall"
}'
```

## 5) Future Media Types (`.jpg`, `.svg`, etc.)

Current state:

- `.jpg`, `.png`, `.svg`, and other media are **not yet ingested directly** as searchable visual content.

Recommended current workflow:

1. Create sidecar text/markdown files describing media content.
2. Store metadata in text:
   - filename
   - caption/description
   - tags
   - source date
3. Ingest those sidecar files for semantic retrieval.

Example:

- `diagram-architecture.svg`
- `diagram-architecture.md` (contains explanation, labels, and tags)

Planned enhancement direction:

- OCR for image text extraction
- metadata extraction pipeline
- multimodal embeddings for image/vector search

## 6) Administrative Tasks

### A) Check service health

```powershell
Invoke-RestMethod http://localhost:8000/health
```

### B) Inspect collection stats

```powershell
Invoke-RestMethod http://localhost:8000/collections/omnikb_documents/stats
```

### C) View corpus summary

```powershell
Invoke-RestMethod http://localhost:8000/corpus/summary
```

### D) List indexed sources

```powershell
Invoke-RestMethod http://localhost:8000/corpus/sources
```

### E) Run smoke checks

Backend/API smoke:

```powershell
.\scripts\smoke-test.ps1
```

Playwright end-to-end smoke (run from repo **root** or from `web/`):

```powershell
# repo root (uses root package.json → delegates to web/)
npm run smoke:playwright

# or from web/
cd web
npm run smoke:playwright
```

Requires `docker compose up -d` (API) and `npm run dev` in `web/` (Vite). The first `ingest` in the smoke can take **over a minute** while the embedding model loads; the script defaults to a **120s** ingest timeout (`INGEST_TIMEOUT_MS`). If the corpus is already indexed, you can skip the seed ingest: `$env:SMOKE_SKIP_INGEST='1'; npm run smoke:playwright` (from root or `web/`).

## 7) View the Database Beyond Individual Queries

Use these methods for broader visibility:

1. **React dashboards**
   - Corpus summary cards
   - File type distribution chart
   - Top sources by chunk count
2. **API endpoints**
   - `/corpus/summary` for totals and distribution
   - `/corpus/sources` for per-source inventory
   - `/collections/{name}/stats` for collection-level data
3. **Benchmark outputs**
   - `data/processed/benchmarks/chunking-benchmark-latest.json`
4. **Incident/evidence log**
   - `devtools/error-tracking-db.md`

## 8) Troubleshooting Guide

### Problem: React shows CORS errors

Symptoms:

- Browser console contains CORS preflight failures.

Fix:

1. Restart API with latest code:
   - `docker compose up --build -d api`
2. Run CORS REPL:
   - `powershell -ExecutionPolicy Bypass -File devtools/cors-repl.ps1`
3. Confirm preflight returns `200` and includes `Access-Control-Allow-Origin`.

### Problem: Query returns no results

Checklist:

1. Confirm ingestion completed successfully.
2. Lower `min_score` threshold.
3. Remove strict filters (`source_path`, `content_hash`, date window).
4. Verify files are in supported formats and contain meaningful text.

### Problem: Dashboard looks empty

Checklist:

1. Confirm `/corpus/summary` returns data.
2. Re-run ingest for `/data/sources`.
3. Refresh React page after ingest.

### Problem: Playwright smoke fails

Checklist:

1. Ensure frontend dev server is running (`web`: `npm run dev`).
2. Ensure backend is running (`docker compose up -d`).
3. Install browser binaries if needed:
   - `npx playwright install chromium`
4. Re-run from repo root or `web/`: `npm run smoke:playwright`
5. If ingest times out, wait for a manual ingest to finish once (model download), or raise timeout: `$env:INGEST_TIMEOUT_MS='180000'; npm run smoke:playwright`

## 9) Daily Operator Workflow (Suggested)

Governance and lifecycle context for this workflow: [data-curation-pipeline.md](data-curation-pipeline.md).

1. Add/update files in `data/sources`.
2. Run ingest.
3. Run 2-3 representative searches.
4. Review corpus dashboards.
5. Run smoke scripts before major demos/releases.
6. Record incidents and lessons in `devtools/error-tracking-db.md`.
