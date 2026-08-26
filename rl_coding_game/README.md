# rl_coding_game - Generic CodingGame RL Framework

A framework for training RL agents on any two-player [CodingGame](https://www.codingame.com) puzzle, using [PettingZoo](https://pettingzoo.farama.org/) environments and Ray RLlib Rainbow DQN or SAC.

**Cellularena** (CodingGame Winter Challenge 2024) is the reference implementation. Adding a new game takes ~1 hour of boilerplate + however long it takes to implement the game engine.

---

## Start training on a new game in 5 minutes

> Paste this into GitHub Copilot Chat (agent mode): **"I want to train on a new CodingGame"**  
> The `new-game` skill will guide you through the whole workflow, asking only for the game URL.

Or do it manually:

```bash
# 1. Set up conda environment (one-time)
conda env create -f environment.yml
conda activate cellularena

# 2. Scaffold the new game (only the URL is required)
python -m Core.cli.scaffold_game --url https://www.codingame.com/contests/fall-challenge-2024

# 3. Download game rules as Markdown (helps you implement the engine)
python -m Core.cli.download_rules --url https://www.codingame.com/contests/fall-challenge-2024

# 4. Download expert replays (requires CG_SESSION in .env — see below)
python download_games.py --url https://www.codingame.com/contests/fall-challenge-2024

# 5. Implement the game engine  (see scaffold TODOs in games/<GAME>/game/game.py)

# 6. Run smoke tests
python -m pytest Games/<GAME>/engine/tests

# 7. Train a generated game's Ray algorithm
python -m Games.<GAME>.ray.dqn.train --iterations 10 --checkpoint-dir experiments/<GAME>/dqn
# Or use the continuous-action SAC adapter
python -m Games.<GAME>.ray.sac.train --iterations 10 --checkpoint-dir experiments/<GAME>/sac
```

### CodingGame session cookie (for downloading replays)

1. Log in at https://www.codingame.com in your browser
2. Open DevTools (F12) → Application → Cookies → `https://www.codingame.com`
3. Copy the value of the `cgSession` cookie
4. Create `rl_coding_game/.env` and add: `CG_SESSION=<pasted value>`

---

## Copilot skills (agent mode)

| Say... | Skill invoked |
|---|---|
| "Train on a new CodingGame" | `new-game` — full onboarding: scaffold → rules → replays → implement → train |
| "Download replays for my game" | `download-replays` — leaderboard or single-game replay download |
| "Validate my game engine" | `validate-game` — replay-driven engine correctness check |
| "Run / resume an experiment" | `run-experiment` — local Ray training |
| "Pretrain from expert replays" | `offline-training` — offline imitation pretraining |
| "Start self-play from checkpoint" | `selfplay-from-pretrained` — bootstrap self-play from offline model |
| "View TensorBoard" | `tensorboard` — local Ray metrics |

---

## Cellularena (reference implementation)

---

## Quick start

```bash
# Create and activate the conda environment
conda env create -f environment.yml
conda activate cellularena

# Run the test suite
python test_env.py
python test_replay.py

# Generate synthetic replays and validate the engine
python generate_test_replay.py --count 10
python validate_engine.py

# Export a self-play core replay, then generate viewer data externally
python export_episode_replay.py --seed 123 --policy greedy
python replay_transform.py --mode to-viewer --input replays/selfplay_greedy_123.json --output replays/selfplay_greedy_123.viewer.json

# Build and run the standalone TS viewer
cd Viewer
npm install
npm run build
cd ..
python -m http.server 8000

# Then open:
# http://localhost:8000/Viewer/view/index.html
# and load ../replays/selfplay_greedy_123.viewer.json

# Runtime conversion mode (no .viewer.json files written):
# 1) start the integrated UI + API server
python Viewer/viewer_server.py --port 8000
# 2) open http://localhost:8000/view/index.html
# 3) load a raw replay (codingame_*.json or core_*.json) via "Load Replay"
#    The replay is simulated in-memory and converted to viewer JSON in HTTP response only.

# Download real CodingGame replays (requires account or known game ID)
python download_games.py --no-verify --username YOU --password PW
python download_games.py --game-id 12345678 --no-verify

# Monitor local Ray experiments in TensorBoard (from project root)
tensorboard --logdir Games/cellularena/experiments --port 6006
```

## Local Ray workflow

```bash
python -m Games.cellularena.ray.dqn.train --iterations 10 \
  --checkpoint-dir Games/cellularena/experiments/dqn
tensorboard --logdir Games/cellularena/experiments --port 6006
```

For frozen league opponents, add `--frozen-opponent`, repeat `--opponent-policy`
and pair each with `--opponent-checkpoint`; only the learner policy is updated.

---

## Project layout

Recommended data layout for iterative RL work:

```
rl_coding_game/
├── data/
│   └── games/
│       └── cellularena/
│           └── replays/                  # shared game dataset (downloaded + transformed replays)
└── experiments/
  └── cellularena/
    └── <experiment_name>/
      ├── runs/                     # tensorboard + checkpoints
      ├── replay_store/             # per-experiment replay DB/cache
      └── league_pool/              # self-play snapshots
```

Rule of thumb:
- Downloaded/curated replays are shared per game in `data/games/<game>/replays`.
- Training artifacts and generated data are per experiment under `experiments/<game>/<experiment_name>/`.
rl_coding_game/
├── environment.yml            # conda env (Python 3.11, numpy, pettingzoo, requests)
├── replays/                   # flat replay storage (core + test samples + viewer exports)
├── export_episode_replay.py   # self-play -> core-raw replay export
├── replay_transform.py        # CodingGame->core and core->viewer transformations
├── games/
│   └── cellularena/
│   ├── __init__.py            # exports CellularenaEnv
│   ├── env.py                 # PettingZoo ParallelEnv wrapper
│   ├── viewer/                # standalone TS visualizer for Cellularena
│   │   ├── ts/                # copied/adapted viewer sources
│   │   └── view/              # static harness + sprite assets
│   └── game/
│       ├── coord.py           # Coord, Direction
│       ├── grid.py            # Grid, Tile, Protein
│       ├── organ.py           # Organ, OrganType (with protein costs)
│       ├── grid_maker.py      # random symmetric grid generation
│       ├── game.py            # core game logic + replay API
│       └── replay_loader.py   # parse CodingGame replay JSON
├── test_env.py                # PettingZoo env smoke tests
├── test_replay.py             # replay infrastructure tests
├── generate_test_replay.py    # build synthetic CodingGame-format replays
├── download_games.py          # fetch replays from CodingGame API
└── validate_engine.py         # compare engine output against reference replays
```

Core/visualizer separation:
- `games/cellularena/game/*` and `games/cellularena/env.py` contain only simulation/training logic.
- All display code lives under `games/cellularena/viewer/`.

---

## Game rules (summary)

| Concept | Detail |
|---|---|
| **Grid** | Rectangle ~W×H (W = 2H, H = 8–12), point-symmetric obstacles and proteins |
| **Players** | 2, each starts with one ROOT in opposite corners |
| **Organ types** | ROOT (1A1B1C1D), BASIC (1A), TENTACLE (1B1C), HARVESTER (1C1D), SPORER (1B1D) |
| **Proteins** | A, B, C, D — absorbed when growing onto a tile (+3), harvested each turn by HARVESTERs (+1) |
| **Combat** | A TENTACLE kills the organ it faces; removes entire child subtree |
| **Sporing** | A SPORER fires a new ROOT along its facing line-of-sight |
| **Collision** | Two growths targeting the same cell → both pay cost, cell becomes wall |
| **Turns** | Max 100; also ends on player elimination, grid full, or no progress possible |
| **Score** | Total organ count; tie-break by total proteins |

---

## PettingZoo API

```python
from games.cellularena import CellularenaEnv

env = CellularenaEnv(seed=42)
obs, infos = env.reset()

while env.agents:
    actions = {agent: env.action_space(agent).sample() for agent in env.agents}
    obs, rewards, terminations, truncations, infos = env.step(actions)
```

### Observation space (per agent)

`Dict`:
- `"grid"` — `Box(float32, shape=(12, 24, 17))` — one-hot grid encoding:
  - ch 0: obstacle
  - ch 1–4: proteins A/B/C/D
  - ch 5–9: player-0 organ type (ROOT/BASIC/TENTACLE/HARVESTER/SPORER)
  - ch 10–14: player-1 organ type
  - ch 15–16: organ facing direction (0–1 normalised) for each player
- `"storage"` — `Box(float32, shape=(2, 4))` — proteins A/B/C/D per player ÷ 50
- `"turn"` — `Box(float32, shape=(1,))` — turn ÷ 100

### Action space (per agent)

`MultiDiscrete([69] * 5)` — 5 organism slots, 69 actions each:

| Range | Action |
|---|---|
| `0` | WAIT |
| `1–64` | GROW — decode `raw = action − 1`; `growth_dir = raw // 16`, `facing_dir = (raw // 4) % 4`, `organ_type = raw % 4` (0=BASIC, 1=TENTACLE, 2=HARVESTER, 3=SPORER) |
| `65–68` | SPORE — fire ROOT from SPORER facing direction `action − 65` |

### Rewards

Sparse, terminal-only:

| Outcome | Player reward |
|---|---|
| Win (more organs) | +1.0 |
| Loss | −1.0 |
| Tie-break win (more proteins) | +0.5 |
| Tie-break loss | −0.5 |
| True tie | 0.0 |

---

## Viewer controls

| Key | Action |
|---|---|
| `←` / `→` | Previous / next turn |
| `Space` | Play / pause auto-advance |
| `+` / `−` | Speed up / slow down (fps) |
| `R` | Restart from turn 0 |
| `Q` / `Esc` | Quit |

---

## Generic Ray framework (game-agnostic core)

The Ray stack under `Core/` is reusable across two-agent PettingZoo games:

- `Core/ray_env.py` – environment registration helpers
- `Core/ray_config.py` – configuration overrides
- `Core/ray_policies.py` – shared and frozen policy setup
- `Core/ray_training.py` – checkpointing and metric callbacks

To port to a new PettingZoo game, add:

1. A game package environment wrapper and factory.
2. DQN and SAC config/train modules under `Games/<GAME>/ray/`.

---

## Downloading real replays

The CodingGame API requires authentication for leaderboard queries.  
Three options:

**A) Provide credentials:**
```bash
python download_games.py --no-verify --username YOUR_LOGIN --password YOUR_PW --top 5
```

**B) Download by known game ID:**
```bash
python download_games.py --no-verify --game-id 12345678
```

**C) Manual browser export:**
1. Open a game replay on [codingame.com](https://www.codingame.com/multiplayer/bot-programming/winter-challenge-2024)
2. DevTools → Network → find `findByGameId` POST response
3. Copy the JSON body -> save as `replays/codingame_<gameId>.json`

---

## Engine validation

```bash
python generate_test_replay.py --count 10   # create synthetic raw replays
python validate_engine.py                   # compare engine vs CodingGame/synthetic samples in replays/
python validate_engine.py --loop            # re-run after manual fixes
```

The validator infers the initial protein storage via brute-force search (8⁴ = 4096 combinations), then replays every command from the reference stdout and compares storage turn-by-turn.

Current status: **10/10 synthetic replays — 100% accurate**.
