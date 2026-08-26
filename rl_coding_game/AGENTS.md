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

Scaffold creates: `games/<GAME>/env.py`, `game/game.py`, `game/replay_loader.py`,
`offline_replay_adapter.py`, `factories.py`, `bots/obs_mapper.py`, `test_<GAME>.py`, `data/games/<GAME>/`.

After implementing the engine, see `games/<GAME>/AGENTS.md` for game-specific commands.

---

## Run smoke tests

```bash
# Generic per-game smoke test (checks env compiles + random episode terminates)
python -m pytest Games/<GAME>/engine/tests

# Replay infrastructure tests
python -m pytest Games/<GAME>/engine/tests/test_replay.py

# Prioritized replay buffer tests
python -m pytest Core/tests/test_prioritized_replay.py
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
python -m Core.cli.export_to_codingame \
    --checkpoint experiments/<GAME>/<EXP>/checkpoints/checkpoint_<step>.pt \
    --output bot_<GAME>.py
```

---

## Project file map

| File | What it does |
|---|---|
| `scaffold_game.py` | Scaffold a new game from a CodingGame URL |
| `download_rules.py` | Download puzzle statement as Markdown + HTML + plain text |
| `download_games.py` | Download replays from CodingGame API (any puzzle) |
| `Games/<GAME>/ray/dqn/train.py` | Stock RLlib Rainbow DQN entrypoint |
| `Games/<GAME>/ray/sac/train.py` | Stock RLlib SAC entrypoint |
| `Core/cli/export_to_codingame.py` | Export trained network as a CodingGame bot |
| `validate_engine.py` | Engine accuracy checker (cellularena; extend per game) |
| `replay_transform.py` | CodingGame → core and core → viewer format conversion |
| `project_paths.py` | Canonical path conventions for experiments and data |
| `test_replay.py` | Replay infrastructure tests |
| `Core/ray_*.py` | Game-agnostic Ray environment, policy, training, and metrics helpers |
| `Games/<GAME>/` | Per-game environment, engine, replay, and Ray adapters |
| `data/games/<GAME>/replays/` | Shared replay dataset for that game |
| `Games/<GAME>/experiments/<EXP>/` | Per-experiment Ray checkpoints and metrics |

---

## Common tasks for an AI agent

| Task | Command |
|---|---|
| Scaffold new game | `python scaffold_game.py --url <CG_URL>` |
| Download replays | `python download_games.py --url <CG_URL>` |
| Run smoke tests | `python test_<GAME>.py` |
| Validate engine | see `games/<GAME>/AGENTS.md` |
| Start DQN training | `python -m Games.<GAME>.ray.dqn.train --iterations 10 --checkpoint-dir Games/<GAME>/experiments/dqn` |
| Start SAC training | `python -m Games.<GAME>.ray.sac.train --iterations 10 --checkpoint-dir Games/<GAME>/experiments/sac` |
| View TensorBoard | `tensorboard --logdir experiments/<GAME> --port 6006` |
| Export bot | `python -m Core.cli.export_to_codingame --checkpoint <PATH> --output bot.py` |

---

All training is local. TensorBoard reads the Ray output directory directly:

```bash
tensorboard --logdir Games/<GAME>/experiments --port 6006
```
