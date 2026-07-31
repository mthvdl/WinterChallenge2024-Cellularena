---
name: aca-run-training
description: "Use when the user asks to start or resume a training experiment on Azure Container Apps GPU. Covers cold-start, warm replay, and checkpoint resume. Handles job creation, start, monitoring, and log retrieval."
---

# ACA Run Training

Use this skill to launch or resume a training job on Azure Container Apps using
the `Consumption-GPU-NC8as-T4` workload profile.

> **Prerequisites**: `aca-setup` has been run and the training image has been pushed to ACR.

---

## Execution context

**Local (WSL)**: Run bash scripts from the **repo root**. Source `env.sh` first:

```bash
source pz_cellularena/env.sh
```

---

## Inputs To Ask Or Confirm

- Experiment name (e.g. `exp_001_baseline`)
- Image reference (`$TRAIN_IMAGE` from `env.sh`, or full `<acr_server>/cellularena-train:latest`)
- Total steps (default: 500 000)
- Number of parallel envs (default: 4)
- Cold start, or resume from checkpoint?
- If resuming: checkpoint path inside the share (e.g. `/mnt/data/experiments/cellularena/exp_001_baseline/league_pool/step_100000.pt`)

---

## Safety Checks

- Confirm experiment name does not collide with an existing run you want to keep
- If resuming, confirm the checkpoint path exists in Azure Files before launching
- `--reset-replay` / `-r` clears the replay buffer — only use for true cold starts

---

## Launch Commands

### Cold start (new experiment)

```bash
source pz_cellularena/env.sh
./pz_cellularena/remote/aca/run_job.sh \
    -x exp_001_baseline \
    -i "$TRAIN_IMAGE" \
    -s 500000 \
    -n 4 \
    -r
```

### Resume from checkpoint

```bash
source pz_cellularena/env.sh
./pz_cellularena/remote/aca/run_job.sh \
    -x exp_001_baseline \
    -i "$TRAIN_IMAGE" \
    -s 500000 \
    -n 4 \
    -c /mnt/data/experiments/cellularena/exp_001_baseline/league_pool/step_100000.pt
```

---

## Monitoring

### Check execution status

```bash
az containerapp job execution show \
    -n <JOB_NAME> -g cellularena-rg \
    --job-execution-name <EXEC_NAME> \
    --query properties.status -o tsv
```

### Stream live logs

```bash
az containerapp job logs show \
    -n <JOB_NAME> -g cellularena-rg \
    --execution <EXEC_NAME> \
    --follow true
```

### List all executions

```bash
az containerapp job execution list -n <JOB_NAME> -g cellularena-rg -o table
```

---

## Job Name Convention

The script derives the job name as `<game>-<experiment>` (lowercase, hyphens,
truncated to 32 chars). Example: `cellularena-exp-001-baseline`.

---

## What To Report Back

- Job name and execution name
- Status after creation
- Data paths inside the container:
  - Runs: `/mnt/data/experiments/<game>/<exp>/runs`
  - Replay: `/mnt/data/experiments/<game>/<exp>/replay_store`
  - Snapshots: `/mnt/data/experiments/<game>/<exp>/league_pool`
- How to view TensorBoard: use the `aca-tensorboard` skill
