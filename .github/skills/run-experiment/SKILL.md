---
name: run-experiment
description: "Use when the user asks to start, resume, or launch any self-play training experiment — either locally on WSL or remotely on Azure Container Apps GPU. Covers cold-start, warm replay, and checkpoint resume for both flavours."
---

# Run Experiment

Use this skill to start or resume a self-play training experiment.

> For expert-imitation pretraining → `offline-training`
> For self-play bootstrapped from an offline-trained model → `selfplay-from-pretrained`

---

## Step 0 — Detect Current Game and Confirm

```bash
ls -d rl_coding_game/games/*/
ls -d rl_coding_game/experiments/*/ 2>/dev/null || echo "(none)"
```

Confirm game with the user before proceeding.

---

## Step 1 — Ask: LOCAL or REMOTE?

> Will this experiment run **locally** (WSL, your machine) or **remotely** (Azure Container Apps GPU)?

- **LOCAL** → conda + WSL, experiment artifacts in `rl_coding_game/experiments/`
- **REMOTE** → ACA GPU job, artifacts in Azure Files at `/mnt/data/experiments/`

---

## ── LOCAL ──────────────────────────────────────────────────────────────────

Run from the **repo root** in bash.

### Inputs

- Experiment name (e.g. `exp_001_baseline`)
- Total steps
- Number of parallel envs (default: 4)
- Fresh cold start, warm replay, or resume from checkpoint?

### A) Cold start (fresh experiment)

```bash
conda run -n cellularena python rl_coding_game/train_rainbow.py \
    --env-factory games.<GAME>.factories:make_env \
    --game <GAME> \
    --experiment-name <EXPERIMENT_NAME> \
    --total-steps <TOTAL_STEPS> \
    --n-envs <N_ENVS> \
    --self-play \
    --reset-replay
```

### B) Warm replay start (reuse existing replay buffer)

```bash
conda run -n cellularena python rl_coding_game/train_rainbow.py \
    --env-factory games.<GAME>.factories:make_env \
    --game <GAME> \
    --experiment-name <EXPERIMENT_NAME> \
    --total-steps <TOTAL_STEPS> \
    --n-envs <N_ENVS> \
    --self-play \
    --replay-dir <EXISTING_REPLAY_DIR>
```

### C) Resume from checkpoint

```bash
conda run -n cellularena python rl_coding_game/train_rainbow.py \
    --env-factory games.<GAME>.factories:make_env \
    --game <GAME> \
    --experiment-name <EXPERIMENT_NAME> \
    --total-steps <TOTAL_STEPS> \
    --n-envs <N_ENVS> \
    --self-play \
    --resume-checkpoint <CHECKPOINT_PATH>
```

Verify the checkpoint exists first:
```bash
test -f <CHECKPOINT_PATH> && echo "exists" || echo "MISSING"
```

### Local TensorBoard

```bash
conda run -n cellularena tensorboard \
    --logdir rl_coding_game/experiments/<GAME> --port 6006
```

---

## ── REMOTE (ACA) ────────────────────────────────────────────────────────────

Prerequisites: `aca-setup` ran, image is pushed to ACR.

Run from the **repo root** in bash after sourcing env settings:

```bash
source rl_coding_game/env.sh
```

### Inputs

- Experiment name
- Total steps (default: 500 000)
- Number of parallel envs (default: 4)
- Fresh cold start, or resume from checkpoint?
- If resuming: checkpoint path inside the share (`/mnt/data/experiments/...`)

### A) Cold start

```bash
source rl_coding_game/env.sh
./rl_coding_game/remote/aca/run_job.sh \
    -x <EXPERIMENT_NAME> \
    -i "$TRAIN_IMAGE" \
    -s <TOTAL_STEPS> \
    -n <N_ENVS> \
    -r
```

### B) Resume from checkpoint

```bash
source rl_coding_game/env.sh
./rl_coding_game/remote/aca/run_job.sh \
    -x <EXPERIMENT_NAME> \
    -i "$TRAIN_IMAGE" \
    -s <TOTAL_STEPS> \
    -n <N_ENVS> \
    -c /mnt/data/experiments/<GAME>/<EXPERIMENT_NAME>/league_pool/step_<STEP>.pt
```

### Monitoring

```bash
# Check status
az containerapp job execution show \
    -n <JOB_NAME> -g "$AZURE_RG" \
    --job-execution-name <EXEC_NAME> \
    --query properties.status -o tsv

# Stream live logs
az containerapp job logs show \
    -n <JOB_NAME> -g "$AZURE_RG" \
    --execution <EXEC_NAME> --follow true

# List all executions
az containerapp job execution list -n <JOB_NAME> -g "$AZURE_RG" -o table
```

Job name convention: `<game>-<experiment>` (lowercase, hyphens, max 32 chars).

Remote data paths:
- Runs: `/mnt/data/experiments/<game>/<exp>/runs`
- Replay: `/mnt/data/experiments/<game>/<exp>/replay_store`
- Snapshots: `/mnt/data/experiments/<game>/<exp>/league_pool`

To view metrics: use the `tensorboard` skill.

---

## Safety Checks

- Do **not** use `--experiment-name offline_pretrain` (reserved for the immutable expert seed).
- For cold starts: confirm `--reset-replay` / `-r` is set to avoid reusing stale data.
- For resumes: verify checkpoint path exists before launching.
