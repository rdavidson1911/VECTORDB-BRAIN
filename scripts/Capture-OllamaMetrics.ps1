#Requires -Version 7.0
<#
.SYNOPSIS
    Benchmarks local Ollama models and captures performance + memory metrics to CSV.

.DESCRIPTION
    For each target model, sends a standard benchmark prompt via the Ollama REST API
    and captures: token throughput, latency breakdown, process RAM, GPU VRAM,
    and GPU utilisation. Results are appended to a CSV safe for Power Query ingestion.

    Security posture:
      - All traffic stays on localhost (127.0.0.1:11434) — never routed externally.
      - Prompt text is SHA-256 hashed in the output; raw text is never written to disk.
      - No credentials, keys, or auth headers are required or stored.
      - Output CSV is written to the user profile tree, not a shared path.

.PARAMETER Models
    List of Ollama model names to benchmark. Defaults to all local (non-cloud) models.

.PARAMETER OutputDir
    Directory for CSV output. Defaults to $env:USERPROFILE\OllamaMetrics.

.PARAMETER Prompts
    Hashtable of prompt labels to prompt strings used for benchmarking.
    Defaults to three built-in synthetic prompts (short / medium / reasoning).

.PARAMETER WarmupRuns
    Number of throwaway runs before recording. Warms the model into VRAM. Default 1.

.PARAMETER RepeatRuns
    Number of timed runs per model per prompt. Averages are written. Default 3.

.EXAMPLE
    .\Capture-OllamaMetrics.ps1
    .\Capture-OllamaMetrics.ps1 -Models @("llama3.2:latest","qwen2.5-coder:7b") -RepeatRuns 5
#>

[CmdletBinding()]
param(
    [string[]]  $Models      = @(),
    [string]    $OutputDir   = "$env:USERPROFILE\OllamaMetrics",
    [hashtable] $Prompts     = @{},
    [int]       $WarmupRuns  = 1,
    [int]       $RepeatRuns  = 3
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
$OLLAMA_BASE  = 'http://127.0.0.1:11434'
$CSV_FILE     = Join-Path $OutputDir 'ollama_metrics.csv'
$LOG_FILE     = Join-Path $OutputDir 'ollama_metrics.log'
$TIMESTAMP_FMT = 'yyyy-MM-dd HH:mm:ss'

# ---------------------------------------------------------------------------
# Default benchmark prompts  (label → prompt text)
# ---------------------------------------------------------------------------
$DefaultPrompts = [ordered]@{
    'short_factual'  = 'In one sentence, what is the capital of France?'
    'medium_explain' = 'Explain how a transformer neural network works in three concise paragraphs.'
    'reasoning'      = 'A farmer has 17 sheep. All but 9 die. How many sheep does the farmer have left? Show your reasoning step by step.'
}
if ($Prompts.Count -eq 0) { $Prompts = $DefaultPrompts }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $entry = "[$(Get-Date -Format $TIMESTAMP_FMT)] [$Level] $Message"
    Add-Content -Path $LOG_FILE -Value $entry
    switch ($Level) {
        'WARN'  { Write-Warning $Message }
        'ERROR' { Write-Error   $Message }
        default { Write-Host    $entry -ForegroundColor Cyan }
    }
}

function Get-SHA256 ([string]$Text) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hash  = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString('x2') }) -join ''
}

function Get-GpuMetrics {
    try {
        $raw = nvidia-smi `
            --query-gpu=name,memory.used,memory.free,memory.total,utilization.gpu,temperature.gpu `
            --format=csv,noheader,nounits 2>$null

        if (-not $raw) { return $null }

        # Take first GPU line only
        $parts = ($raw -split "`n")[0] -split ',\s*'
        return [pscustomobject]@{
            GpuName          = $parts[0].Trim()
            VramUsedMB       = [int]$parts[1]
            VramFreeMB       = [int]$parts[2]
            VramTotalMB      = [int]$parts[3]
            GpuUtilizationPct = [int]$parts[4]
            GpuTempC         = [int]$parts[5]
        }
    } catch {
        return $null
    }
}

