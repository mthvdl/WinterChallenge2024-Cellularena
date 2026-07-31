---
name: offline-training
description: "Use when the user asks to train a bot from downloaded expert games, run offline pretraining, seed a replay buffer from top-player replays, or start an experiment that learns from the offline_pretrain replay store."
---

# Offline Training (Expert Game Imitation)

Train a Rainbow DQN agent that learns purely from top-player CodingGame replays
before any self-play, using the pre-filled expert replay buffer.

---

## Execution context

**Local (WSL)**: Run from the **repo root** in bash using `conda run -n cellularena`.

---

## Step 0 — Detect Current Game and Confirm

**Always do this first, before any other step.**

```bash
# List available games
ls -d pz_cellularena/games/*/

# List existing experiments
ls -d pz_cellularena/experiments/*/ 2>/dev/null || echo "(none)"
```

Then ask the user:

> The detected game is **`<GAME>`** (env-factory: `games.<GAME>.factories:make_env`).
> This skill will operate on that game. Confirm before proceeding? (yes / pick a different game)

**Do not proceed until the user explicitly confirms the game.**

---

## ⛔ HARD RULES — Read Before Doing Anything Else

These rules are **non-negotiable**. Violating any one of them permanently destroys
the expert dataset and requires a multi-hour re-download + re-parse.

| # | Rule | Why |
|---|------|-----|
| 1 | **NEVER** pass `--replay-dir` pointing to `offline_pretrain/replay_store` | Training writes self-play transitions directly into that dir, corrupting expert data |
| 2 | **NEVER** pass `--reset-replay` in any command that uses `--seed-replay-dir` | `--reset-replay` runs **after** the seed copy, wiping the just-copied expert data |
| 3 | **NEVER** pass `--experiment-name offline_pretrain` for a training run | That experiment's replay_store IS the immutable seed; training would write into it |
| 4 | **NEVER** delete or move `offline_pretrain/replay_store/replay.duckdb` | It takes hours to rebuild |
| 5 | The only two operations ever allowed on `offline_pretrain/replay_store` are: **read** (via `--seed-replay-dir`) and **rebuild** (via `prefill_replay_buffer.py --clear-first`) | Everything else is forbidden |

If the user asks to do anything that would break rule 1–5, **refuse and explain**.

---

## Pre-flight Verification (Run Before Every Launch)

```bash
# 1. Confirm the seed store exists
test -f pz_cellularena/experiments/<GAME>/offline_pretrain/replay_store/replay.duckdb \
    && echo "seed store OK" || echo "MISSING — rebuild required"

# 2. Confirm the experiment name is NOT "offline_pretrain"
echo "Experiment name: <EXPERIMENT_NAME>"   # must differ from offline_pretrain

# 3. Confirm the launch command contains --seed-replay-dir and NO --replay-dir / --reset-replay
```

**Do not proceed if step 1 shows MISSING or if step 2/3 checks fail.**

---

## Key Concept

- `pz_cellularena/experiments/<GAME>/offline_pretrain/replay_store` is the
  **immutable expert buffer** — read-only data asset, never a training target.
- `--seed-replay-dir` copies it into the **new experiment's own** replay_store on
  first launch only. Re-runs skip the copy automatically.
- Omit `--reset-replay` and `--replay-dir` — both are intentionally absent.

## Preconditions

- Workspace root contains `pz_cellularena/`.
- Conda env `cellularena` exists.
- Game `<GAME>` has `pz_cellularena/games/<GAME>/factories.py` with `make_env`.
- Expert buffer exists:
  `pz_cellularena/experiments/<GAME>/offline_pretrain/replay_store/replay.duckdb`
  If missing → run **Rebuilding the Expert Buffer** below first.

## Standard Paths

| Path | Role |
|------|------|
| `pz_cellularena/experiments/<GAME>/offline_pretrain/replay_store/` | **Immutable seed** — never written to by training |
| `pz_cellularena/experiments/<GAME>/<EXPERIMENT_NAME>/replay_store/` | Working copy — created by `--seed-replay-dir`, augmented by self-play |
| `pz_cellularena/experiments/<GAME>/<EXPERIMENT_NAME>/runs/` | TensorBoard logs + checkpoints |
| `pz_cellularena/experiments/<GAME>/<EXPERIMENT_NAME>/league_pool/` | Self-play snapshots |

