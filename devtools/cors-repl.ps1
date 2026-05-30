param(
    [string]$ApiBaseUrl = "http://localhost:8000",
    [string]$Origin = "http://localhost:5173",
    [int]$TimeoutSec = 8
)

function Test-Endpoint {
    param(
        [string]$Path,
        [string]$Method = "GET",
        [bool]$WithContentTypePreflight = $false
    )

    $url = "$ApiBaseUrl$Path"
    Write-Host "`n=== $Method $url ==="

    if ($WithContentTypePreflight) {
        $preflightHeaders = @{
            Origin = $Origin
            "Access-Control-Request-Method" = $Method
            "Access-Control-Request-Headers" = "content-type"
        }
        try {
            $pre = Invoke-WebRequest -Method Options -Uri $url -Headers $preflightHeaders -TimeoutSec $TimeoutSec -ErrorAction Stop
            Write-Host "Preflight status: $($pre.StatusCode)"
            Write-Host "Preflight ACAO: $($pre.Headers['Access-Control-Allow-Origin'])"
            Write-Host "Preflight ACAM: $($pre.Headers['Access-Control-Allow-Methods'])"
        } catch {
            if ($_.Exception.Response) {
                $resp = $_.Exception.Response
                Write-Host "Preflight status: $([int]$resp.StatusCode)"
                Write-Host "Preflight ACAO: $($resp.Headers['Access-Control-Allow-Origin'])"
            } else {
                throw
            }
        }
    }

    try {
        $headers = @{ Origin = $Origin }
        $res = Invoke-WebRequest -Method $Method -Uri $url -Headers $headers -TimeoutSec $TimeoutSec -ErrorAction Stop
        Write-Host "Request status: $($res.StatusCode)"
        Write-Host "Request ACAO: $($res.Headers['Access-Control-Allow-Origin'])"
    } catch {
        if ($_.Exception.Response) {
            $resp = $_.Exception.Response
            Write-Host "Request status: $([int]$resp.StatusCode)"
            Write-Host "Request ACAO: $($resp.Headers['Access-Control-Allow-Origin'])"
        } else {
            throw
        }
    }
}

Write-Host "CORS REPL against $ApiBaseUrl from origin $Origin"
Test-Endpoint -Path "/health" -Method "GET" -WithContentTypePreflight $true
Test-Endpoint -Path "/corpus/summary" -Method "GET" -WithContentTypePreflight $true
Test-Endpoint -Path "/corpus/sources" -Method "GET" -WithContentTypePreflight $true
