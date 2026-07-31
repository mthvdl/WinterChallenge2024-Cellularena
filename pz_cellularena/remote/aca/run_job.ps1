#!/usr/bin/env pwsh
# Creates and starts an ACA training job.
# Usage:
#   ./run_job.ps1 -Experiment my_exp_001 -Image <acr>/cellularena-train:latest
#   ./run_job.ps1 -Experiment my_exp_001 -Image <acr>/cellularena-train:latest -TotalSteps 1000000 -NEnvs 4
#   ./run_job.ps1 -Experiment my_exp_001 -Image <acr>/cellularena-train:latest -ResumeCheckpoint /mnt/data/experiments/cellularena/my_exp_001/league_pool/step_100000.pt
#   ./run_job.ps1 -Experiment offline_train_v1 -Image <acr>/cellularena-train:latest -SeedReplayDir /mnt/data/experiments/cellularena/offline_pretrain/replay_store
param(
    [Parameter(Mandatory)][string]$Experiment,
    [Parameter(Mandatory)][string]$Image,
    [string]$ResourceGroup  = 'cellularena-rg',
    [string]$AcaEnv         = 'cellularena-env',
    [string]$Game           = 'cellularena',
    [string]$GpuProfile     = 'gpu-nc8t4',
    [int]   $TotalSteps     = 500000,
    [int]   $NEnvs          = 4,
    [string]$SeedReplayDir  = '',
    [string]$ResumeCheckpoint = '',
    [switch]$ResetReplay
)

$ErrorActionPreference = 'Stop'

# Data paths inside the container (Azure Files mounted at /mnt/data)
$base        = "/mnt/data/experiments/$Game/$Experiment"
$runDir      = "$base/runs"
$replayDir   = "$base/replay_store"
$snapshotDir = "$base/league_pool"

if ($Experiment -eq 'offline_pretrain') {
    throw "Experiment name 'offline_pretrain' is reserved for immutable seed data. Choose a different experiment name."
}
if ($SeedReplayDir -and $ResetReplay) {
    throw "Do not combine -SeedReplayDir with -ResetReplay; reset would wipe seeded data."
}
if ($SeedReplayDir -and ($SeedReplayDir -eq $replayDir)) {
    throw "Seed replay dir must not equal destination replay dir."
}

$jobName = "$Game-$Experiment".Replace('_','-').ToLower()
if ($jobName.Length -gt 32) { $jobName = $jobName.Substring(0,32) }

# Build training args
$trainArgs = @(
    "train_rainbow.py",
    "--env-factory", "games.$Game.factories:make_env",
    "--game",        $Game,
    "--run-dir",     $runDir,
    "--replay-dir",  $replayDir,
    "--snapshot-dir",$snapshotDir,
    "--device",      "cuda",
    "--total-steps", "$TotalSteps",
    "--n-envs",      "$NEnvs",
    "--self-play"
)
if ($ResetReplay)         { $trainArgs += "--reset-replay" }
if ($SeedReplayDir)       { $trainArgs += @("--seed-replay-dir", $SeedReplayDir) }
if ($ResumeCheckpoint)    { $trainArgs += @("--resume-checkpoint", $ResumeCheckpoint) }

$argsStr = $trainArgs -join ","

Write-Host "=== ACA Training Job ===" -ForegroundColor Cyan
Write-Host "  Job name  : $jobName"
Write-Host "  Experiment: $Experiment"
Write-Host "  Image     : $Image"
Write-Host "  Steps     : $TotalSteps"
Write-Host "  Envs      : $NEnvs"
Write-Host "  Run dir   : $runDir"
Write-Host "  Replay dir: $replayDir"
Write-Host "  Snapshot  : $snapshotDir"
if ($SeedReplayDir) { Write-Host "  Seed from : $SeedReplayDir" }

# Delete existing job definition if present (allows updating image/args)
try {
    $existing = (az containerapp job show -n $jobName -g $ResourceGroup --query name -o tsv 2>$null).Trim()
} catch {
    $existing = ''
}
if ($existing) {
    Write-Host "`nDeleting existing job definition $jobName..." -ForegroundColor Yellow
    az containerapp job delete -n $jobName -g $ResourceGroup --yes -o none
}

Write-Host "`nCreating ACA job..." -ForegroundColor Cyan
az containerapp job create `
    -n $jobName -g $ResourceGroup `
    --environment $AcaEnv `
    --workload-profile-name $GpuProfile `
    --trigger-type Manual `
    --replica-timeout 86400 `
    --replica-retry-limit 0 `
    --image $Image `
    --cpu 4 --memory 28Gi `
    --args $argsStr `
    --volume-name experiments --volume-storage-type AzureFile --volume-storage-name experiments `
    --volume-mount volumeName=experiments,mountPath=/mnt/data `
    -o none
if ($LASTEXITCODE -ne 0) { throw "Job create failed" }

Write-Host "Starting execution..." -ForegroundColor Cyan
$exec = (az containerapp job start -n $jobName -g $ResourceGroup -o json | ConvertFrom-Json)
Write-Host "`n=== Started ===" -ForegroundColor Green
Write-Host "  Execution : $($exec.name)"
Write-Host "  Monitor   : az containerapp job execution show -n $jobName -g $ResourceGroup --job-execution-name $($exec.name) --query properties.status"
Write-Host "  Logs      : az containerapp job logs show -n $jobName -g $ResourceGroup --execution $($exec.name) --follow true"
