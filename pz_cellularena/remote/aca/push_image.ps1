#!/usr/bin/env pwsh
# Builds the training image and pushes it to ACR.
# Must be run from the repo root (WinterChallenge2024-Cellularena/).
# Usage: ./pz_cellularena/remote/aca/push_image.ps1 -AcrName <name> -ResourceGroup <rg> [-Tag latest] [-Engine podman|docker]
# When Engine=podman (default), build/push are delegated to WSL where podman lives.
param(
    [Parameter(Mandatory)][string]$AcrName,
    [Parameter(Mandatory)][string]$ResourceGroup,
    [string]$Tag = 'latest',
    [ValidateSet('podman','docker')][string]$Engine = 'podman'
)

$ErrorActionPreference = 'Stop'

$acrServer = (wsl az acr show -n $AcrName -g $ResourceGroup --query loginServer -o tsv).Trim()
$imageFull  = "${acrServer}/cellularena-train:${Tag}"

Write-Host "Building $imageFull from repo root with $Engine..." -ForegroundColor Cyan
Write-Host "(Dockerfile: pz_cellularena/remote/aca/Dockerfile)"

# Stage the WSL CA bundle so Dockerfile can inject it (fixes corporate TLS interception during pip)
$caBundleDest = 'pz_cellularena\remote\aca\ca-bundle.crt'
Write-Host "  Staging CA bundle for build..." -ForegroundColor DarkGray
wsl bash -c "cat /etc/ssl/certs/ca-certificates.crt" | Set-Content -Encoding utf8 $caBundleDest

# Resolve repo root as a WSL path; handles \\wsl.localhost\<distro>\... UNC paths
$providerPath = (Get-Location).ProviderPath
if ($providerPath -match '^\\\\wsl\.localhost\\[^\\]+(.*)$') {
    $wslRepoRoot = $Matches[1].Replace('\','/')
} else {
    $wslRepoRoot = (wsl wslpath -u ($providerPath.Replace('\','/')))
}

if ($Engine -eq 'podman') {
    # podman lives in WSL; run build there
    Write-Host "  (delegating to WSL podman)" -ForegroundColor DarkGray
    wsl podman build -f "$wslRepoRoot/pz_cellularena/remote/aca/Dockerfile" -t $imageFull "$wslRepoRoot"
    if ($LASTEXITCODE -ne 0) { throw "podman build failed" }

    Write-Host "`nLogging in to ACR..." -ForegroundColor Cyan
    $tokenJson = wsl az acr login -n $AcrName --expose-token -o json
    if ($LASTEXITCODE -ne 0) { throw "Failed to get ACR access token" }
    $token = ($tokenJson | ConvertFrom-Json).accessToken
    if (-not $token) { throw "ACR access token is empty" }
    # pipe password to avoid it appearing in process list
    $token | wsl podman login $acrServer --username 00000000-0000-0000-0000-000000000000 --password-stdin
    if ($LASTEXITCODE -ne 0) { throw "podman login failed" }

    Write-Host "Pushing $imageFull..." -ForegroundColor Cyan
    wsl podman push $imageFull
    if ($LASTEXITCODE -ne 0) { throw "podman push failed" }
} else {
    if (-not (Get-Command $Engine -ErrorAction SilentlyContinue)) {
        throw "Container engine '$Engine' was not found in PATH."
    }
    & $Engine build -f pz_cellularena/remote/aca/Dockerfile -t $imageFull .
    if ($LASTEXITCODE -ne 0) { throw "$Engine build failed" }

    Write-Host "`nLogging in to ACR..." -ForegroundColor Cyan
    wsl az acr login -n $AcrName
    if ($LASTEXITCODE -ne 0) { throw "docker registry login failed" }

    Write-Host "Pushing $imageFull..." -ForegroundColor Cyan
    & $Engine push $imageFull
    if ($LASTEXITCODE -ne 0) { throw "$Engine push failed" }
}

Remove-Item -ErrorAction SilentlyContinue $caBundleDest

Write-Host "`nImage pushed: $imageFull" -ForegroundColor Green
Write-Host "Pass this image to run_job.ps1 with:  -Image $imageFull"
