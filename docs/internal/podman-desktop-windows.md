# Podman Desktop on Windows 11 Pro (OmniKB + Qdrant)

**Audience:** Internal team
**Stack:** `omnikb-api` + `omnikb-qdrant` via [docker-compose.yml](../../docker-compose.yml)
**Related:** [docker-desktop-wsl2-resources.md](docker-desktop-wsl2-resources.md), [qdrant-wal-disk-space-troubleshooting.md](qdrant-wal-disk-space-troubleshooting.md)

---

## 1. Role of Podman Desktop

- **Podman Desktop** — container lifecycle GUI (Images, Containers, Logs, resource view).
- **Qdrant dashboard** — `http://127.0.0.1:6333/dashboard` (collections, cluster UI).
- **OmniKB API** — `http://127.0.0.1:8000/health`.

Compose publishes API and Qdrant on **loopback only** (`127.0.0.1`) in `docker-compose.yml` (same idea as the mailcatcher bindings).

---

## 2. Prerequisites

- Podman Desktop installed; default **Podman machine** (WSL) **Running**.
- Quit **Docker Desktop** when using OmniKB so ports `6333` / `8000` are not contested.
- Recommended machine sizing (Podman Desktop → Settings → Resources): **8 GB+ RAM**, **4+ CPUs**, adequate disk for images and `data/qdrant`. Cold ingest needs headroom for the API embedder and Qdrant upserts (see Docker WSL resource doc).

Verify:

```powershell
podman version
podman machine list
```

### 2.1 Single Podman CLI on Windows (avoid duplicate installs)

Podman Desktop and Chocolatey can both install `podman.exe`. Multiple clients on PATH cause Podman Desktop / IDE warnings and version skew against the **podman-machine** VM.

**Canonical client for OmniKB:** Podman Desktop bundle:

```text
%LOCALAPPDATA%\Programs\Podman\podman.exe
```

**Workstation setup:**

1. **Remove duplicate (preferred):** `choco uninstall podman-cli -y` when you use Podman Desktop only (run an **elevated** PowerShell if Chocolatey reports access denied).
2. **Or** reorder User `Path` so `%LOCALAPPDATA%\Programs\Podman\` appears **before** `C:\ProgramData\chocolatey\bin` (OmniKB automation prepends this User path when you run the verify block below).
3. **Pin IDE / Dev Containers extension** — merge [config/vscode-podman-recommended.settings.json](../../config/vscode-podman-recommended.settings.json) into workspace `.vscode/settings.json` (local; folder is gitignored) or Cursor/VS Code user settings. In **Podman Desktop**, set the custom binary path to the same `podman.exe` if the entry screen warns about multiple installations.
4. **Pin scripts (optional):** `$env:PODMAN_BIN = "$env:LOCALAPPDATA\Programs\Podman\podman.exe"` in your PowerShell profile, or per session before compose.

**Verify one effective client:**

```powershell
Get-Command podman -All | Format-Table Name, Source -AutoSize
(Get-Command podman).Source
& "$env:LOCALAPPDATA\Programs\Podman\podman.exe" version
podman machine inspect podman-machine-default --format '{{.ConnectionInfo.PodmanPipe.Path}}'
```

[`Invoke-OmniKBCompose.ps1`](../../scripts/Invoke-OmniKBCompose.ps1) prefers `PODMAN_BIN`, then the Desktop default path, then PATH.

---

## 3. Compose on Windows (`DOCKER_HOST`)

`podman compose` may delegate to the Windows `docker-compose.exe` provider. Point it at the Podman machine pipe before compose/build:

```powershell
$env:DOCKER_HOST = 'npipe:////./pipe/podman-machine-default'
cd I:\VECTORDB-BRAIN
```

Use the helper script (sets `DOCKER_HOST` for the session):

```powershell
.\scripts\Invoke-OmniKBCompose.ps1 up -d
```

**Build API image** (if `compose up --build` hangs, build with Podman directly):

```powershell
$env:DOCKER_HOST = 'npipe:////./pipe/podman-machine-default'
podman build -t localhost/vectordb-brain-api:latest -f Dockerfile .
podman tag localhost/vectordb-brain-api:latest vectordb-brain-api:latest
podman compose up -d
```

**Pre-pull Qdrant** (pinned in compose):

```powershell
podman pull docker.io/qdrant/qdrant:v1.17.1
```

---

## 4. Bind mounts from `I:\`

If Qdrant storage appears empty after ingest, run compose from WSL against the mounted repo:

```bash
cd /mnt/i/VECTORDB-BRAIN
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock   # if needed inside WSL
podman compose up -d
```

Success: files under `data/qdrant` on the host grow on ingest; `podman compose restart qdrant` keeps collections (`GET /health` still reports `qdrant: ok`).

---

## 5. Security defaults

| Topic | Practice |
|--------|----------|
| Ports | `127.0.0.1:6333`, `127.0.0.1:8000` in compose |
| Secrets | `.env` gitignored; use `.env.example` as template |
| Corpus | `data/sources` mounted read-only in compose |
| Curation | `CURATION_GATE_ENABLED=true`, `CURATION_ALLOW_OVERRIDE=false` on main |
| Qdrant auth | Not enabled in compose; do not expose 6333 on LAN without API keys + TLS |

Optional local override pattern: [compose.override.example.yml](../../compose.override.example.yml) (gitignored `compose.override.yml` only if you fork port settings).

---

## 6. Research Qdrant (port 6334)

Never point research jobs at production **6333**. Use loopback **6334**:

```powershell
podman run -d --name qdrant-research `
  -p 127.0.0.1:6334:6333 `
  -v qdrant_research_data:/qdrant/storage `
  qdrant/qdrant:latest
```

One-off benchmark containers that used `host.docker.internal` on Docker should use `host.containers.internal` or compose `extra_hosts: host.docker.internal:host-gateway` (see [embedding-model-comparison.md](../research/embedding-model-comparison.md)).

Makefile: `make research-qdrant-up` / `make research-qdrant-down` with `CONTAINER_CLI=podman`.

---

## 7. Day-to-day commands

```powershell
$env:DOCKER_HOST = 'npipe:////./pipe/podman-machine-default'
podman compose ps
podman compose logs -f qdrant
podman stats
podman compose down
Invoke-RestMethod http://127.0.0.1:8000/health
```

---

## 8. GUI workflow

1. Podman Desktop → **Images** — confirm `qdrant/qdrant:v1.17.1` and `vectordb-brain-api`.
2. **Containers** — `omnikb-qdrant`, `omnikb-api` → Logs / Restart.
3. Browser — Qdrant dashboard and API health URLs above.
