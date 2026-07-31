---
name: aca-setup
description: "Use when the user wants to provision Azure infrastructure for ACA GPU training: storage account + file share for experiments, Azure Container Registry, and the ACA environment with the Consumption-GPU-NC8as-T4 workload profile."
---

# ACA Setup — One-Time Infrastructure Provisioning

Use this skill once per subscription to create all shared Azure resources needed
for GPU training via Azure Container Apps.

> **Re-running is safe.** The script skips already-existing resources.

---

## Execution context

**Local (WSL)**: Run bash scripts from the **repo root**. Source `env.sh` first
to pick up configured defaults.

```bash
source pz_cellularena/env.sh
```

---

## What Gets Created

| Resource | Name | Purpose |
|---|---|---|
| Resource group | `cellularena-rg` | Container for all resources |
| Storage account | `cellularena<suffix>` | Persistent experiment storage |
| Azure Files share | `experiments` (128 GiB) | Parquets, TF events, checkpoints |
| Azure Container Registry | `cellularenaaacr<suffix>` | Docker image hosting |
| ACA Environment | `cellularena-env` | GPU job runtime |
| Workload profile | `gpu-nc8t4` | `Consumption-GPU-NC8as-T4` (1× T4, 4 vCPU, 28 GiB) |

The file share is mounted inside every training job at `/mnt/data`.  
Experiment layout inside the share:

```
experiments/
  cellularena/
    <experiment-name>/
      runs/          ← TF event files
      replay_store/  ← DuckDB + Parquet replay data
      league_pool/   ← model snapshot checkpoints
```

---

## Step 0 — Prerequisites

- Azure CLI authenticated (`az login`)
- `podman` installed locally (for building the training image)
- Allowed deployment location: `westeurope` (subscription policy)

---

## Step 1 — Provision Infrastructure

Run from the repo root:

```bash
./pz_cellularena/remote/aca/setup_infra.sh
```

Optional overrides:

```bash
./pz_cellularena/remote/aca/setup_infra.sh -l westeurope -p cellularena
```

The script prints the ACR login server and storage account name at the end.
**Update `pz_cellularena/env.sh`** with the printed `AZURE_STORAGE_ACCT`, `AZURE_ACR_NAME`, and `AZURE_ACR_SERVER` values.

---

## Step 2 — Build and Push the Training Image

Run from the **repo root** (not inside `pz_cellularena/`):

```bash
source pz_cellularena/env.sh
./pz_cellularena/remote/aca/push_image.sh -a "$AZURE_ACR_NAME" -g "$AZURE_RG"
```

This builds the image using `pz_cellularena/remote/aca/Dockerfile` with the
full repo as context, installs deps from `pz_cellularena/requirements.txt`
(plus CUDA torch), then pushes to ACR.

**Rebuild the image whenever `requirements.txt` or project code changes.**

The full image reference to pass to training jobs:
```
<ACR_LOGIN_SERVER>/cellularena-train:latest
```

---

## What To Report Back

- Resource group name
- Storage account name → update `AZURE_STORAGE_ACCT` in `pz_cellularena/env.sh`
- ACR login server → update `AZURE_ACR_NAME` and `AZURE_ACR_SERVER` in `pz_cellularena/env.sh`
- Confirm the GPU workload profile exists:
  ```bash
  az containerapp env workload-profile show \
      -n cellularena-env -g cellularena-rg \
      --workload-profile-name gpu-nc8t4 \
      --query properties.workloadProfileType -o tsv
  ```
  Expected output: `Consumption-GPU-NC8as-T4`
