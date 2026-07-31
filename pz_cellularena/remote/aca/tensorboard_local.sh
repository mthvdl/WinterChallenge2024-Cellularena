#!/usr/bin/env bash
# Syncs TF event files from Azure Files to a local temp dir, then opens TensorBoard.
# Run from the repo root (WinterChallenge2024-Cellularena/).
# Usage:
#   ./pz_cellularena/remote/aca/tensorboard_local.sh -a <storage-account>
#   ./pz_cellularena/remote/aca/tensorboard_local.sh -a <storage-account> -x my_exp_001
#   ./pz_cellularena/remote/aca/tensorboard_local.sh -a <storage-account> -x my_exp_001 -w
set -euo pipefail

# Fall back to Windows az CLI when az is not in WSL PATH
if ! command -v az &>/dev/null; then
    az() { /mnt/c/Users/mvidal/tools/azure-cli/python.exe -IBm azure.cli "$@"; }
    export -f az
fi

# Preserve any caller-provided CONDA_ENV before sourcing env.sh.
CALLER_CONDA_ENV="${CONDA_ENV-}"

# Source env settings if available
ENV_FILE="$(dirname "$0")/../../env.sh"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

STORAGE_ACCOUNT=''
GAME="${GAME:-cellularena}"
EXPERIMENT=''
RESOURCE_GROUP="${AZURE_RG:-cellularena-rg}"
LOCAL_DIR="${TMPDIR:-/tmp}/cellularena_tb"
PORT=6006
WATCH=false
CONDA_ENV="${CALLER_CONDA_ENV:-${CONDA_ENV:-cellularena}}"

usage() {
    echo "Usage: $0 -a <storage-account> [-m game] [-x experiment] [-g rg] [-d local-dir] [-p port] [-w]"
    exit 1
}

while getopts 'a:m:x:g:d:p:wh' opt; do
    case $opt in
        a) STORAGE_ACCOUNT=$OPTARG ;;
        m) GAME=$OPTARG ;;
        x) EXPERIMENT=$OPTARG ;;
        g) RESOURCE_GROUP=$OPTARG ;;
        d) LOCAL_DIR=$OPTARG ;;
        p) PORT=$OPTARG ;;
        w) WATCH=true ;;
        h) usage ;;
        *) usage ;;
    esac
done

[[ -z "$STORAGE_ACCOUNT" ]] && usage

STORAGE_KEY=$(az storage account keys list -n "$STORAGE_ACCOUNT" -g "$RESOURCE_GROUP" --query '[0].value' -o tsv | tr -d '\r')

# Auto-detect whether the share contains nested "experiments/" paths.
if [[ -n "$EXPERIMENT" ]]; then
    CANDIDATES=(
        "experiments/$GAME/$EXPERIMENT/runs"
        "$GAME/$EXPERIMENT/runs"
    )
else
    CANDIDATES=(
        "experiments/$GAME"
        "$GAME"
    )
fi

REMOTE_PREFIX=''
# Prefer candidates that already contain TensorBoard event files.
for CANDIDATE in "${CANDIDATES[@]}"; do
    if [[ -n "$EXPERIMENT" ]]; then
        HAS_EVENTS=$(az storage file list \
            --share-name "experiments" \
            --path "$CANDIDATE" \
            --account-name "$STORAGE_ACCOUNT" \
            --account-key "$STORAGE_KEY" \
            --query "[?contains(name, 'events.out.tfevents')].name" \
            -o tsv 2>/dev/null || true)
    else
        HAS_EVENTS=''
        for EXP_DIR in $(az storage file list \
            --share-name "experiments" \
            --path "$CANDIDATE" \
            --account-name "$STORAGE_ACCOUNT" \
            --account-key "$STORAGE_KEY" \
            --query "[].name" \
            -o tsv 2>/dev/null || true); do
            if az storage file list \
                --share-name "experiments" \
                --path "$CANDIDATE/$EXP_DIR/runs" \
                --account-name "$STORAGE_ACCOUNT" \
                --account-key "$STORAGE_KEY" \
                --query "[?contains(name, 'events.out.tfevents')].name" \
                -o tsv 2>/dev/null | grep -q .; then
                HAS_EVENTS=1
                break
            fi
        done
    fi

    if [[ -n "$HAS_EVENTS" ]]; then
        REMOTE_PREFIX="$CANDIDATE"
        break
    fi
done

# Fall back to the first existing candidate if no event file is found yet.
if [[ -z "$REMOTE_PREFIX" ]]; then
for CANDIDATE in "${CANDIDATES[@]}"; do
    if az storage file list \
        --share-name "experiments" \
        --path "$CANDIDATE" \
        --account-name "$STORAGE_ACCOUNT" \
        --account-key "$STORAGE_KEY" \
        -o none 2>/dev/null; then
        REMOTE_PREFIX="$CANDIDATE"
        break
    fi
done
fi

if [[ -z "$REMOTE_PREFIX" ]]; then
    echo "Error: Could not find remote path for game '$GAME' and experiment '${EXPERIMENT:-<all>}' in share 'experiments'." >&2
    exit 1
fi

# Keep local logdir aligned with the exact remote prefix used by download-batch.
LOCAL_LOGDIR="$LOCAL_DIR/$REMOTE_PREFIX"
if [[ -n "$EXPERIMENT" ]]; then
    EVENT_PATTERN="$REMOTE_PREFIX/events.out.tfevents.*"
else
    EVENT_PATTERN="$REMOTE_PREFIX/*/runs/events.out.tfevents.*"
fi

echo "=== TensorBoard Local Viewer ==="
echo "  Storage  : $STORAGE_ACCOUNT"
echo "  Remote   : $REMOTE_PREFIX"
echo "  Local    : $LOCAL_LOGDIR"
echo "  Port     : $PORT"
echo "  Conda env: $CONDA_ENV"

mkdir -p "$LOCAL_LOGDIR"

sync_events() {
    echo "[$(date '+%H:%M:%S')] Syncing from Azure Files..."
    az storage file download-batch \
        --source "experiments" \
        --destination "$LOCAL_DIR" \
        --account-name "$STORAGE_ACCOUNT" \
        --account-key "$STORAGE_KEY" \
    --pattern "$EVENT_PATTERN" \
        -o none
}

sync_events

echo ""
echo "Launching TensorBoard on http://localhost:${PORT} ..."
conda run -n "$CONDA_ENV" tensorboard --logdir "$LOCAL_LOGDIR" --port "$PORT" &
TB_PID=$!

sleep 2
echo "TensorBoard PID: $TB_PID"

if [[ "$WATCH" == "true" ]]; then
    echo "Watch mode: syncing every 30 s. Press Ctrl+C to stop."
    trap "kill $TB_PID 2>/dev/null; exit 0" INT TERM
    while kill -0 "$TB_PID" 2>/dev/null; do
        sleep 30
        sync_events
    done
else
    echo "Run with -w to keep syncing. Press Enter to stop TensorBoard."
    read -r
    kill "$TB_PID" 2>/dev/null || true
fi