## Inputs To Ask Or Confirm

- Game (confirmed in Step 0)
- Experiment name — must NOT be `offline_pretrain` (example: `offline_train_v1`)
- Total steps (recommended: 500 000 – 2 000 000)
- Number of parallel envs (default: 4)

## Command — Offline Training

```bash
conda run -n cellularena python pz_cellularena/train_rainbow.py \
    --env-factory games.<GAME>.factories:make_env \
    --game <GAME> \
    --experiment-name <EXPERIMENT_NAME> \
    --seed-replay-dir pz_cellularena/experiments/<GAME>/offline_pretrain/replay_store \
    --total-steps <TOTAL_STEPS> \
    --n-envs <N_ENVS> \
    --self-play
```

**Absent flags and why:**

| Missing flag | Reason |
|---|---|
| `--replay-dir` | Auto-resolved to `experiments/<GAME>/<EXPERIMENT_NAME>/replay_store/` |
| `--reset-replay` | Would wipe the seeded expert data on startup |

## Resuming a Failed / Interrupted Run

Re-run the **exact same command** unchanged. Seed copy is skipped; trainer resumes
from the latest checkpoint automatically.

## Rebuilding the Expert Buffer From Scratch

Only run if `offline_pretrain/replay_store/replay.duckdb` is missing or corrupt.
**Confirm with the user first — this is destructive on the seed store.**

### Step 1 — Download top-player games

Requires `CG_SESSION` set in `pz_cellularena/env.secret.sh`.

```bash
source pz_cellularena/env.secret.sh

conda run -n cellularena python pz_cellularena/download_games.py \
    --top 100 --per-player 35 --delay 0.5 --keep-samples 0 --no-verify
```

### Step 2 — Prefill the expert buffer

```bash
conda run -n cellularena python pz_cellularena/prefill_replay_buffer.py \
    --adapter games.<GAME>.offline_replay_adapter:create_adapter \
    --storage-dir pz_cellularena/experiments/<GAME>/offline_pretrain/replay_store \
    --capacity 500000 \
    --clear-first
```

## Locating the Best Checkpoint After Training

```bash
find pz_cellularena/experiments/<GAME>/<EXPERIMENT_NAME>/runs \
    -name "checkpoint_*.pt" | xargs ls -lt | head -5
```

## TensorBoard

```bash
conda run -n cellularena tensorboard \
    --logdir pz_cellularena/experiments/<GAME>/<EXPERIMENT_NAME>/runs --port 6006
```

## What To Report Back

- **Confirmed game** (from Step 0)
- Experiment name (confirmed ≠ `offline_pretrain`)
- Seed store existence check result
- Whether seed copy was performed (first run) or skipped (resume)
- Full path to the experiment's replay_store (working copy)
- TensorBoard command

---

## ── REMOTE (ACA) — Offline Training ────────────────────────────────────────

Run the same offline training on an ACA GPU job. The seed replay store must
already be uploaded to Azure Files before launching.

### Step 0 — Upload the seed replay store (first time only)

```bash
source pz_cellularena/env.sh
./pz_cellularena/remote/aca/upload_offline_pretrain.ps1 \
    -StorageAccount "$AZURE_STORAGE_ACCT"
```

Or, to upload from WSL:

```bash
source pz_cellularena/env.sh
KEY=$(az storage account keys list -n "$AZURE_STORAGE_ACCT" -g "$AZURE_RG" \
    --query '[0].value' -o tsv | tr -d '\r')
az storage file upload-batch \
    --source pz_cellularena/experiments/<GAME>/offline_pretrain/replay_store \
    --destination experiments \
    --destination-path "<GAME>/offline_pretrain/replay_store" \
    --account-name "$AZURE_STORAGE_ACCT" \
    --account-key "$KEY" \
    --overwrite false
```

### Step 1 — Launch the ACA job

```bash
source pz_cellularena/env.sh
./pz_cellularena/remote/aca/run_job.sh \
    -x <EXPERIMENT_NAME> \
    -i "$TRAIN_IMAGE" \
    -s <TOTAL_STEPS> \
    -n <N_ENVS> \
    -d /mnt/data/experiments/<GAME>/offline_pretrain/replay_store
```

The same hard rules apply: `-d` must point to `offline_pretrain/replay_store`,
never the destination experiment's store. Never combine `-d` with `-r`.
