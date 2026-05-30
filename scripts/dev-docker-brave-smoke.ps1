#Requires -Version 5.1
<#
.SYNOPSIS
  Bring up the Docker API + Qdrant stack, wait for health, optionally run API smoke, then print UI steps for Brave.

.DESCRIPTION
  Use this on branch test/docker-brave-smoke (or any checkout at the same HEAD) before pushing to GitHub.
  The React app lives under web/ (untracked in Manifest A); install deps once, then run the Vite dev server
  and open Brave at http://localhost:5173.

.PARAMETER ApiBase
  Base URL for the FastAPI service (default http://localhost:8000).

.PARAMETER SkipSmoke
  If set, skip scripts/smoke-test.ps1 after health is OK (faster when you only need containers + UI).

.PARAMETER HealthTimeoutSeconds
  Max seconds to poll GET /health before failing (default 300; first model pull can be slow).
#>
param(
    [string]$ApiBase = "http://localhost:8000",
    [switch]$SkipSmoke,
    [int]$HealthTimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path (Join-Path $repoRoot ".env"))) {
    Write-Error "Missing .env in repo root. Run: Copy-Item .env.example .env"
}

Write-Host "Tip: For Playwright smoke, set INGEST_TIMEOUT_MS and QUERY_TIMEOUT_MS (e.g. 120000) if cold-start embed is slow." -ForegroundColor DarkGray

Write-Host "Starting Docker stack (api + qdrant)..." -ForegroundColor Cyan
docker compose up --build -d
if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed with exit code $LASTEXITCODE"
}

$deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    try {
        $h = Invoke-RestMethod -Method Get -Uri "$ApiBase/health" -TimeoutSec 8
        if ($null -ne $h.service -and $h.service.ToString().ToLowerInvariant() -eq "ok") {
            Write-Host "API health OK:" -ForegroundColor Green
            $h | ConvertTo-Json -Depth 6
            $healthy = $true
            break
        }
    } catch {
        Write-Host "Waiting for API at $ApiBase/health ... ($($_.Exception.Message))"
    }
    Start-Sleep -Seconds 4
}

if (-not $healthy) {
    Write-Host "docker compose ps:" -ForegroundColor Yellow
    docker compose ps
    throw "API did not become healthy within $HealthTimeoutSeconds s. Check: docker compose logs api"
}

if (-not $SkipSmoke) {
    Write-Host "Running scripts/smoke-test.ps1 ..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\smoke-test.ps1") -ApiBase $ApiBase
}

Write-Host ""
Write-Host "=== Next: React UI in Brave ===" -ForegroundColor Green
Write-Host "1. In a second terminal (repo root): npm run web:install"
Write-Host "2. Then: npm run web:dev"
Write-Host "3. Open Brave: http://localhost:5173  (or http://127.0.0.1:5173 — both are in CORS_ALLOWED_ORIGINS in .env.example)"
Write-Host "4. In the UI: trigger ingest for /data/sources if needed, then run a query and confirm result cards."
Write-Host ""
Write-Host "Optional: npm run smoke:playwright (requires Playwright browsers: npx playwright install)"
Write-Host "Stop stack when done: docker compose down"
