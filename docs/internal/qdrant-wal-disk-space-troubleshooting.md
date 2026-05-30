# Qdrant WAL / disk space errors (OmniKB)

**Audience:** Operators and developers running `omnikb-qdrant` via [docker-compose.yml](../../docker-compose.yml).
**Related:** [docker-desktop-wsl2-resources.md](docker-desktop-wsl2-resources.md), [../data-curation-pipeline.md](../data-curation-pipeline.md), local notes in `internal_docs/qdrant-ingested-data-where-it-lives.md`.

---

## Error we encountered

During ingest or upsert, the API or Qdrant client may surface:

```json
{
  "error": "Service internal error: No space left on device: WAL buffer size exceeds available disk space"
}
```

HTTP status is often **500** from the API when Qdrant rejects the write. Health may still report `qdrant: ok` until the next failing write.

**What it is not**

- Not a misconfiguration of the **`omnikb_documents`** collection name or vector size (384-dim cosine is unrelated).
- Not fixed by “allowing specific example collection data” in Docker — there is no per-collection disk grant in our compose file.

**What it is**

- Qdrant refuses to grow its **write-ahead log (WAL)** and/or persist segments because the filesystem backing **`/qdrant/storage`** does not report enough **free space** for the WAL buffer Qdrant expects at that moment.

Our stack maps storage as:

```yaml
# docker-compose.yml
volumes:
  - ${QDRANT_STORAGE_PATH:-./data/qdrant}:/qdrant/storage
```

Default host path: `./data/qdrant` (e.g. `I:\VECTORDB-BRAIN\data\qdrant`).

---

## Investigation status

| When | What we did | Result |
|------|-------------|--------|
| First report | Config review only; host disk commands interrupted | **Root cause not confirmed at failure time** |
| Follow-up (2026-05-25) | `df` inside `omnikb-qdrant`, host `I:` free space, folder size | **~478 GB free** on mount, **~0.9 GB** used under `/qdrant/storage` |

So the error may have been **environmental at the time of failure** (since resolved), or **intermittent** (Docker/WSL disk image, different `QDRANT_STORAGE_PATH`, heavy ingest spike). Document captures **theories** and **how to prove** the next occurrence.

---

## Theories (possible / likely causes)

### Likely

1. **Host volume actually full (or nearly full) during ingest**
   Large PDF corpora → many chunks → WAL + new segments grow quickly. If `I:` (or whatever drive backs `QDRANT_STORAGE_PATH`) was low on space, Qdrant fails with this message.

