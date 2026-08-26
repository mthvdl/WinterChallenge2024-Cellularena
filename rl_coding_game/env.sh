#!/usr/bin/env bash
# Shared environment loader for rl_coding_game.
# Sources per-game non-secret settings from games/<game>/env.sh.
#
# Usage:
#   export GAME=cellularena   # optional, defaults to cellularena
#   source rl_coding_game/env.sh

# The selected game can be pre-set by caller.
GAME="${GAME:-cellularena}"
GAME_ENV_FILE="$(dirname "${BASH_SOURCE[0]}")/games/${GAME}/env.sh"

if [[ -f "$GAME_ENV_FILE" ]]; then
	# shellcheck disable=SC1090
	source "$GAME_ENV_FILE"
else
	# Safe fallbacks when the game file does not exist yet.
	CONDA_ENV="${CONDA_ENV:-${GAME}}"
	AZURE_LOCATION="${AZURE_LOCATION:-westeurope}"
	AZURE_PREFIX="${AZURE_PREFIX:-${GAME}}"
	AZURE_RG="${AZURE_RG:-${GAME}-rg}"
	AZURE_FILE_SHARE="${AZURE_FILE_SHARE:-experiments}"
	AZURE_ACA_ENV="${AZURE_ACA_ENV:-${GAME}-env}"
	AZURE_GPU_PROFILE="${AZURE_GPU_PROFILE:-gpu-nc8t4}"
fi

# Derive TRAIN_IMAGE when possible.
if [[ -n "${AZURE_ACR_SERVER:-}" ]]; then
	TRAIN_IMAGE="${TRAIN_IMAGE:-${AZURE_ACR_SERVER}/${GAME}-train:latest}"
fi
