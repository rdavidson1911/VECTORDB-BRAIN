# Opens Brave to the OmniKB Vite dev server and prints React DevTools reminders.
# Usage: .\scripts\open-brave-react-dev.ps1 [-Port 5173]

param(
    [int] $Port = 5173
)

$ErrorActionPreference = 'Stop'
$url = "http://localhost:$Port/"

Write-Host "VECTORDB-BRAIN web dev URL: $url" -ForegroundColor Cyan
Write-Host ""
Write-Host "Before profiling in Brave:" -ForegroundColor Yellow
Write-Host "  1. cd web; npm run dev   (or npm run dev:fresh after vite config changes)"
Write-Host "  2. Install React Developer Tools extension"
Write-Host "  3. F12 -> Components / Profiler (Profiler needs dev build, not preview)"
Write-Host ""
Write-Host "Docs: docs/brave-react-devtools-setup.md"
Write-Host ""

$bravePaths = @(
    "${env:ProgramFiles}\BraveSoftware\Brave-Browser\Application\brave.exe",
    "${env:ProgramFiles(x86)}\BraveSoftware\Brave-Browser\Application\brave.exe",
    "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\Application\brave.exe"
)

$brave = $bravePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($brave) {
    Start-Process -FilePath $brave -ArgumentList $url
} else {
    Write-Warning "Brave not found; open manually: $url"
    Start-Process $url
}
