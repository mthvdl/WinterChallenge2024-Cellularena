#!/usr/bin/env bash
# Project-wide non-secret environment settings.
# Source this file before running any remote script:
#   source pz_cellularena/env.sh
#
# For credentials (CG_SESSION, etc.) copy env.secret.sh.example → env.secret.sh
# and fill in values. That file is gitignored and must never be committed.

# ── Local ──────────────────────────────────────────────────────────────────
CONDA_ENV=cellularena
GAME=cellularena

# ── Azure resources ────────────────────────────────────────────────────────
AZURE_LOCATION=westeurope
AZURE_PREFIX=cellularena
AZURE_RG=cellularena-rg
AZURE_FILE_SHARE=experiments
AZURE_ACA_ENV=cellularena-env
AZURE_GPU_PROFILE=gpu-nc8t4

# Set by setup_infra.sh (derived from subscription ID).
# Fill these in after running setup_infra.sh the first time:
AZURE_STORAGE_ACCT=cellularena0c8681
AZURE_ACR_NAME=cellularenaacr0c8681
AZURE_ACR_SERVER=cellularenaacr0c8681.azurecr.io

# Full image reference for training jobs
TRAIN_IMAGE="${AZURE_ACR_SERVER}/cellularena-train:latest"
