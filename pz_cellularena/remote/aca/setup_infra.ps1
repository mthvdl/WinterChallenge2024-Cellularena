#!/usr/bin/env pwsh
# Provisions: resource group, storage account + file share, ACR, ACA environment with GPU profile.
# Run once per subscription; safe to re-run (skips already-existing resources).
# Usage: ./setup_infra.ps1 [-Location westeurope] [-Prefix cellularena]
param(
    [string]$Location = 'westeurope',
    [string]$Prefix   = 'cellularena'
)

$ErrorActionPreference = 'Stop'
$az = 'C:\Users\mvidal\tools\azure-cli\python.exe'

# Derive globally-unique suffix from subscription ID (first 6 hex chars)
$subId = (& $az -IBm azure.cli account show --query id -o tsv).Trim()
$suffix = $subId.Replace('-','').Substring(0,6).ToLower()

$rg          = "$Prefix-rg"
$storageAcct = "$($Prefix.Replace('-',''))$suffix"   # max 24 chars, lowercase
$fileShare   = 'experiments'
$acrName     = "$($Prefix.Replace('-',''))acr$suffix"
$acaEnv      = "$Prefix-env"
$gpuProfile  = 'gpu-nc8t4'

Write-Host "=== Config ===" -ForegroundColor Cyan
Write-Host "  RG:           $rg"
Write-Host "  Storage acct: $storageAcct"
Write-Host "  File share:   $fileShare"
Write-Host "  ACR:          $acrName"
Write-Host "  ACA env:      $acaEnv"
Write-Host "  Location:     $Location"

# --- Resource group ---
Write-Host "`n[1/5] Resource group..." -ForegroundColor Cyan
& $az -IBm azure.cli group create -n $rg -l $Location -o none

# --- Storage account + file share ---
Write-Host "`n[2/5] Storage account + file share..." -ForegroundColor Cyan
$exists = (& $az -IBm azure.cli storage account check-name -n $storageAcct --query nameAvailable -o tsv).Trim()
if ($exists -eq 'true') {
    & $az -IBm azure.cli storage account create -n $storageAcct -g $rg -l $Location --sku Standard_LRS --kind StorageV2 -o none
} else {
    Write-Host "  Storage account $storageAcct already exists."
}
$storageKey = (& $az -IBm azure.cli storage account keys list -n $storageAcct -g $rg --query '[0].value' -o tsv).Trim()
& $az -IBm azure.cli storage share-rm create --storage-account $storageAcct -g $rg -n $fileShare --quota 128 -o none
Write-Host "  Share: $fileShare  (128 GiB)"

# --- ACR ---
Write-Host "`n[3/5] Azure Container Registry..." -ForegroundColor Cyan
try {
    $acrExists = (& $az -IBm azure.cli acr show -n $acrName -g $rg --query name -o tsv 2>$null).Trim()
} catch {
    $acrExists = ''
}
if (-not $acrExists) {
    & $az -IBm azure.cli acr create -n $acrName -g $rg -l $Location --sku Basic --admin-enabled true -o none
} else {
    Write-Host "  ACR $acrName already exists."
}
$acrServer = (& $az -IBm azure.cli acr show -n $acrName -g $rg --query loginServer -o tsv).Trim()

# --- ACA Environment ---
Write-Host "`n[4/5] ACA environment + GPU workload profile..." -ForegroundColor Cyan
try {
    $envExists = (& $az -IBm azure.cli containerapp env show -n $acaEnv -g $rg --query name -o tsv 2>$null).Trim()
} catch {
    $envExists = ''
}
if (-not $envExists) {
    & $az -IBm azure.cli containerapp env create -n $acaEnv -g $rg -l $Location --logs-destination none --enable-workload-profiles -o none
} else {
    Write-Host "  ACA env $acaEnv already exists."
}
try {
    $profileExists = (& $az -IBm azure.cli containerapp env workload-profile show -n $acaEnv -g $rg --workload-profile-name $gpuProfile --query name -o tsv 2>$null).Trim()
} catch {
    $profileExists = ''
}
if (-not $profileExists) {
    & $az -IBm azure.cli containerapp env workload-profile add -n $acaEnv -g $rg `
        --workload-profile-name $gpuProfile --workload-profile-type Consumption-GPU-NC8as-T4 -o none
} else {
    Write-Host "  GPU workload profile $gpuProfile already exists."
}

# --- Mount storage in ACA environment ---
Write-Host "`n[5/5] Link file share to ACA environment..." -ForegroundColor Cyan
try {
    $mountExists = (& $az -IBm azure.cli containerapp env storage show -n $acaEnv -g $rg --storage-name experiments -o tsv 2>$null)
} catch {
    $mountExists = ''
}
if (-not $mountExists) {
    & $az -IBm azure.cli containerapp env storage set -n $acaEnv -g $rg `
        --storage-name experiments `
        --azure-file-account-name $storageAcct `
        --azure-file-account-key $storageKey `
        --azure-file-share-name $fileShare `
        --access-mode ReadWrite -o none
} else {
    Write-Host "  Storage mount 'experiments' already linked."
}

# --- Output connection info ---
Write-Host "`n=== Done ===" -ForegroundColor Green
Write-Host "ACR login server : $acrServer"
Write-Host "Storage account  : $storageAcct"
Write-Host "Storage key      : (run: az storage account keys list -n $storageAcct -g $rg)"
Write-Host ""
Write-Host "Next: build and push the training image:"
Write-Host "  ./push_image.ps1 -AcrName $acrName -ResourceGroup $rg"
