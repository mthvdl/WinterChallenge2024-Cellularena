#!/usr/bin/env bash
# Creates and starts an ACA training job.
# Must be run from the repo root (WinterChallenge2024-Cellularena/).
# Usage:
#   ./pz_cellularena/remote/aca/run_job.sh -x my_exp_001 -i <acr>/cellularena-train:latest
#   ./pz_cellularena/remote/aca/run_job.sh -x my_exp_001 -i <acr>/cellularena-train:latest -s 1000000 -n 4
#   ./pz_cellularena/remote/aca/run_job.sh -x my_exp_001 -i <acr>/cellularena-train:latest -c /mnt/data/experiments/cellularena/my_exp_001/league_pool/step_100000.pt
#   ./pz_cellularena/remote/aca/run_job.sh -x offline_train_v1 -i <acr>/cellularena-train:latest -d /mnt/data/experiments/cellularena/offline_pretrain/replay_store
set -euo pipefail

# Fall back to Windows az CLI when az is not in WSL PATH
if ! command -v az &>/dev/null; then
    az() { /mnt/c/Users/mvidal/tools/azure-cli/python.exe -IBm azure.cli "$@"; }
    export -f az
fi

EXPERIMENT=''
IMAGE=''
RESOURCE_GROUP='cellularena-rg'
ACA_ENV='cellularena-env'
GAME='cellularena'
GPU_PROFILE='gpu-nc8t4'
TOTAL_STEPS=500000
N_ENVS=4
SEED_REPLAY_DIR=''
RESUME_CHECKPOINT=''
RESET_REPLAY=false

usage() {
    echo "Usage: $0 -x <experiment> -i <image> [-g rg] [-e aca-env] [-m game] [-p gpu-profile]"
    echo "          [-s total-steps] [-n n-envs] [-d seed-replay-dir] [-c resume-checkpoint] [-r]"
    exit 1
}

while getopts 'x:i:g:e:m:p:s:n:d:c:rh' opt; do
    case $opt in
        x) EXPERIMENT=$OPTARG ;;
        i) IMAGE=$OPTARG ;;
        g) RESOURCE_GROUP=$OPTARG ;;
        e) ACA_ENV=$OPTARG ;;
        m) GAME=$OPTARG ;;
        p) GPU_PROFILE=$OPTARG ;;
        s) TOTAL_STEPS=$OPTARG ;;
        n) N_ENVS=$OPTARG ;;
        d) SEED_REPLAY_DIR=$OPTARG ;;
        c) RESUME_CHECKPOINT=$OPTARG ;;
        r) RESET_REPLAY=true ;;
        h) usage ;;
        *) usage ;;
    esac
done

[[ -z "$EXPERIMENT" || -z "$IMAGE" ]] && usage

if [[ "$EXPERIMENT" == "offline_pretrain" ]]; then
    echo "Error: Experiment name 'offline_pretrain' is reserved for immutable seed data." >&2
    exit 1
fi
if [[ -n "$SEED_REPLAY_DIR" && "$RESET_REPLAY" == "true" ]]; then
    echo "Error: Do not combine -d (seed-replay-dir) with -r (reset-replay)." >&2
    exit 1
fi

BASE="/mnt/data/experiments/${GAME}/${EXPERIMENT}"
RUN_DIR="${BASE}/runs"
REPLAY_DIR="${BASE}/replay_store"
SNAPSHOT_DIR="${BASE}/league_pool"

if [[ -n "$SEED_REPLAY_DIR" && "$SEED_REPLAY_DIR" == "$REPLAY_DIR" ]]; then
    echo "Error: Seed replay dir must not equal destination replay dir." >&2
    exit 1
fi

JOB_NAME="${GAME}-${EXPERIMENT}"
JOB_NAME="${JOB_NAME//_/-}"
JOB_NAME="${JOB_NAME,,}"
JOB_NAME="${JOB_NAME:0:32}"

TRAIN_ARGS="train_rainbow.py,--env-factory,games.${GAME}.factories:make_env,--game,${GAME},--run-dir,${RUN_DIR},--replay-dir,${REPLAY_DIR},--snapshot-dir,${SNAPSHOT_DIR},--device,cuda,--total-steps,${TOTAL_STEPS},--n-envs,${N_ENVS},--self-play"
[[ "$RESET_REPLAY" == "true" ]] && TRAIN_ARGS="${TRAIN_ARGS},--reset-replay"
[[ -n "$SEED_REPLAY_DIR" ]] && TRAIN_ARGS="${TRAIN_ARGS},--seed-replay-dir,${SEED_REPLAY_DIR}"
[[ -n "$RESUME_CHECKPOINT" ]] && TRAIN_ARGS="${TRAIN_ARGS},--resume-checkpoint,${RESUME_CHECKPOINT}"

echo "=== ACA Training Job ==="
echo "  Job name  : $JOB_NAME"
echo "  Experiment: $EXPERIMENT"
echo "  Image     : $IMAGE"
echo "  Steps     : $TOTAL_STEPS"
echo "  Envs      : $N_ENVS"
echo "  Run dir   : $RUN_DIR"
echo "  Replay dir: $REPLAY_DIR"
echo "  Snapshot  : $SNAPSHOT_DIR"
[[ -n "$SEED_REPLAY_DIR" ]] && echo "  Seed from : $SEED_REPLAY_DIR"

# Delete existing job definition if present (allows updating image/args)
EXISTING=$(az containerapp job show -n "$JOB_NAME" -g "$RESOURCE_GROUP" --query name -o tsv 2>/dev/null || true)
if [[ -n "$EXISTING" ]]; then
    echo ""
    echo "Deleting existing job definition $JOB_NAME..."
    az containerapp job delete -n "$JOB_NAME" -g "$RESOURCE_GROUP" --yes -o none
fi

echo ""
echo "Creating ACA job..."
az containerapp job create \
    -n "$JOB_NAME" -g "$RESOURCE_GROUP" \
    --environment "$ACA_ENV" \
    --workload-profile-name "$GPU_PROFILE" \
    --trigger-type Manual \
    --replica-timeout 86400 \
    --replica-retry-limit 0 \
    --image "$IMAGE" \
    --cpu 4 --memory 28Gi \
    --args "$TRAIN_ARGS" \
    --volume-name experiments --volume-storage-type AzureFile --volume-storage-name experiments \
    --volume-mount volumeName=experiments,mountPath=/mnt/data \
    -o none

echo "Starting execution..."
EXEC=$(az containerapp job start -n "$JOB_NAME" -g "$RESOURCE_GROUP" -o json)
EXEC_NAME=$(echo "$EXEC" | python3 -c "import sys,json; print(json.load(sys.stdin)['name'])")

echo ""
echo "=== Started ==="
echo "  Execution : $EXEC_NAME"
echo "  Monitor   : az containerapp job execution show -n $JOB_NAME -g $RESOURCE_GROUP --job-execution-name $EXEC_NAME --query properties.status"
echo "  Logs      : az containerapp job logs show -n $JOB_NAME -g $RESOURCE_GROUP --execution $EXEC_NAME --follow true"
