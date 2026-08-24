# AGENTS – rl_coding_game Framework

This file gives AI agents (Copilot, Claude, GPT, etc.) the exact commands
needed to work with this project without guessing.

For game-specific commands (engine validation, viewer, synthetic replays) see
`games/<GAME>/AGENTS.md`. The reference implementation is at
`games/cellularena/AGENTS.md`.

---

## Execution environment

The developer machine runs **WSL (Linux)**. All local commands use bash; there
is no native PowerShell environment.

| Context | Shell | Python runtime |
|---------|-------|----------------|
| **Local (WSL)** | bash | `conda run -n cellularena` — do **not** assume the env is pre-activated |
| **Remote (ACA Docker)** | container entrypoint | bare `python` — no conda inside the image |

Never use `Get-ChildItem`, `Test-Path`, `Stop-Process`, or other PowerShell
cmdlets for local operations. Use bash equivalents (`ls`, `test`, `pkill`, etc.).

---

## Environment config files

| File | Purpose | Committed? |
|------|---------|-----------|
| `rl_coding_game/env.sh` | Non-secret settings: Azure resource names, conda env name | ✅ yes |
| `rl_coding_game/env.secret.sh` | Credentials: `CG_SESSION`, service principal (if any) | ❌ gitignored |
| `rl_coding_game/env.secret.sh.example` | Template — copy → `env.secret.sh` and fill in | ✅ yes |

Source both at the start of any shell session that talks to Azure or CodingGame:

```bash
source rl_coding_game/env.sh
source rl_coding_game/env.secret.sh  # only if it exists
```

---

## Environment setup

```bash
# One-time: create the conda env
conda env create -f environment.yml

# Every session: activate it before running anything
conda activate cellularena
```

> All commands below assume the working directory is `rl_coding_game/`
> and the `cellularena` conda env is active.

---

## Add a new game

```bash
# Scaffold from a CodingGame URL (only input required):
python scaffold_game.py --url https://www.codingame.com/contests/<PUZZLE_ID>

# Download game rules as plain text:
python download_rules.py --url https://www.codingame.com/contests/<PUZZLE_ID>

# Download expert replays (requires CG_SESSION in .env):
python download_games.py --url https://www.codingame.com/contests/<PUZZLE_ID>
```

Scaffold creates: `games/<GAME>/env.py`, `game/game.py`, `game/replay_loader.py`,
`offline_replay_adapter.py`, `factories.py`, `test_<GAME>.py`, `data/games/<GAME>/`.

After implementing the engine, see `games/<GAME>/AGENTS.md` for game-specific commands.

---

## Run smoke tests

```bash
# Generic per-game smoke test (checks env compiles + random episode terminates)
python test_<GAME>.py

# Replay infrastructure tests
python test_replay.py

# Prioritized replay buffer tests
python test_prioritized_replay.py
```

All suites exit with code 0 on full pass.

---

## Download CodingGame replays

```bash
# From a game URL (derives game name and puzzle slug automatically)
python download_games.py --url https://www.codingame.com/contests/<PUZZLE_ID>

# Override top-N and games per player
python download_games.py --url <URL> --top 10 --per-player 5

# Single game by known ID
python download_games.py --url <URL> --game-id 12345678
```

Replays saved to `data/games/<GAME>/replays/core_<ID>.json`.

---

## Train

### Self-play (cold start)

```bash
python train_rainbow.py \
    --env-factory games.<GAME>.factories:make_env \
    --game <GAME> \
    --experiment-name exp_001 \
    --total-steps 500000 --n-envs 4 --self-play --reset-replay
```

### Resume from checkpoint

```bash
python train_rainbow.py \
    --env-factory games.<GAME>.factories:make_env \
    --game <GAME> \
    --experiment-name exp_001 \
    --total-steps 1000000 --n-envs 4 --self-play \
    --resume-checkpoint experiments/<GAME>/exp_001/checkpoints/checkpoint_0000500000.pt
```

### Offline pretraining from expert replays

```bash
python prefill_replay_buffer.py \
    --adapter games.<GAME>.offline_replay_adapter:create_adapter \
    --game <GAME> \
    --experiment-name offline_pretrain
```

---

## Use the PettingZoo env in code