2. **Docker Desktop WSL2 virtual disk full**
   Docker stores images/layers/containers in a WSL2 **disk image**. That pool can fill even when a bind-mounted Windows drive (`I:\`) shows plenty of free space. Symptoms: random pull/build failures, other containers failing, or inconsistent behavior under heavy I/O.

3. **Wrong or moved `QDRANT_STORAGE_PATH`**
   `.env` pointing at a small/full drive, USB stick, or network path with quota. After changing `.env`, a **new empty** `data/qdrant` can make it look like “ingest worked before but data vanished” while the real issue was writing to a different path that later filled or was deleted.

### Possible

4. **Transient spike during bulk upsert**
   WAL grows before compaction/flush; rare edge cases if free space is borderline (e.g. &lt; 1–2 GB) and many parallel writes occur.

5. **Container wrote to ephemeral layer**
   If Qdrant ran **without** the bind mount (one-off `docker run`, old compose, manual container), storage uses the container filesystem (small). Our standard compose uses the bind mount — verify with `docker inspect omnikb-qdrant` → Mounts.

6. **Permission or mount not visible inside container**
   Less common on Docker Desktop with `I:\` bind mounts; if `df` inside the container shows **0** avail or wrong filesystem, treat as mount issue.

### Unlikely for this project (but check if symptoms persist)

7. **Qdrant `wal_capacity_mb` mis-set** to a value larger than reported free space (custom `config.yaml` not in default compose).
8. **Collection-specific** Docker “allow list” — **not used** in OmniKB; no change needed for `omnikb_documents` alone.

---

## Capture kit (run when the error happens)

Run these **immediately** while the failure is reproducible (copy output into an incident note or `devtools/error-tracking-db.md`).

### 1. Inside Qdrant container (authoritative for Qdrant)

```powershell
docker exec omnikb-qdrant df -h /qdrant/storage
docker exec omnikb-qdrant sh -c "du -sh /qdrant/storage && du -sh /qdrant/storage/* 2>/dev/null | sort -h | tail -20"
docker logs omnikb-qdrant --tail 80
```

Record: **Avail**, **Use%**, **du** total, and any log lines mentioning `WAL`, `No space left`, `panic`, `io error`.

### 2. Host path (same bind mount)

```powershell
$root = "I:\VECTORDB-BRAIN\data\qdrant"   # or your QDRANT_STORAGE_PATH
Get-PSDrive (Split-Path $root -Qualifier) | Select-Object Name, @{N='FreeGB';E={[math]::Round($_.Free/1GB,2)}}
if (Test-Path $root) {
  (Get-ChildItem $root -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1GB
}
```

### 3. Docker disk pool

```powershell
docker system df -v
```

Note: **Images** / **Local Volumes** reclaimable space. If **Build cache** or images are huge, prune only after you understand what you are deleting.

### 4. Compose / env proof

```powershell
docker inspect omnikb-qdrant --format "{{json .Mounts}}"
Get-Content .env | Select-String QDRANT
```

Confirm mount **Destination** `/qdrant/storage` and **Source** matches intended host folder.

### 5. API context

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/corpus/summary
docker compose logs api --tail 40
```

Note whether failure was **`/ingest/path`**, **`/ingest/file`**, or upsert during smoke seed.

### Incident note template

```markdown
## Incident QDRANT-WAL-DISK-YYYY-MM-DD

- Timestamp (UTC):
- Operation: ingest path | ingest file | query | other
- Error text: (paste full JSON/message)
- df in container: (paste)
- Host drive free GB:
- data/qdrant size GB:
- docker system df: (paste summary)
- QDRANT_STORAGE_PATH from .env:
- Theory confirmed: yes/no — which #
- Resolution applied:
```

---

## Resolution strategies

### Immediate (restore writes)

1. **Free space on the filesystem shown by `df` inside the container**
   - Delete unneeded files on that drive.
   - Move `data/qdrant` only with Qdrant **stopped** (`docker compose stop qdrant`), copy tree, update `QDRANT_STORAGE_PATH`, start again.

2. **Reclaim Docker disk** (if `docker system df` shows pressure)
   ```powershell
   docker system prune -f          # unused containers/networks
   # docker image prune -a       # aggressive — removes unused images
   ```
   Increase **Docker Desktop → Settings → Resources → Disk image size** if the VHD is capped and full.

3. **Restart Qdrant after space is free**
   ```powershell
   docker compose restart qdrant
   ```
   Retry a **small** ingest (one small `.txt`) before full corpus.

4. **If storage is corrupted or unrecoverable**
   Stop Qdrant, backup then clear `data/qdrant` (see gitignore policy), start Qdrant, **re-ingest** from `data/sources` (`skip_unchanged` as needed).

### Preventive

| Strategy | Action |
|----------|--------|
| **Monitor free space** | Alert or manual check: host drive for `QDRANT_STORAGE_PATH` and `df` in container before large ingest. |
| **Keep Qdrant on a large local SSD** | Avoid network drives and tiny USB volumes for `QDRANT_STORAGE_PATH`. |
| **Docker Desktop disk budget** | Periodically review disk image size vs usage; prune images; extend cap before full. |
| **Staged ingest** | Ingest subtrees or `skip_unchanged: true` after first full pass; avoids repeated WAL pressure. |
| **Document `.env`** | Commit `.env.example`; never point `QDRANT_STORAGE_PATH` at a full disk without team awareness. |
| **Verify mount after changes** | After compose/env edits, always run `docker exec omnikb-qdrant df -h /qdrant/storage`. |

### Optional (advanced)

- **Compose disk limits** — Docker does not give Qdrant “more disk”; only host/WSL space matters for bind mounts.
- **Separate disk for vectors** — Dedicated drive or partition for `data/qdrant` only.
- **Qdrant tuning** — Custom config for WAL size only after reading [Qdrant storage docs](https://qdrant.tech/documentation/guides/configuration/); not required for default OmniKB compose.

---

## How this ties to “empty collection” symptoms

WAL/disk failures during ingest can leave:

- **Zero points** in `omnikb_documents` (failed upserts), while
- **Source files** still present under `data/sources`.

That is separate from “we deleted `data/qdrant`” or `QDRANT_STORAGE_PATH` changed. See `internal_docs/qdrant-ingested-data-where-it-lives.md`.

---

## Quick decision tree

```text
Error: WAL buffer size exceeds available disk space
  │
  ├─ docker exec … df /qdrant/storage → Avail ≈ 0 or very low?
  │     YES → Free host drive OR fix QDRANT_STORAGE_PATH → restart qdrant → re-ingest
  │
  ├─ Host drive has GB free but error persists?
  │     → docker system df, Docker Desktop disk image, WSL restart
  │
  └─ df shows plenty free (e.g. 100+ GB) but error once?
        → Historical/full disk since fixed; keep capture kit for next time
```

---

## Changelog

| Date | Note |
|------|------|
| 2026-05-25 | Initial doc: error text, theories, capture kit, resolution; follow-up diag ~478 GB free / ~0.9 GB qdrant data |
