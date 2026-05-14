param(
    [string]$ApiBase = "http://localhost:8000",
    [string]$SamplePath = "/data/sources"
)

$ErrorActionPreference = "Stop"

Write-Host "Checking Docker services..."
docker compose ps

Write-Host "Checking API health..."
$health = Invoke-RestMethod -Method Get -Uri "$ApiBase/health"
$health | ConvertTo-Json -Depth 4

Write-Host "Running sample ingest..."
$ingestBody = @{ path = $SamplePath; recursive = $true } | ConvertTo-Json
$ingest = Invoke-RestMethod -Method Post -Uri "$ApiBase/ingest/path" -ContentType "application/json" -Body $ingestBody
$ingest | ConvertTo-Json -Depth 4

Write-Host "Running sample query..."
$queryBody = @{ query = "What documents are in this knowledge base?"; limit = 3 } | ConvertTo-Json
$query = Invoke-RestMethod -Method Post -Uri "$ApiBase/query" -ContentType "application/json" -Body $queryBody
$query | ConvertTo-Json -Depth 6

Write-Host "Smoke test complete."
