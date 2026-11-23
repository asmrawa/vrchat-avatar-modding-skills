<#
.SYNOPSIS
    Install VRChat Avatar Modding Skills into Codex, Antigravity, or Cursor on Windows.
.EXAMPLE
    .\install.ps1 -Client codex
    .\install.ps1 -Client all -Force
#>
[CmdletBinding()]
param(
    [ValidateSet('codex', 'antigravity', 'cursor', 'all')]
    [string]$Client = 'codex',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillsSrc = Join-Path $root 'skills'

$targets = @{
    codex       = Join-Path $env:USERPROFILE '.codex\skills'
    antigravity = Join-Path $env:USERPROFILE '.gemini\config\skills'
    cursor      = Join-Path $env:USERPROFILE '.cursor\skills'
}

$selectedClients = if ($Client -eq 'all') { @('codex', 'antigravity', 'cursor') } else { @($Client) }
$skillDirs = Get-ChildItem -LiteralPath $skillsSrc -Directory

foreach ($c in $selectedClients) {
    $destRoot = $targets[$c]
    New-Item -ItemType Directory -Force -Path $destRoot | Out-Null
    Write-Host "`n[$c] Installing skills to: $destRoot" -ForegroundColor Cyan

    foreach ($skill in $skillDirs) {
        $dest = Join-Path $destRoot $skill.Name
        if (Test-Path -LiteralPath $dest) {
            if (-not $Force) {
                Write-Warning "  Skipped '$($skill.Name)' (already exists). Re-run with -Force to replace."
                continue
            }
            $backup = "$dest.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
            Move-Item -LiteralPath $dest -Destination $backup
            Write-Host "  Backed up previous version to: $backup" -ForegroundColor Yellow
        }
        Copy-Item -LiteralPath $skill.FullName -Destination $dest -Recurse -Force
        Write-Host "  Installed: $($skill.Name)" -ForegroundColor Green
    }
}

Write-Host "`nDone! Restart your AI client or open a new session to load the skills." -ForegroundColor Green
