# AGENTS – Cellularena

Game-specific commands for the [Cellularena](https://www.codingame.com/multiplayer/bot-programming/winter-challenge-2024) implementation (CodingGame Winter Challenge 2024).

For generic framework commands (training and downloading), see `rl_coding_game/AGENTS.md`.

> All commands assume working directory is `rl_coding_game/` and the `cellularena` conda env is active.

---

## Run tests

```bash
# PettingZoo env smoke tests
python test_env.py

# Replay infrastructure tests
python test_replay.py
```

## Run stock Ray algorithms

```bash
# Rainbow DQN, native Discrete(4033) action space
python -m Games.cellularena.ray.dqn.train --iterations 1

# SAC, explicit scalar Box action adapter mapped to Discrete(4033)
python -m Games.cellularena.ray.sac.train --iterations 1

# Train only player 0 while player 1 uses a separate frozen policy
python -m Games.cellularena.ray.dqn.train --iterations 1 --frozen-opponent

# Initialize that opponent from a prior shared-policy checkpoint
python -m Games.cellularena.ray.dqn.train --iterations 1 \
    --frozen-opponent --opponent-checkpoint <checkpoint-dir>
```

Both smoke commands default to zero environment runners. Increase them with
`--num-env-runners <count>` after the local smoke passes. Checkpoints can be
written with `--checkpoint-dir <path>`.

---

## Generate synthetic replays

Needed before engine validation if no real replays have been downloaded yet.

```bash
python generate_test_replay.py            # 5 replays (seeds 0-4)
python generate_test_replay.py --count 10
```

Output: `replays/synthetic_9000000XX.json`

---

## Validate the engine

```bash
# Validate all replays in replays/
python validate_engine.py

# Validate a specific file
python validate_engine.py replays/synthetic_900000000.json

# Loop mode: re-run automatically after fixing a bug
python validate_engine.py --loop
```

Success:
```
Engine is 100% accurate on all replays!
```

Failure:
```
FAIL  T12 P0 storage: engine=A:5 B:3 C:2 D:1  ref=A:5 B:3 C:2 D:2
```

Fix failures by editing `Games/cellularena/engine/game.py`, then re-run.

---

## Export self-play replay for viewer

```bash
python export_episode_replay.py --seed 123 --policy greedy
python replay_transform.py --mode to-viewer \
    --input replays/selfplay_greedy_123.json \
    --output replays/selfplay_greedy_123.viewer.json
```

---

## Visualize a replay (standalone TS viewer)

```bash
cd Viewer
npm install
npm run build
cd ..
python -m http.server 8000
# Open: http://localhost:8000/Viewer/view/index.html
# Load: ../replays/selfplay_greedy_0.viewer.json
```

Runtime conversion (no `.viewer.json` files written):

```bash
python Viewer/viewer_server.py --port 8000
# Open the viewer URL and use "Load Replay" to load a raw core_*.json
```

### Viewer keyboard controls

| Key | Action |
|---|---|
| `Play/Pause` | Start/stop playback |
| `Prev/Next` | Previous/next turn |
| `Turn slider` | Jump to a turn |
| `Speed` | Change playback speed |

---

## Project file map

| File | What it does |
|---|---|
| `games/cellularena/env.py` | PettingZoo `ParallelEnv` |
| `games/cellularena/factories.py` | `make_env()` factory |
| `games/cellularena/engine/obs_mapper.py` | `CellularenaObsMapper` — override to preprocess obs before the network |
| `games/cellularena/offline_replay_adapter.py` | Converts core replays → RL transitions |
| `games/cellularena/game/game.py` | All game logic, rules, replay API |
| `games/cellularena/game/grid.py` | Grid, Tile, Protein |
| `games/cellularena/game/organ.py` | Organ, OrganType (with protein costs) |
| `games/cellularena/game/grid_maker.py` | Random symmetric grid generation |
| `games/cellularena/game/coord.py` | Coord, Direction |
| `games/cellularena/game/replay_loader.py` | Parse CodingGame replay JSON |
| `Viewer/` | Standalone TypeScript replay visualizer |
| `test_env.py` | PettingZoo env smoke tests |
| `test_replay.py` | Replay infrastructure tests |
| `generate_test_replay.py` | Build synthetic replays for validation |
| `export_episode_replay.py` | Export self-play replay for viewer |
| `validate_engine.py` | Engine accuracy checker against CodingGame replays |
| `Viewer/viewer_server.py` | Runtime conversion server (load raw replay via HTTP) |

---

## Game rules summary

| Concept | Detail |
|---|---|
| **Grid** | ~W×H rectangle (W=2H, H=8–12), point-symmetric obstacles and proteins |
| **Players** | 2, each starts with one ROOT in opposite corners |
| **Organ types** | ROOT (1A1B1C1D), BASIC (1A), TENTACLE (1B1C), HARVESTER (1C1D), SPORER (1B1D) |
| **Proteins** | A, B, C, D — absorbed when growing onto (+3), harvested by HARVESTERs (+1/turn) |
| **Combat** | A TENTACLE kills the organ it faces; removes entire child subtree |
| **Sporing** | A SPORER fires a new ROOT along its facing line-of-sight |
| **Collision** | Two growths targeting same cell → both pay cost, cell becomes wall |
| **Turns** | Max 100; also ends on elimination, grid full, or no progress |
| **Score** | Total organ count; tie-break by total proteins |

---

## Observation space

`Dict` per agent:
- `"grid"` — `Box(float32, shape=(12, 24, 17))` — 17 channels (obstacles, proteins, organs per player, directions)
- `"storage"` — `Box(float32, shape=(2, 4))` — A/B/C/D counts per player, normalised ÷50
- `"turn"` — `Box(float32, shape=(1,))` — current turn / MAX_TURNS

## Action space

`MultiDiscrete([69] * 5)` per agent — 5 organism slots × 69 actions:
- `0` → WAIT
- `1..64` → GROW (encodes direction × facing × type)
- `65..68` → SPORE (direction)

---

## Common tasks for an AI agent

| Task | Command |
|---|---|
| Check everything works | `python test_env.py && python test_replay.py` |
| Generate + validate engine | `python generate_test_replay.py && python validate_engine.py` |
| Build viewer | `cd Viewer && npm install && npm run build` |
| Export training replay | `python export_episode_replay.py --seed 123 --policy greedy` |
| Fix validation failure | Edit `games/cellularena/game/game.py`, re-run `python validate_engine.py` |
| Train with Rainbow DQN | `python -m Games.cellularena.ray.dqn.train --iterations 10 --checkpoint-dir Games/cellularena/experiments/dqn` |
| Train with SAC | `python -m Games.cellularena.ray.sac.train --iterations 10 --checkpoint-dir Games/cellularena/experiments/sac` |
