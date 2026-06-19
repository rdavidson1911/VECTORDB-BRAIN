#Requires -Version 5.1
<#
.SYNOPSIS
    Remove Claude agent git worktrees under .claude/worktrees (VECTORDB-BRAIN).
.DESCRIPTION
    Default is -WhatIf. Orchestrator should confirm no uncommitted work before -ForceRemove.
    Does not remove the main repo checkout or Cursor-managed worktrees.
.PARAMETER ProjectRoot
    Repo root. Default: I:\VECTORDB-BRAIN
.PARAMETER WhatIf
    Show actions only (default when -ForceRemove is not set).
.PARAMETER ForceRemove
    Actually run git worktree remove and optional branch delete.
.PARAMETER AllowDirty
    With -ForceRemove, use git worktree remove --force when the tree has uncommitted changes.
.PARAMETER DeleteMergedBranches
    After remove, git branch -d worktree-* and agent/* branches that are merged into main.
.EXAMPLE
    .\scripts\Invoke-AgentWorktreeTeardown.ps1
    .\scripts\Invoke-AgentWorktreeTeardown.ps1 -ForceRemove -DeleteMergedBranches
#>
param(
    [string] $ProjectRoot = "I:\VECTORDB-BRAIN",
    [switch] $ForceRemove,
    [switch] $AllowDirty,
    [switch] $DeleteMergedBranches
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$whatIfMode = -not $ForceRemove
$wtRoot = Join-Path $ProjectRoot '.claude\worktrees'
if (-not (Test-Path (Join-Path $ProjectRoot '.git'))) {
    Write-Error "Not a git repo: $ProjectRoot"
}

Push-Location $ProjectRoot
try {
    $lines = git worktree list --porcelain
    $entries = @()
    $current = @{}
    foreach ($line in $lines) {
        if ($line -eq '') {
            if ($current.worktree) { $entries += [pscustomobject]$current; $current = @{} }
            continue
        }
        if ($line -like 'worktree *') { $current.worktree = $line.Substring(9).Trim() }
        elseif ($line -like 'branch *') { $current.branch = $line.Substring(7).Trim() }
    }
    if ($current.worktree) { $entries += [pscustomobject]$current }

    $targets = $entries | Where-Object {
        $_.worktree -replace '\\', '/' -like "$(($ProjectRoot -replace '\\', '/'))/.claude/worktrees/*"
    }

    if (-not $targets) {
        Write-Host "No worktrees under $wtRoot" -ForegroundColor Gray
        return
    }

    foreach ($t in $targets) {
        $path = $t.worktree
        $branch = $t.branch -replace '^refs/heads/', ''
        Write-Host "Worktree: $path  branch: $branch"

        Push-Location $path
        $dirty = (git status --porcelain)
        Pop-Location
        if ($dirty) {
            Write-Warning "Dirty tree: $path"
            if ($whatIfMode) {
                $flag = if ($AllowDirty) { ' --force' } else { '' }
                Write-Host "  [WhatIf] git worktree remove$flag `"$path`"" -ForegroundColor Cyan
                continue
            }
            if (-not $AllowDirty) {
                Write-Warning "Skip remove (use -AllowDirty to discard uncommitted files)."
                continue
            }
        }

        if ($whatIfMode) {
            Write-Host "  [WhatIf] git worktree remove `"$path`"" -ForegroundColor Cyan
        }
        else {
            if ($dirty -and $AllowDirty) {
                git worktree remove --force $path 2>&1
            }
            else {
                git worktree remove $path 2>&1
            }
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Remove failed; try: git worktree remove --force `"$path`""
            }
        }

        if ($DeleteMergedBranches -and $branch) {
            if ($whatIfMode) {
                Write-Host "  [WhatIf] git branch -d $branch" -ForegroundColor Cyan
            }
            else {
                git branch -d $branch 2>&1 | Out-Null
            }
        }
    }

    if ($whatIfMode) {
        Write-Host "`nDry run only. Re-run with -ForceRemove to apply." -ForegroundColor Yellow
    }
    else {
        git worktree prune
        Write-Host "`nAfter prune:" -ForegroundColor Green
        git worktree list
    }
}
finally {
    Pop-Location
}
