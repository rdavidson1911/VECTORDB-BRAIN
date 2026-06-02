#Requires -Version 5.1
<#
.SYNOPSIS
  SMTP learning lab CLI (mock sends + MailCatcher API list/clear).

.EXAMPLE
  .\scripts\Invoke-SmtpLab.ps1 demo
  .\scripts\Invoke-SmtpLab.ps1 send --scenario plain
  .\scripts\Invoke-SmtpLab.ps1 send --all
  .\scripts\Invoke-SmtpLab.ps1 list
#>
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("demo", "send", "list", "clear")]
    [string]$Command,

    [string]$Scenario,
    [switch]$All
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

$pyArgs = @("-m", "devtools.smtp_lab.cli", $Command)
if ($Command -eq "send") {
    if ($All) {
        $pyArgs += "--all"
    }
    elseif ($Scenario) {
        $pyArgs += @("--scenario", $Scenario)
    }
    else {
        Write-Host "For send, use -Scenario <id> or -All. Run 'demo' to list scenarios." -ForegroundColor Yellow
        & python @(@("-m", "devtools.smtp_lab.cli", "demo"))
        exit 1
    }
}

& python @pyArgs
exit $LASTEXITCODE
