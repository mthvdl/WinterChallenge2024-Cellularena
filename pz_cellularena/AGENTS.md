# AGENTS – Cellularena PettingZoo

This file gives AI agents (Copilot, Claude, GPT, etc.) the exact commands
needed to work with this project without guessing.

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
| `pz_cellularena/env.sh` | Non-secret settings: Azure resource names, conda env name, game | ✅ yes |
| `pz_cellularena/env.secret.sh` | Credentials: `CG_SESSION`, service principal (if any) | ❌ gitignored |
| `pz_cellularena/env.secret.sh.example` | Template — copy → `env.secret.sh` and fill in | ✅ yes |

Source both at the start of any shell session that talks to Azure or CodingGame:

```bash
source pz_cellularena/env.sh
source pz_cellularena/env.secret.sh  # only if it exists
```

---

## Environment setup

```bash
# One-time: create the conda env
conda env create -f environment.yml

# Every session: activate it before running anything
conda activate cellularena
```

> All commands below assume the working directory is `pz_cellularena/`
> and the `cellularena` env is active.

---

## Run tests

```bash
# PettingZoo environment smoke tests (5 tests)
python test_env.py

# Replay infrastructure tests (4 tests)
python test_replay.py
```

Both suites exit with code 0 on full pass.

---

## Generate synthetic replays

Needed before validation if no real replays have been downloaded.

```bash
python generate_test_replay.py            # 5 replays (seeds 0-4)
python generate_test_replay.py --count 10 # 10 replays
```

Output: `replays/synthetic_9000000XX.json`

## Export self-play replay for viewer

```bash
python export_episode_replay.py --seed 123 --policy greedy
python export_episode_replay.py --seed 123 --policy random --output replays/train_123.json
python replay_transform.py --mode to-viewer --input replays/train_123.json --output replays/train_123.viewer.json
```

Output: core replay `replays/selfplay_<policy>_<seed>.json` plus optional viewer replay via `replay_transform.py`.

---

## Validate the engine

```bash
# Validate default CodingGame/synthetic samples in replays/
python validate_engine.py

# Validate a specific file
python validate_engine.py replays/synthetic_900000000.json

# Loop mode: re-run automatically after you fix a bug
python validate_engine.py --loop
```

Success looks like:
```
Engine is 100% accurate on all replays!
```

Any discrepancy is reported as:
```
FAIL  T12 P0 storage: engine=A:5 B:3 C:2 D:1  ref=A:5 B:3 C:2 D:2
```

---

## Visualize a replay (standalone TS viewer)

```bash
# Build the viewer bundle
cd viewer
npm install
npm run build

# Serve files from project root
cd ..
python -m http.server 8000

# Open in browser:
# http://localhost:8000/viewer/view/index.html
# Then load ../../replays/selfplay_greedy_0.viewer.json
```

### Keyboard controls

| Key | Action |
|---|---|
| `Play/Pause` | Start/stop playback |
| `Prev/Next` | Previous/next turn |
| `Turn slider` | Jump to a turn |
| `Speed` | Change playback speed |

---

## Download real CodingGame replays

```bash
# With credentials
python download_games.py --no-verify --username LOGIN --password PW

# By game ID (from the CodingGame replay URL or DevTools)
python download_games.py --no-verify --game-id 12345678

# Override the number of top players and games per player
python download_games.py --no-verify --username LOGIN --password PW --top 5 --per-player 3
```

Downloaded games are converted to `replays/core_<gameId>.json` for core-engine use.
Only a small sample of original CodingGame replays is kept as `replays/codingame_<gameId>.json` for validation.
Viewer-ready replays are generated externally from core raw via `replay_transform.py`.

---

## Use the PettingZoo env in code

```python
from games.cellularena import CellularenaEnv

env = CellularenaEnv(seed=42)
obs, infos = env.reset()

while env.agents:
    actions = {a: env.action_space(a).sample() for a in env.agents}
    obs, rewards, terminations, truncations, infos = env.step(actions)
```

---

## Project file map

| File | What it does |
|---|---|
| `games/cellularena/env.py` | PettingZoo `ParallelEnv` |
| `games/cellularena/game/game.py` | All game logic, rules, replay API |
| `games/cellularena/game/grid.py` | Grid, Tile, Protein |
| `games/cellularena/game/organ.py` | Organ, OrganType (with costs) |
| `games/cellularena/game/grid_maker.py` | Random symmetric grid generation |
| `games/cellularena/game/coord.py` | Coord, Direction |
| `games/cellularena/game/replay_loader.py` | Parse CodingGame replay JSON |
| `viewer/view/assets/` | Sprite sheets (PNG + JSON atlas) |
| `viewer/` | Standalone TS replay visualizer |
| `replays/` | Flat replay storage (core raw, codingame samples, synthetic, viewer exports) |
| `test_env.py` | PettingZoo env tests |
| `test_replay.py` | Replay infrastructure tests |
| `generate_test_replay.py` | Build synthetic replays |
| `export_episode_replay.py` | Export self-play replay for standalone viewer |
| `download_games.py` | CodingGame API downloader |
| `validate_engine.py` | Engine accuracy checker |

---

## Common tasks for an AI agent

| Task | Command |
|---|---|
| Check everything works | `python test_env.py && python test_replay.py` |
| Validate engine accuracy | `python generate_test_replay.py && python validate_engine.py` |
| Build viewer | `cd viewer && npm install && npm run build` |
| Open replay in viewer | Run `python -m http.server 8000` and open `/viewer/view/index.html` |
| Export a training replay | `python export_episode_replay.py --seed 123 --policy greedy` |
| Fix a validation failure | Edit `games/cellularena/game/game.py`, then re-run `python validate_engine.py` |

---

## Remote GPU training (Azure Container Apps)

All remote training runs via ACA with the `Consumption-GPU-NC8as-T4` workload profile.
Experiment artifacts live in Azure Files (`experiments/` share) mounted at `/mnt/data` inside the container.

Run all remote scripts from the **repo root** in WSL bash after sourcing `env.sh`.

| Task | Command / Skill |
|---|---|
| First-time infra setup | `./pz_cellularena/remote/aca/setup_infra.sh` → skill `aca-setup` |
| Build + push image | `./pz_cellularena/remote/aca/push_image.sh -a $AZURE_ACR_NAME -g $AZURE_RG` |
| Start training job | `./pz_cellularena/remote/aca/run_job.sh -x <name> -i $TRAIN_IMAGE` → skill `run-experiment` |
| View TensorBoard locally | `./pz_cellularena/remote/aca/tensorboard_local.sh -a $AZURE_STORAGE_ACCT` → skill `tensorboard` |

Data paths inside the container:

```
/mnt/data/experiments/<game>/<experiment>/runs/          ← TF events
/mnt/data/experiments/<game>/<experiment>/replay_store/  ← Parquet / DuckDB
/mnt/data/experiments/<game>/<experiment>/league_pool/   ← model snapshots
```

### Docker image

The training image installs Python packages in two steps (no conda in container):

1. `torch` + `torchvision` from `https://download.pytorch.org/whl/cu121` (CUDA-specific)
2. All other deps from `pz_cellularena/requirements.txt` (mirrors `environment.yml`)

**Keep `requirements.txt` and `environment.yml` in sync** whenever you add a dependency.