function Get-OllamaProcessMemoryMB {
    $proc = Get-Process -Name 'ollama' -ErrorAction SilentlyContinue |
            Sort-Object WorkingSet64 -Descending |
            Select-Object -First 1
    if (-not $proc) { return 0 }
    return [math]::Round($proc.WorkingSet64 / 1MB, 1)
}

function Get-OllamaVramMB ([string]$ModelName) {
    try {
        $ps = Invoke-RestMethod "$OLLAMA_BASE/api/ps" -TimeoutSec 5
        $entry = $ps.models | Where-Object { $_.name -eq $ModelName } | Select-Object -First 1
        if ($entry -and $entry.size_vram) {
            return [math]::Round($entry.size_vram / 1MB, 1)
        }
    } catch { }
    return 0
}

function Get-SystemRamUsedMB {
    $os = Get-CimInstance Win32_OperatingSystem
    return [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1KB, 1)
}

function Invoke-OllamaBenchmark {
    param(
        [string]$ModelName,
        [string]$PromptText,
        [int]   $TimeoutSec = 300
    )

    $body = @{
        model  = $ModelName
        prompt = $PromptText
        stream = $false
        options = @{ temperature = 0.0 }   # deterministic for benchmarking
    } | ConvertTo-Json -Compress

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $response = Invoke-RestMethod `
        -Uri             "$OLLAMA_BASE/api/generate" `
        -Method          POST `
        -Body            $body `
        -ContentType     'application/json' `
        -TimeoutSec      $TimeoutSec
    $sw.Stop()

    # Ollama returns durations in nanoseconds
    $ns = 1e9
    return [pscustomobject]@{
        WallClockMs         = [math]::Round($sw.Elapsed.TotalMilliseconds, 1)
        TotalDurationMs     = [math]::Round($response.total_duration    / $ns * 1000, 1)
        LoadDurationMs      = [math]::Round($response.load_duration     / $ns * 1000, 1)
        PromptEvalDurationMs= [math]::Round($response.prompt_eval_duration / $ns * 1000, 1)
        GenDurationMs       = [math]::Round($response.eval_duration     / $ns * 1000, 1)
        PromptTokenCount    = $response.prompt_eval_count
        GenTokenCount       = $response.eval_count
        TokensPerSec        = if ($response.eval_duration -gt 0) {
                                  [math]::Round($response.eval_count / ($response.eval_duration / $ns), 2)
                              } else { 0 }
        PromptTokensPerSec  = if ($response.prompt_eval_duration -gt 0) {
                                  [math]::Round($response.prompt_eval_count / ($response.prompt_eval_duration / $ns), 2)
                              } else { 0 }
        ResponseLength      = $response.response.Length
        Done                = $response.done
        DoneReason          = $response.done_reason
    }
}

# ---------------------------------------------------------------------------
# Resolve model list  (skip cloud/remote models — no local memory to measure)
# ---------------------------------------------------------------------------
function Get-LocalModels {
    $tags = Invoke-RestMethod "$OLLAMA_BASE/api/tags" -TimeoutSec 10
    return $tags.models |
           Where-Object { $_.size -gt 1MB } |   # cloud stubs are a few hundred bytes
           Select-Object -ExpandProperty name
}

# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------
$CsvHeaders = @(
    'RunId','Timestamp','ModelName','ModelFamily','ParameterSize','QuantLevel',
    'PromptLabel','PromptHash','WarmupRuns','RepeatRuns',
    'AvgWallClockMs','AvgTotalDurationMs','AvgLoadDurationMs',
    'AvgPromptEvalMs','AvgGenDurationMs',
    'AvgPromptTokenCount','AvgGenTokenCount',
    'AvgTokensPerSec','AvgPromptTokensPerSec','AvgResponseLength',
    'OllamaProcessRamMB','OllamaModelVramMB',
    'SystemRamUsedMB',
    'GpuName','VramUsedMB','VramFreeMB','VramTotalMB','GpuUtilizationPct','GpuTempC',
    'Notes'
)

function Initialize-Csv {
    if (-not (Test-Path $CSV_FILE)) {
        ($CsvHeaders -join ',') | Set-Content -Path $CSV_FILE -Encoding UTF8
        Write-Log "Created CSV: $CSV_FILE"
    }
}

function Write-MetricRow ([hashtable]$Row) {
    $line = ($CsvHeaders | ForEach-Object {
        $val = $Row[$_]
        if ($null -eq $val) { $val = '' }
        # Quote if contains comma
        if ($val -match ',') { "`"$val`"" } else { $val }
    }) -join ','
    Add-Content -Path $CSV_FILE -Value $line -Encoding UTF8
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}
Initialize-Csv

