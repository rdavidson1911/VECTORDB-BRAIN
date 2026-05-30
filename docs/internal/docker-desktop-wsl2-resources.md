# Docker Desktop, WSL2, and OmniKB resource allocation (Windows 11 Pro)

**Audience:** Internal team (dev, ops, QA)
**Stack:** `omnikb-api` + `omnikb-qdrant` via `docker-compose.yml`
**Companion workbook:** `internal_docs/docker-resource-budget-model.xlsx` (generate with `python scripts/generate_docker_resource_model.py`)

---

## 1. What actually gets “allocated” on Windows 11 Pro

Docker Desktop on Windows does **not** assign a fixed CPU/RAM quota per container the way a hypervisor might assign vCPUs to two VMs. The usual path is:

```text
Windows 11 (host)
  └── vmmem / WSL2 lightweight utility VM  ← Docker Desktop memory/CPU slider applies HERE
        └── Linux (Docker Engine)
              ├── container: omnikb-qdrant
              └── container: omnikb-api
```

Implications for OmniKB:

| Layer | What you configure | Effect on Qdrant vs API |
|--------|-------------------|-------------------------|
| **Docker Desktop → Resources** | CPUs, memory, swap, disk image size | Caps the **whole** WSL2/Docker VM. Both services share that pool. |
| **`%UserProfile%\.wslconfig`** | `memory`, `processors`, `swap` | Can further cap WSL before Docker starts (must `wsl --shutdown` after edits). |
| **`docker-compose.yml`** | *(this repo)* no `deploy.resources` / no `mem_limit` | **No per-service cap** — Qdrant and API compete freely inside the VM. |
| **Container runtime** | Linux cgroups (managed by Docker) | Default fair scheduling; spikes from one container can starve the other under pressure. |

So “allocation between Qdrant and the API” is really **shared-pool behavior + workload timing**, not a 50/50 split unless you add Compose limits (not in the current compose file).

---

## 2. How each OmniKB service uses resources (intuition)

### Qdrant (`omnikb-qdrant`)

- **Role:** Vector index + payload storage (`data/qdrant` bind mount).
- **CPU:** Bursts during upsert (ingest), HNSW search under query load; often moderate at idle.
- **RAM:** Grows with **point count**, **vector dimension** (384 for `all-MiniLM-L6-v2`), payload size, and segment count. Rough order: hundreds of MB for small corpora → GB+ for large indexes.
- **Disk:** Persistent under `./data/qdrant`; I/O on ingest and compaction.

### API (`omnikb-api`)

- **Role:** FastAPI + **sentence-transformers** embedder + Qdrant client.
- **CPU:** Spikes on **first embed** (model load) and on **ingest/query** (encoding + HTTP).
- **RAM:** Often **dominates** the stack: PyTorch + model weights + batching. First ingest after cold start is the worst case (model + many chunks).
- **Disk:** Image size; read-only `/data/sources`; writes under `/data/processed` and `/app/logs`.

### Typical contention scenarios

1. **Cold ingest** — API RAM/CPU high (embeddings); Qdrant RAM/CPU rise (upserts). Highest risk of hitting Docker memory limit.
2. **Steady query** — API encode + Qdrant search; usually lower than full ingest.
3. **Idle** — Both lower; API may still hold model in memory if the process has not released it.

---

## 3. Where Docker Desktop “measures” usage

| Tool | What it shows |
|------|----------------|
| **Docker Desktop → Containers** | Per-container CPU % and memory (live). |
| **`docker stats`** | CLI stream: `NAME`, `CPU %`, `MEM USAGE / LIMIT`, `NET I/O`, `BLOCK I/O`. |
| **Windows Task Manager → Performance** | **vmmem** / **VmmemWSL** ≈ entire WSL2 VM (all containers + overhead). |
| **`wsl --status`** | WSL version, default distro, sometimes memory info. |
| **Resource Monitor** | Confirm whether pressure is WSL-wide vs rest of Windows. |