```python
# Replace <GAME>Env with the actual env class for your game
from games.<GAME>.factories import make_env

env = make_env()
obs, infos = env.reset()

while env.agents:
    actions = {a: env.action_space(a).sample() for a in env.agents}
    obs, rewards, terminations, truncations, infos = env.step(actions)
```

---

## Export trained bot to CodingGame

```bash
python export_to_codingame.py \
    --checkpoint experiments/<GAME>/<EXP>/checkpoints/checkpoint_<step>.pt \
    --output bot_<GAME>.py
```

---

## Project file map

| File | What it does |
|---|---|
| `scaffold_game.py` | Scaffold a new game from a CodingGame URL |
| `download_rules.py` | Download puzzle statement as HTML + plain text |
| `download_games.py` | Download replays from CodingGame API (any puzzle) |
| `train_rainbow.py` | Main training entrypoint (Rainbow DQN + self-play) |
| `prefill_replay_buffer.py` | Seed replay store from offline replay adapter |
| `export_to_codingame.py` | Export trained network as a CodingGame bot |
| `validate_engine.py` | Engine accuracy checker (cellularena; extend per game) |
| `replay_transform.py` | CodingGame → core and core → viewer format conversion |
| `project_paths.py` | Canonical path conventions for experiments and data |
| `test_replay.py` | Replay infrastructure tests |
| `test_prioritized_replay.py` | Prioritized replay buffer tests |
| `rl/` | Game-agnostic RL framework (Rainbow, PPO, self-play, buffers) |
| `games/<GAME>/` | Per-game: env, factories, offline adapter, engine |
| `data/games/<GAME>/replays/` | Shared replay dataset for that game |
| `experiments/<GAME>/<EXP>/` | Per-experiment: runs (TF), replay_store, league_pool |
| `remote/aca/` | Azure Container Apps deployment scripts |

---

## Common tasks for an AI agent

| Task | Command |
|---|---|
| Scaffold new game | `python scaffold_game.py --url <CG_URL>` |
| Download replays | `python download_games.py --url <CG_URL>` |
| Run smoke tests | `python test_<GAME>.py` |
| Validate engine | see `games/<GAME>/AGENTS.md` |
| Start training | `python train_rainbow.py --env-factory games.<GAME>.factories:make_env --game <GAME> --experiment-name <NAME> --total-steps 500000 --n-envs 4 --self-play --reset-replay` |
| View TensorBoard | `tensorboard --logdir experiments/<GAME> --port 6006` |
| Export bot | `python export_to_codingame.py --checkpoint <PATH> --output bot.py` |

---

## Remote GPU training (Azure Container Apps)

All remote training runs via ACA with the `Consumption-GPU-NC8as-T4` workload profile.
Experiment artifacts live in Azure Files (`experiments/` share) mounted at `/mnt/data` inside the container.

Run all remote scripts from the **repo root** in WSL bash after sourcing `env.sh`.

| Task | Command / Skill |
|---|---|
| First-time infra setup | `./rl_coding_game/remote/aca/setup_infra.sh` → skill `aca-setup` |
| Build + push image | `./rl_coding_game/remote/aca/push_image.sh -a $AZURE_ACR_NAME -g $AZURE_RG` |
| Start training job | `./rl_coding_game/remote/aca/run_job.sh -x <name> -i $TRAIN_IMAGE` → skill `run-experiment` |
| View TensorBoard locally | `./rl_coding_game/remote/aca/tensorboard_local.sh -a $AZURE_STORAGE_ACCT` → skill `tensorboard` |

Data paths inside the container:

```
/mnt/data/experiments/<GAME>/<EXP>/runs/          ← TF events
/mnt/data/experiments/<GAME>/<EXP>/replay_store/  ← Parquet / DuckDB
/mnt/data/experiments/<GAME>/<EXP>/league_pool/   ← model snapshots
```

### Docker image

The training image installs Python packages in two steps (no conda in container):

1. `torch` + `torchvision` from `https://download.pytorch.org/whl/cu121` (CUDA-specific)
2. All other deps from `rl_coding_game/requirements.txt` (mirrors `environment.yml`)

**Keep `requirements.txt` and `environment.yml` in sync** whenever you add a dependency.
