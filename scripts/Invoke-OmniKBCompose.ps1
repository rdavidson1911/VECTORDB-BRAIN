#Requires -Version 5.1
<#
.SYNOPSIS
  Run podman compose for OmniKB with DOCKER_HOST set to the Podman machine (Windows).
.DESCRIPTION
  Resolves podman.exe in order: $env:PODMAN_BIN, Podman Desktop default path,
  then first podman on PATH. Set PODMAN_BIN to pin the client (see docs/internal/podman-desktop-windows.md).
.EXAMPLE
  .\scripts\Invoke-OmniKBCompose.ps1 up -d
  .\scripts\Invoke-OmniKBCompose.ps1 ps
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposeArgs
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Get-OmniKBPodmanExecutable {
    if ($env:PODMAN_BIN) {
        if (-not (Test-Path -LiteralPath $env:PODMAN_BIN)) {
            throw "PODMAN_BIN is set but not found: $env:PODMAN_BIN"
        }
        return (Resolve-Path -LiteralPath $env:PODMAN_BIN).Path
    }

    $desktopDefault = Join-Path $env:LOCALAPPDATA 'Programs\Podman\podman.exe'
    if (Test-Path -LiteralPath $desktopDefault) {
        return (Resolve-Path -LiteralPath $desktopDefault).Path
    }

    $onPath = Get-Command podman -ErrorAction SilentlyContinue
    if ($onPath) {
        return $onPath.Source
    }

    throw 'podman CLI not found. Start Podman Desktop or set PODMAN_BIN to podman.exe.'
}

$podmanExe = Get-OmniKBPodmanExecutable

$machineName = 'podman-machine-default'
$pipePath = & $podmanExe machine inspect --format '{{.ConnectionInfo.PodmanPipe.Path}}' $machineName 2>$null
if ($pipePath) {
    $pipeName = $pipePath -replace '^\\\\\.\\pipe\\', ''
    $env:DOCKER_HOST = "npipe:////./pipe/$pipeName"
}

if ($ComposeArgs.Count -eq 0) {
    $ComposeArgs = @('ps')
}

& $podmanExe compose @ComposeArgs
exit $LASTEXITCODE
