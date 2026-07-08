#Requires -Version 5.1
<#
.SYNOPSIS
  Start MailCatcher for local dev (SMTP + web UI), bound to localhost only.

.DESCRIPTION
  Uses Docker Compose profile dev-mail. SMTP: 127.0.0.1:1025, UI: http://127.0.0.1:1080

.EXAMPLE
  .\scripts\Start-MailCatcher.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not on PATH. Install Docker Desktop or use Ruby MailCatcher (see docs/dev-mailcatcher.md)."
}

docker compose --profile dev-mail up -d mailcatcher
Write-Host ""
Write-Host "MailCatcher is running (localhost only)." -ForegroundColor Green
$smtpPort = if ($env:MAILCATCHER_SMTP_PORT) { $env:MAILCATCHER_SMTP_PORT } else { "1025" }
$webPort = if ($env:MAILCATCHER_WEB_PORT) { $env:MAILCATCHER_WEB_PORT } else { "1081" }
Write-Host "  SMTP:    127.0.0.1:$smtpPort  (no TLS, no auth — dev only)" -ForegroundColor Cyan
Write-Host "  Web UI:  http://127.0.0.1:$webPort" -ForegroundColor Cyan
Write-Host ""
Write-Host "Stop:  docker compose --profile dev-mail stop mailcatcher" -ForegroundColor DarkGray
