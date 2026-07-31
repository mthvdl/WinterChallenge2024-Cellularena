#!/usr/bin/env bash
# Provisions: resource group, storage account + file share, ACR, ACA environment with GPU profile.
# Run once per subscription; safe to re-run (skips already-existing resources).
# Usage: ./pz_cellularena/remote/aca/setup_infra.sh [-l westeurope] [-p cellularena]
set -euo pipefail

# Fall back to Windows az CLI when az is not in WSL PATH
if ! command -v az &>/dev/null; then
    az() { /mnt/c/Users/mvidal/tools/azure-cli/python.exe -IBm azure.cli "$@"; }
    export -f az
fi

LOCATION='westeurope'
PREFIX='cellularena'

usage() {
    echo "Usage: $0 [-l <location>] [-p <prefix>]"
    exit 1
}

while getopts 'l:p:h' opt; do
    case $opt in
        l) LOCATION=$OPTARG ;;
        p) PREFIX=$OPTARG ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Derive globally-unique suffix from subscription ID (first 6 hex chars)
SUB_ID=$(az account show --query id -o tsv)
SUFFIX="${SUB_ID//-/}"
SUFFIX="${SUFFIX:0:6}"
SUFFIX="${SUFFIX,,}"

PREFIX_NODASH="${PREFIX//-/}"
RG="${PREFIX}-rg"
STORAGE_ACCT="${PREFIX_NODASH}${SUFFIX}"   # max 24 chars, lowercase
FILE_SHARE='experiments'
ACR_NAME="${PREFIX_NODASH}acr${SUFFIX}"
ACA_ENV="${PREFIX}-env"
GPU_PROFILE='gpu-nc8t4'

echo "=== Config ==="
echo "  RG:           $RG"
echo "  Storage acct: $STORAGE_ACCT"
echo "  File share:   $FILE_SHARE"
echo "  ACR:          $ACR_NAME"
echo "  ACA env:      $ACA_ENV"
echo "  Location:     $LOCATION"

# --- Resource group ---
echo ""
echo "[1/5] Resource group..."
az group create -n "$RG" -l "$LOCATION" -o none

# --- Storage account + file share ---
echo ""
echo "[2/5] Storage account + file share..."
NAME_AVAILABLE=$(az storage account check-name -n "$STORAGE_ACCT" --query nameAvailable -o tsv)
if [[ "$NAME_AVAILABLE" == "true" ]]; then
    az storage account create -n "$STORAGE_ACCT" -g "$RG" -l "$LOCATION" \
        --sku Standard_LRS --kind StorageV2 -o none
else
    echo "  Storage account $STORAGE_ACCT already exists."
fi
STORAGE_KEY=$(az storage account keys list -n "$STORAGE_ACCT" -g "$RG" --query '[0].value' -o tsv)
az storage share-rm create --storage-account "$STORAGE_ACCT" -g "$RG" -n "$FILE_SHARE" --quota 128 -o none
echo "  Share: $FILE_SHARE  (128 GiB)"

# --- ACR ---
echo ""
echo "[3/5] Azure Container Registry..."
ACR_EXISTS=$(az acr show -n "$ACR_NAME" -g "$RG" --query name -o tsv 2>/dev/null || true)
if [[ -z "$ACR_EXISTS" ]]; then
    az acr create -n "$ACR_NAME" -g "$RG" -l "$LOCATION" --sku Basic --admin-enabled true -o none
else
    echo "  ACR $ACR_NAME already exists."
fi
ACR_SERVER=$(az acr show -n "$ACR_NAME" -g "$RG" --query loginServer -o tsv)

# --- ACA Environment ---
echo ""
echo "[4/5] ACA environment + GPU workload profile..."
ENV_EXISTS=$(az containerapp env show -n "$ACA_ENV" -g "$RG" --query name -o tsv 2>/dev/null || true)
if [[ -z "$ENV_EXISTS" ]]; then
    az containerapp env create -n "$ACA_ENV" -g "$RG" -l "$LOCATION" \
        --logs-destination none --enable-workload-profiles -o none
else
    echo "  ACA env $ACA_ENV already exists."
fi
PROFILE_EXISTS=$(az containerapp env workload-profile show -n "$ACA_ENV" -g "$RG" \
    --workload-profile-name "$GPU_PROFILE" --query name -o tsv 2>/dev/null || true)
if [[ -z "$PROFILE_EXISTS" ]]; then
    az containerapp env workload-profile add -n "$ACA_ENV" -g "$RG" \
        --workload-profile-name "$GPU_PROFILE" \
        --workload-profile-type Consumption-GPU-NC8as-T4 -o none
else
    echo "  GPU workload profile $GPU_PROFILE already exists."
fi

# --- Mount storage in ACA environment ---
echo ""
echo "[5/5] Link file share to ACA environment..."
MOUNT_EXISTS=$(az containerapp env storage show -n "$ACA_ENV" -g "$RG" \
    --storage-name experiments -o tsv 2>/dev/null || true)
if [[ -z "$MOUNT_EXISTS" ]]; then
    az containerapp env storage set -n "$ACA_ENV" -g "$RG" \
        --storage-name experiments \
        --azure-file-account-name "$STORAGE_ACCT" \
        --azure-file-account-key "$STORAGE_KEY" \
        --azure-file-share-name "$FILE_SHARE" \
        --access-mode ReadWrite -o none
else
    echo "  Storage mount 'experiments' already linked."
fi

# --- Output connection info ---
echo ""
echo "=== Done ==="
echo "ACR login server : $ACR_SERVER"
echo "Storage account  : $STORAGE_ACCT"
echo "Storage key      : (run: az storage account keys list -n $STORAGE_ACCT -g $RG)"
echo ""
echo "Next: build and push the training image:"
echo "  ./pz_cellularena/remote/aca/push_image.sh -a $ACR_NAME -g $RG"
