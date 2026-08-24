---
name: tensorboard
description: "Use when the user wants to view TensorBoard metrics for a training experiment — either from a local experiment directory (WSL) or synced from Azure Files (remote ACA experiment). Asks whether the experiment is local or remote before running."
---

# TensorBoard

Use this skill to launch TensorBoard for any training experiment, local or remote.

---

## Step 0 — Ask: LOCAL or REMOTE experiment?

> Are you viewing a **local** experiment (artifacts in `rl_coding_game/experiments/`) or a **remote** experiment (artifacts on Azure Files from an ACA job)?

---

## ── LOCAL ──────────────────────────────────────────────────────────────────

Artifacts are already on disk. Just launch TensorBoard.

### Single experiment

```bash
conda run -n cellularena tensorboard \
    --logdir rl_coding_game/experiments/<GAME>/<EXPERIMENT_NAME>/runs \
    --port 6006
```

### Compare all experiments for a game

```bash
conda run -n cellularena tensorboard \
    --logdir rl_coding_game/experiments/<GAME> \
    --port 6006
```

---

## ── REMOTE (ACA) ────────────────────────────────────────────────────────────

Event files live in Azure Files at:
```
experiments/<game>/<experiment>/runs/events.out.tfevents.*
```

The script syncs them locally then launches TensorBoard.

### Inputs

- Storage account name (`$AZURE_STORAGE_ACCT` from `env.sh`)
- Experiment name (leave empty to view all experiments for the game)
- Watch mode? (`-w` keeps re-syncing every 30 s)

### View a single experiment

```bash
source rl_coding_game/env.sh
./rl_coding_game/remote/aca/tensorboard_local.sh \
    -a "$AZURE_STORAGE_ACCT" \
    -x <EXPERIMENT_NAME>
```

### Compare all experiments for the game

```bash
source rl_coding_game/env.sh
./rl_coding_game/remote/aca/tensorboard_local.sh \
    -a "$AZURE_STORAGE_ACCT"
```

### Keep syncing during live training

```bash
source rl_coding_game/env.sh
./rl_coding_game/remote/aca/tensorboard_local.sh \
    -a "$AZURE_STORAGE_ACCT" \
    -x <EXPERIMENT_NAME> \
    -w
```

### Manual sync without launching TensorBoard

```bash
source rl_coding_game/env.sh
KEY=$(az storage account keys list -n "$AZURE_STORAGE_ACCT" -g "$AZURE_RG" \
    --query '[0].value' -o tsv | tr -d '\r')
az storage file download-batch \
    --source experiments \
    --destination /tmp/cellularena_tb \
    --account-name "$AZURE_STORAGE_ACCT" \
    --account-key "$KEY" \
    --pattern "experiments/<GAME>/<EXPERIMENT>/runs/events.out.tfevents.*"
```

---

## What To Report Back

- Local logdir path where events were synced (remote) or read from (local)
- TensorBoard URL: `http://localhost:<port>`
