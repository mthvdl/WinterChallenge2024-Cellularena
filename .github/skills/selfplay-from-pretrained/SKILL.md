---
name: selfplay-from-pretrained
description: "Use when the user asks to start self-play training from an offline-trained or pretrained checkpoint, run a new experiment that inherits model weights from a previous offline training phase, or bootstrap self-play from an expert-imitation agent."
---

# Self-Play From Pretrained Agent

Start a fresh self-play experiment whose model is **warm-started** from a
checkpoint produced by the offline training phase, with a **clean empty replay
buffer** (no expert data contamination).

---

## Execution context

**Local (WSL)**: Run from the **repo root** in bash using `conda run -n cellularena`.

---

## Step 0 — Detect Current Game and Confirm

**Always do this first, before any other step.**

```bash
# List available games
ls -d pz_cellularena/games/*/

# List existing experiments to find the offline training experiment
ls -d pz_cellularena/experiments/*/ 2>/dev/null || echo "(none)"
```

Then ask the user:

> The detected game is **`<GAME>`** (env-factory: `games.<GAME>.factories:make_env`).
> Offline training experiment: **`<OFFLINE_EXP>`**.
> This skill will start self-play on that game from that checkpoint. Confirm before proceeding?

**Do not proceed until the user explicitly confirms both the game and the source experiment.**

---

## Key Concept

- Model weights come from the offline-trained checkpoint (`--resume-checkpoint`).
- Replay buffer starts completely empty (`--reset-replay`).
- New experiment name → isolated replay_store, runs, and league_pool.
- The offline training experiment is untouched.

## Preconditions

- Workspace root contains `pz_cellularena/`.
- Conda env `cellularena` exists.
- Game `<GAME>` has `pz_cellularena/games/<GAME>/factories.py` with `make_env`.
- A checkpoint `.pt` file exists from a completed or ongoing offline training run.

## Standard Paths

- Offline experiment root: `pz_cellularena/experiments/<GAME>/<OFFLINE_EXP>/`
- Checkpoint pattern: `.../<OFFLINE_EXP>/runs/rainbow_<timestamp>/checkpoints/checkpoint_<step>.pt`
- New experiment root: `pz_cellularena/experiments/<GAME>/<SELFPLAY_EXP>/`

## Step 1 — Locate the Best Checkpoint

```bash
find pz_cellularena/experiments/<GAME>/<OFFLINE_EXP>/runs \
    -name "checkpoint_*.pt" | xargs ls -lt | head -5
```

Pick the checkpoint at the highest step (largest number in the filename).
Verify it exists:

```bash
test -f <CHECKPOINT_PATH> && echo "exists" || echo "MISSING"
```

## Step 2 — Launch Self-Play

```bash
conda run -n cellularena python pz_cellularena/train_rainbow.py \
    --env-factory games.<GAME>.factories:make_env \
    --game <GAME> \
    --experiment-name <SELFPLAY_EXP> \
    --resume-checkpoint <CHECKPOINT_PATH> \
    --total-steps <TOTAL_STEPS> \
    --n-envs <N_ENVS> \
    --self-play \
    --reset-replay
```

### What each flag does

| Flag | Effect |
|------|--------|
| `--resume-checkpoint` | Loads model + optimizer weights from the offline-trained `.pt` file |
| `--reset-replay` | Starts with an empty replay buffer (self-play data only) |
| `--self-play` | Enables league self-play with dynamic opponent pool |
| No `--seed-replay-dir` | Intentional — buffer populated from self-play from scratch |

## Resuming After Interruption

Re-run the **same command** (same `--experiment-name`). The trainer detects the
existing checkpoint in the experiment's own `runs/` directory and resumes. The
`--resume-checkpoint` pointing to the offline experiment is only used on the
very first launch.

To resume from the experiment's *own* latest checkpoint instead:

```bash
conda run -n cellularena python pz_cellularena/train_rainbow.py \
    --env-factory games.<GAME>.factories:make_env \
    --game <GAME> \
    --experiment-name <SELFPLAY_EXP> \
    --resume-checkpoint pz_cellularena/experiments/<GAME>/<SELFPLAY_EXP>/runs/rainbow_<timestamp>/checkpoints/checkpoint_<step>.pt \
    --total-steps <TOTAL_STEPS> \
    --n-envs <N_ENVS> \
    --self-play
```

(No `--reset-replay` when resuming — that would wipe accumulated self-play data.)

## TensorBoard — Compare Offline vs Self-Play

```bash
conda run -n cellularena tensorboard --logdir pz_cellularena/experiments/<GAME> --port 6006
```

## What To Report Back

- **Confirmed game** (from Step 0)
- **Confirmed offline experiment** used as checkpoint source
- Confirmed checkpoint path (verified to exist)
- Confirmed `--reset-replay` is set (fresh buffer)
- TensorBoard command

## Safety Checks

- Verify the checkpoint `.pt` file exists before running.
- Do **not** pass `--seed-replay-dir` — fresh buffer is intentional.
- Do **not** pass `--replay-dir` pointing to the offline experiment's replay_store.
- Do **not** omit `--reset-replay` on first launch of the new experiment.

---

## ── REMOTE (ACA) — Self-Play From Pretrained ───────────────────────────────

Run self-play from a pretrained checkpoint on an ACA GPU job. The checkpoint must
already be accessible in Azure Files (uploaded there by a previous ACA offline
training job, or manually).

### Locate the checkpoint path in Azure Files

```bash
source pz_cellularena/env.sh
KEY=$(az storage account keys list -n "$AZURE_STORAGE_ACCT" -g "$AZURE_RG" \
    --query '[0].value' -o tsv | tr -d '\r')
az storage file list \
    --share-name experiments \
    --path "<GAME>/<OFFLINE_EXP>/runs" \
    --account-name "$AZURE_STORAGE_ACCT" \
    --account-key "$KEY" \
    --query "[?contains(name, 'checkpoint_')].name" -o tsv
```

### Launch the ACA job

```bash
source pz_cellularena/env.sh
./pz_cellularena/remote/aca/run_job.sh \
    -x <SELFPLAY_EXP> \
    -i "$TRAIN_IMAGE" \
    -s <TOTAL_STEPS> \
    -n <N_ENVS> \
    -c /mnt/data/experiments/<GAME>/<OFFLINE_EXP>/runs/rainbow_<timestamp>/checkpoints/checkpoint_<step>.pt \
    -r
```

The `-r` flag resets the replay buffer (fresh self-play data). Do not combine
with `-d` (seed replay dir).