**Important:** Per-container `% CPU` in `docker stats` is **relative to host CPUs assigned to Docker**, not per physical core on the PC. Memory **LIMIT** often shows the VM cap when using Docker Desktop.

---

## 4. Recommended measurement procedure (actuals for the workbook)

Use the same **scenario name** in the Excel **Measurements** sheet each time.

### A. Record Docker Desktop settings (once per machine)

Docker Desktop → **Settings → Resources**:

- CPUs
- Memory (GB)
- Swap (GB)
- Disk image size (GB)

Copy into workbook sheet **DockerDesktop**.

### B. Record WSL2 limits (if used)

File: `%UserProfile%\.wslconfig` example:

```ini
[wsl2]
memory=16GB
processors=8
swap=8GB
```

After changes: `wsl --shutdown`, restart Docker Desktop.
Copy into workbook sheet **WSL2**.

### C. Per scenario sample (2–5 minutes each)

| Scenario | How to reproduce |
|----------|------------------|
| `idle` | Compose up, no ingest/query for 2 min |
| `ingest` | `POST /ingest/path` on `/data/sources` (or UI Ingest) |
| `query` | `POST /query` with representative text |
| `smoke` | `npm run smoke:playwright` from `web/` |

While each scenario runs, capture:

```powershell
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

Optional (host VM total):

```powershell
Get-Process vmmem -ErrorAction SilentlyContinue | Select-Object Name, @{N='WS_MB';E={[int]($_.WorkingSet64/1MB)}}
```

Enter rows in **Measurements** (timestamp, scenario, API CPU%, Qdrant CPU%, parse MEM USAGE to MB, notes).

### D. Compare to expected

Workbook sheet **Compare** computes **actual − expected** for RAM/CPU bands you maintain in **OmniKB_Expected** when you fill **Measurements**.

---

## 5. Tuning levers (without changing application code)

1. **Raise Docker Desktop memory** if ingest OOMs or WSL kills processes (vmmem pegged at limit).
2. **Add Compose limits** (future): e.g. cap Qdrant RAM so API always has headroom for embeddings — requires explicit `deploy.resources` in `docker-compose.yml`.
3. **Smaller embedding model** or external embed service — reduces API RAM (product change).
4. **Qdrant storage on fast disk** — `./data/qdrant` on SSD; avoid network drives for bind mounts.
5. **Do not run heavy non-Docker workloads inside the same WSL distro** used by Docker Desktop if you need predictable OmniKB perf.
6. **Disk space for Qdrant WAL** — If ingest returns `WAL buffer size exceeds available disk space`, that is **host/WSL/Docker disk**, not collection config. See [qdrant-wal-disk-space-troubleshooting.md](qdrant-wal-disk-space-troubleshooting.md) (capture kit + prevention).

---

## 6. OmniKB compose reference (no built-in quotas)

Current `docker-compose.yml`:

- **Published ports:** `6333` (Qdrant), `8000` (API).
- **Volumes:** Qdrant storage, sources (ro), processed, logs.
- **No** `cpus`, `mem_limit`, or `deploy.resources` — document this when explaining “unexpected” API vs Qdrant spikes.

---

## 7. Related internal docs

- `docs/user-operations-guide.md` — ingest/query/admin
- `logs/README.md` — API/UI timing logs (`X-Request-Duration-Ms`, correlation ids)
- `docs/internal-react-devtools-debugging-guide.md` — frontend debugging
- [qdrant-wal-disk-space-troubleshooting.md](qdrant-wal-disk-space-troubleshooting.md) — Qdrant `No space left on device` / WAL errors

---

## 8. Regenerating the Excel model

```powershell
python -m pip install openpyxl
python scripts/generate_docker_resource_model.py
# Output: internal_docs/docker-resource-budget-model.xlsx
```

Commit the **script** and this **markdown**; keep filled workbooks local or in team storage ( `internal_docs/` is gitignored).
