#!/usr/bin/env pwsh
# Uploads the local offline_pretrain replay store to Azure Files.
# Run once before launching the first ACA offline training job.
# Usage: ./upload_offline_pretrain.ps1 -StorageAccount cellularena0c8681
param(
    [Parameter(Mandatory)][string]$StorageAccount,
    [string]$ResourceGroup = 'cellularena-rg',
    [string]$Game          = 'cellularena'
)

$ErrorActionPreference = 'Stop'

$localSrc = "pz_cellularena\experiments\$Game\offline_pretrain\replay_store"
if (-not (Test-Path $localSrc)) {
    throw "Local replay store not found at: $localSrc"
}

$storageKey = (az storage account keys list `
    -n $StorageAccount -g $ResourceGroup --query '[0].value' -o tsv).Trim()

$remoteDest = "experiments/$Game/offline_pretrain/replay_store"

Write-Host "=== Uploading offline_pretrain replay store ===" -ForegroundColor Cyan
Write-Host "  From : $localSrc"
Write-Host "  To   : $StorageAccount / $remoteDest"

az storage file upload-batch `
    --source $localSrc `
    --destination "experiments" `
    --destination-path $remoteDest `
    --account-name $StorageAccount `
    --account-key $storageKey `
    --overwrite false

if ($LASTEXITCODE -ne 0) { throw "Upload failed" }

Write-Host "`nUpload complete." -ForegroundColor Green
Write-Host "Seed path in container: /mnt/data/$remoteDest"
