# AGENTS – rl_coding_game Framework

This file gives AI agents (Copilot, Claude, GPT, etc.) the exact commands
needed to work with this project without guessing.

For game-specific commands (engine validation, viewer, synthetic replays) see
`Games/<GAME>/AGENTS.md`. The reference implementation is at
`Games/cellularena/AGENTS.md`.

---

## Execution environment

The developer machine runs **WSL (Linux)**. All local commands use bash; there
is no native PowerShell environment.

| Context | Shell | Python runtime |
|---------|-------|----------------|
| **Local (WSL)** | bash | `conda run -n cellularena` — do **not** assume the env is pre-activated |

Never use `Get-ChildItem`, `Test-Path`, `Stop-Process`, or other PowerShell
cmdlets for local operations. Use bash equivalents (`ls`, `test`, `pkill`, etc.).

---

## Environment config files

| File | Purpose | Committed? |
|------|---------|-----------|
| `rl_coding_game/env.sh` | Shared loader that sources per-game non-secret settings | ✅ yes |
| `rl_coding_game/games/<GAME>/env.sh` | Game-specific non-secret settings: conda env + Azure names | ✅ yes |
| `rl_coding_game/env.secret.sh` | Credentials: `CG_SESSION`, service principal (if any) | ❌ gitignored |
| `rl_coding_game/env.secret.sh.example` | Template — copy → `env.secret.sh` and fill in | ✅ yes |

Source both at the start of any shell session that talks to Azure or CodingGame:

```bash
export GAME=cellularena   # or your target game
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
python -m Core.cli.scaffold_game --url https://www.codingame.com/contests/<PUZZLE_ID>

# Download game rules as Markdown:
python -m Core.cli.download_rules --url https://www.codingame.com/contests/<PUZZLE_ID>

# Download expert replays (requires CG_SESSION in .env):
python -m Core.cli.download_games --url https://www.codingame.com/contests/<PUZZLE_ID>
```

Scaffold creates a `Games/<GAME>/` package: `engine/` (game stub, `replay_loader.py`,
`obs/`, `tools/`), `ray/` (DQN + SAC preprocessor/modules/config/train on the new
API stack), `policy/action_mask.py`, `factories.py`, `experiments/` with
`config.yaml.example` files, and smoke tests under `engine/tests/`.

After implementing the engine, see `Games/<GAME>/AGENTS.md` for game-specific commands.

---

## Run smoke tests

```bash
# Generic per-game smoke test (checks env compiles + random episode terminates)
python -m pytest Games/<GAME>/engine/tests

# Replay infrastructure tests
python -m pytest Games/<GAME>/engine/tests/test_replay.py

# Core replay-buffer tests (prioritized multi-agent episode buffer + store)
python -m pytest Core/tests/test_replay_buffer.py Core/tests/test_replay_buffer_store.py

# Core config / training smoke tests (new API stack + ConnectorV2)
python -m pytest Core/tests/test_dqn_config.py Core/tests/test_sac_config.py
```

All suites exit with code 0 on full pass.

---

## Download CodingGame replays

```bash
# From a game URL (derives game name and puzzle slug automatically)
python -m Core.cli.download_games --url https://www.codingame.com/contests/<PUZZLE_ID>

# Override top-N and games per player
python -m Core.cli.download_games --url <URL> --top 10 --per-player 5

# Single game by known ID
python -m Core.cli.download_games --url <URL> --game-id 12345678
```

Replays saved to `Games/<GAME>/experiments/shared/replays/core_<ID>.json`.

---

## Train locally with Ray

Stock RLlib Rainbow DQN and SAC are the supported training paths. Both entry
points register a fresh wrapped environment, support frozen opponents, and can
save checkpoints.

```bash
python -m Games.<GAME>.ray.dqn.train --iterations 10 \
    --checkpoint-dir Games/<GAME>/experiments/dqn
python -m Games.<GAME>.ray.sac.train --iterations 10 \
    --checkpoint-dir Games/<GAME>/experiments/sac
```

---

## Use the PettingZoo env in code

```python
# Replace <GAME>Env with the actual env class for your game
from Games.<GAME>.factories import make_env

env = make_env()
obs, infos = env.reset()

while env.agents:
    actions = {a: env.action_space(a).sample() for a in env.agents}
    obs, rewards, terminations, truncations, infos = env.step(actions)
```

---

## Export trained bot to CodingGame

```bash
python -m Core.cli.export_to_codingame \
    --checkpoint Games/<GAME>/experiments/<ALGO>/<EXP>/checkpoints/checkpoint_<step> \
    --output bot_<GAME>.py
```

---

## Project file map

| File | What it does |
|---|---|
| `Core/cli/scaffold_game.py` | Scaffold a new game from a CodingGame URL |
| `Core/cli/download_rules.py` | Download puzzle statement as Markdown + HTML + plain text |
| `Core/cli/download_games.py` | Download replays from CodingGame API (any puzzle) |
| `Core/cli/preflight_sac.py` | Print the fully resolved SAC settings with each value's source |
| `Core/cli/export_to_codingame.py` | Export trained network as a CodingGame bot |
| `Games/<GAME>/ray/dqn/train.py` | Rainbow DQN entrypoint (RLlib new API stack) |
| `Games/<GAME>/ray/sac/train.py` | SAC entrypoint (RLlib new API stack) |
| `Games/<GAME>/engine/tools/validate_engine.py` | Engine accuracy checker (per game) |
| `Games/<GAME>/engine/tools/replay_transform.py` | CodingGame → core and core → viewer format conversion |
| `Core/project_paths.py` | Canonical path conventions (game, algorithm, experiment) |
| `Games/<GAME>/engine/tests/test_replay.py` | Replay infrastructure tests |
| `Core/ray_*.py` | Game-agnostic Ray env, policy, training, config, metrics, ConnectorV2 helpers |
| `Games/<GAME>/` | Per-game engine, PettingZoo env, and RLlib adapters |
| `Games/<GAME>/experiments/shared/replays/` | Shared replay dataset for that game |
| `Games/<GAME>/experiments/<ALGO>/<EXP>/` | Per-experiment Ray checkpoints, replay buffer, and TensorBoard |

---

## Common tasks for an AI agent

| Task | Command |
|---|---|
| Scaffold new game | `python -m Core.cli.scaffold_game --url <CG_URL>` |
| Download replays | `python -m Core.cli.download_games --url <CG_URL>` |
| Run smoke tests | `python -m pytest Games/<GAME>/engine/tests` |
| Validate engine | see `Games/<GAME>/AGENTS.md` |
| Start DQN training | `python -m Games.<GAME>.ray.dqn.train --iterations 10 --checkpoint-dir Games/<GAME>/experiments/dqn` |
| Start SAC training | `python -m Games.<GAME>.ray.sac.train --iterations 10 --checkpoint-dir Games/<GAME>/experiments/sac` |
| View TensorBoard | `tensorboard --logdir Games/<GAME>/experiments --port 6006` |
| Export bot | `python -m Core.cli.export_to_codingame --checkpoint <PATH> --output bot.py` |

---

All training is local. TensorBoard reads the Ray output directory directly:

```bash
tensorboard --logdir Games/<GAME>/experiments --port 6006
```
