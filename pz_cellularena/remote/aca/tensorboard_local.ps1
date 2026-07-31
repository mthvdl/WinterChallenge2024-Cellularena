#!/usr/bin/env pwsh
# Syncs TF event files from Azure Files to a local temp dir, then opens TensorBoard.
# Usage:
#   ./tensorboard_local.ps1 -StorageAccount <name>
#   ./tensorboard_local.ps1 -StorageAccount <name> -Experiment my_exp_001
#   ./tensorboard_local.ps1 -StorageAccount <name> -Experiment my_exp_001 -Watch
param(
    [Parameter(Mandatory)][string]$StorageAccount,
    [string]$Game          = 'cellularena',
    [string]$Experiment    = '',     # empty = all experiments for the game
    [string]$ResourceGroup = 'cellularena-rg',
    [string]$LocalDir      = "$env:TEMP\cellularena_tb",
    [int]   $Port          = 6006,
    [switch]$Watch                  # keep syncing every 30 s while TensorBoard runs
)

$ErrorActionPreference = 'Stop'

$storageKey = (az storage account keys list -n $StorageAccount -g $ResourceGroup --query '[0].value' -o tsv).Trim()

# Remote path inside the share
if ($Experiment) {
    $remotePrefix = "experiments/$Game/$Experiment/runs"
    $localLogDir  = Join-Path $LocalDir "$Game\$Experiment\runs"
} else {
    $remotePrefix = "experiments/$Game"
    $localLogDir  = Join-Path $LocalDir $Game
}

Write-Host "=== TensorBoard Local Viewer ===" -ForegroundColor Cyan
Write-Host "  Storage   : $StorageAccount"
Write-Host "  Remote    : $remotePrefix"
Write-Host "  Local     : $localLogDir"
Write-Host "  Port      : $Port"

New-Item -ItemType Directory -Force -Path $localLogDir | Out-Null

function Sync-Events {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Syncing from Azure Files..." -ForegroundColor DarkCyan
    az storage file download-batch `
        --source "experiments" `
        --destination $LocalDir `
        --account-name $StorageAccount `
        --account-key $storageKey `
        --pattern "$remotePrefix/events.out.tfevents.*" `
        -o none
}

Sync-Events

Write-Host "`nLaunching TensorBoard on http://localhost:$Port ..." -ForegroundColor Green
$tbProc = Start-Process -FilePath "python" `
    -ArgumentList "-m tensorboard.main --logdir `"$localLogDir`" --port $Port --bind_all" `
    -PassThru -NoNewWindow

Write-Host "TensorBoard PID: $($tbProc.Id)"
Start-Sleep 2
Start-Process "http://localhost:$Port"

if ($Watch) {
    Write-Host "Watch mode: syncing every 30 s. Press Ctrl+C to stop." -ForegroundColor Yellow
    try {
        while (-not $tbProc.HasExited) {
            Start-Sleep 30
            Sync-Events
        }
    } finally {
        $tbProc | Stop-Process -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "Run with -Watch to keep syncing. Press Enter to stop TensorBoard."
    $null = Read-Host
    $tbProc | Stop-Process -ErrorAction SilentlyContinue
}