# Resolve model list
if ($Models.Count -eq 0) {
    Write-Log 'No models specified — discovering local models...'
    $Models = Get-LocalModels
    Write-Log "Found $($Models.Count) local model(s): $($Models -join ', ')"
}

# Pull model metadata once
$modelMeta = @{}
try {
    $tags = Invoke-RestMethod "$OLLAMA_BASE/api/tags" -TimeoutSec 10
    foreach ($m in $tags.models) {
        $modelMeta[$m.name] = $m
    }
} catch {
    Write-Log 'Could not fetch model tags — metadata fields will be empty.' 'WARN'
}

foreach ($model in $Models) {
    Write-Log "=== Model: $model ==="

    $meta   = if ($modelMeta.ContainsKey($model)) { $modelMeta[$model] } else { $null }
    $family = if ($meta -and $meta.details -and $meta.details.family)              { $meta.details.family }              else { '' }
    $pSize  = if ($meta -and $meta.details -and $meta.details.parameter_size)      { $meta.details.parameter_size }      else { '' }
    $quant  = if ($meta -and $meta.details -and $meta.details.quantization_level)  { $meta.details.quantization_level }  else { '' }

    foreach ($promptLabel in $Prompts.Keys) {
        $promptText = $Prompts[$promptLabel]
        $promptHash = Get-SHA256 $promptText
        Write-Log "  Prompt: $promptLabel"

        # --- Warmup (results discarded) ---
        for ($w = 0; $w -lt $WarmupRuns; $w++) {
            Write-Log "    Warmup run $($w+1)/$WarmupRuns (cold load may take up to 5 min)..."
            try { Invoke-OllamaBenchmark -ModelName $model -PromptText $promptText -TimeoutSec 600 | Out-Null }
            catch { Write-Log "    Warmup failed (non-fatal): $_" 'WARN' }
        }

        # --- Timed runs ---
        $runs = [System.Collections.Generic.List[pscustomobject]]::new()
        for ($r = 0; $r -lt $RepeatRuns; $r++) {
            Write-Log "    Timed run $($r+1)/$RepeatRuns..."
            try {
                $result = Invoke-OllamaBenchmark -ModelName $model -PromptText $promptText
                $runs.Add($result)
            } catch {
                Write-Log "    Run failed: $_" 'WARN'
            }
        }

        if ($runs.Count -eq 0) {
            Write-Log "  All runs failed for $model / $promptLabel — skipping." 'ERROR'
            continue
        }

        # --- Averages ---
        $avg = [pscustomobject]@{
            WallClockMs          = [math]::Round(($runs.WallClockMs         | Measure-Object -Average).Average, 1)
            TotalDurationMs      = [math]::Round(($runs.TotalDurationMs     | Measure-Object -Average).Average, 1)
            LoadDurationMs       = [math]::Round(($runs.LoadDurationMs      | Measure-Object -Average).Average, 1)
            PromptEvalMs         = [math]::Round(($runs.PromptEvalDurationMs| Measure-Object -Average).Average, 1)
            GenDurationMs        = [math]::Round(($runs.GenDurationMs       | Measure-Object -Average).Average, 1)
            PromptTokenCount     = [math]::Round(($runs.PromptTokenCount    | Measure-Object -Average).Average, 0)
            GenTokenCount        = [math]::Round(($runs.GenTokenCount       | Measure-Object -Average).Average, 0)
            TokensPerSec         = [math]::Round(($runs.TokensPerSec        | Measure-Object -Average).Average, 2)
            PromptTokensPerSec   = [math]::Round(($runs.PromptTokensPerSec  | Measure-Object -Average).Average, 2)
            ResponseLength       = [math]::Round(($runs.ResponseLength      | Measure-Object -Average).Average, 0)
        }

        # --- System snapshot (taken once after last timed run) ---
        $gpu       = Get-GpuMetrics
        $procRam   = Get-OllamaProcessMemoryMB
        $modelVram = Get-OllamaVramMB -ModelName $model
        $sysRam    = Get-SystemRamUsedMB

        $row = @{
            RunId                = [guid]::NewGuid().ToString()
            Timestamp            = Get-Date -Format $TIMESTAMP_FMT
            ModelName            = $model
            ModelFamily          = $family
            ParameterSize        = $pSize
            QuantLevel           = $quant
            PromptLabel          = $promptLabel
            PromptHash           = $promptHash.Substring(0, 16)   # 16-char prefix sufficient for audit
            WarmupRuns           = $WarmupRuns
            RepeatRuns           = $runs.Count
            AvgWallClockMs       = $avg.WallClockMs
            AvgTotalDurationMs   = $avg.TotalDurationMs
            AvgLoadDurationMs    = $avg.LoadDurationMs
            AvgPromptEvalMs      = $avg.PromptEvalMs
            AvgGenDurationMs     = $avg.GenDurationMs
            AvgPromptTokenCount  = $avg.PromptTokenCount
            AvgGenTokenCount     = $avg.GenTokenCount
            AvgTokensPerSec      = $avg.TokensPerSec
            AvgPromptTokensPerSec= $avg.PromptTokensPerSec
            AvgResponseLength    = $avg.ResponseLength
            OllamaProcessRamMB   = $procRam
            OllamaModelVramMB    = $modelVram
            SystemRamUsedMB      = $sysRam
            GpuName              = if ($gpu) { $gpu.GpuName }           else { '' }
            VramUsedMB           = if ($gpu) { $gpu.VramUsedMB }        else { '' }
            VramFreeMB           = if ($gpu) { $gpu.VramFreeMB }        else { '' }
            VramTotalMB          = if ($gpu) { $gpu.VramTotalMB }       else { '' }
            GpuUtilizationPct    = if ($gpu) { $gpu.GpuUtilizationPct } else { '' }
            GpuTempC             = if ($gpu) { $gpu.GpuTempC }          else { '' }
            Notes                = ''
        }

        Write-MetricRow -Row $row
        Write-Log "  Recorded: $($avg.TokensPerSec) tok/s | VRAM $($gpu?.VramUsedMB)/$($gpu?.VramTotalMB) MB | ProcRAM ${procRam} MB"
    }

    # Unload model from VRAM between models to get clean memory readings
    try {
        Invoke-RestMethod "$OLLAMA_BASE/api/generate" `
            -Method POST `
            -Body (@{ model = $model; keep_alive = '0' } | ConvertTo-Json) `
            -ContentType 'application/json' `
            -TimeoutSec 10 | Out-Null
        Write-Log "  Unloaded $model from VRAM."
    } catch {
        Write-Log "  Could not unload $model (non-fatal)." 'WARN'
    }
}

Write-Log "Done. Results written to: $CSV_FILE"
Write-Host "`nCSV path: $CSV_FILE" -ForegroundColor Green
