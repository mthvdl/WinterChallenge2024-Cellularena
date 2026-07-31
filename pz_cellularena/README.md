# Cellularena – PettingZoo

Python re-implementation of the [CodingGame Winter Challenge 2024 – Cellularena](https://www.codingame.com/multiplayer/bot-programming/winter-challenge-2024) as a [PettingZoo](https://pettingzoo.farama.org/) `ParallelEnv`.

Remote Azure GPU workflow helpers live under `remote/azure/`.
They cover SSH connection, VM bootstrap, training launch, and TensorBoard
port-forwarding without exposing TensorBoard publicly.

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
cd viewer
npm install
npm run build
cd ..
python -m http.server 8000

# Then open:
# http://localhost:8000/viewer/view/index.html
# and load ../../replays/selfplay_greedy_123.viewer.json

# Runtime conversion mode (no .viewer.json files written):
# 1) start the integrated UI + API server
python viewer_server.py --port 8000
# 2) open http://localhost:8000/viewer/view/index.html
# 3) load a raw replay (codingame_*.json or core_*.json) via "Load Replay"
#    The replay is simulated in-memory and converted to viewer JSON in HTTP response only.

# Download real CodingGame replays (requires account or known game ID)
python download_games.py --no-verify --username YOU --password PW
python download_games.py --game-id 12345678 --no-verify

# Prefill replay storage from offline core replays (game-specific adapter + generic tool)
python prefill_replay_buffer.py --adapter games.cellularena.offline_replay_adapter:create_adapter --glob "data/games/cellularena/replays/core_*.json" --storage-dir replay_store --capacity 200000

# Train Rainbow with the generic PettingZoo trainer entrypoint
python train_rainbow.py --env-factory games.cellularena.factories:make_env --total-steps 200000 --n-envs 4 --self-play --replay-dir replay_store

# Start experiment-centric training layout automatically
python train_rainbow.py --env-factory games.cellularena.factories:make_env --experiment-name exp_001 --total-steps 200000 --n-envs 4 --self-play

# Start a brand-new experiment (fresh logs + fresh replay)
python train_rainbow.py --env-factory games.cellularena.factories:make_env --total-steps 200000 --n-envs 4 --self-play --run-dir runs/exp_001 --replay-dir replay_store_exp_001 --reset-replay

# Resume from a checkpoint while continuing global-step numbering
python train_rainbow.py --env-factory games.cellularena.factories:make_env --total-steps 400000 --n-envs 4 --self-play --run-dir runs/exp_001_resume --replay-dir replay_store_exp_001 --resume-checkpoint runs/exp_001/checkpoints/checkpoint_0002000000.pt

# Monitor training in TensorBoard (from project root)
tensorboard --logdir runs --port 6006
```

## Azure VM remote workflow

The repository includes a small remote-ops toolkit under `remote/azure/`:

```bash
# Local Windows setup for Azure provisioning
powershell -ExecutionPolicy Bypass -File remote/azure/install_azure_cli.ps1
powershell -ExecutionPolicy Bypass -File remote/azure/create_ssh_key.ps1 -KeyPath $HOME/.ssh/cellularena_azure_ed25519

# Then authenticate and create the VM from Windows
powershell -ExecutionPolicy Bypass -File remote/azure/provision_gpu_vm.ps1 -SubscriptionId <SUBSCRIPTION_ID>

# On the Azure VM, from pz_cellularena/
bash remote/azure/bootstrap_vm.sh

# Launch training on the VM
bash remote/azure/run_training.sh smoke_remote 200000 --reset-replay

# Start TensorBoard on the VM, bound to localhost only
bash remote/azure/start_tensorboard.sh
```

From Windows, use the PowerShell helpers to connect and open a tunnel:

```powershell
./remote/azure/connect_vm.ps1 -HostName <PUBLIC_IP> -UserName azureuser -KeyPath C:\keys\cellularena.pem
./remote/azure/open_tensorboard_tunnel.ps1 -HostName <PUBLIC_IP> -UserName azureuser -KeyPath C:\keys\cellularena.pem
```

Then open `http://localhost:6006` locally.

Provisioning defaults are parameterized so you can change Azure region, VM SKU,
resource group, VM name, and SSH key path without editing scripts.

Iterative training workflow:
- Use a unique `--run-dir` per experiment so TensorBoard can compare runs side-by-side.
- Keep `--replay-dir` if you want a warm start from prior experience; add `--reset-replay` for a cold start.
- Use `--resume-checkpoint` to continue model and optimizer state from a prior checkpoint.
- If checkpoint filename does not follow `checkpoint_<step>.pt`, pass `--resume-global-step` explicitly.

---

## Project layout

```

Recommended data layout for iterative RL work:

```
pz_cellularena/
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
pz_cellularena/
├── environment.yml            # conda env (Python 3.11, numpy, pettingzoo, requests)
├── replays/                   # flat replay storage (core + test samples + viewer exports)
├── export_episode_replay.py   # self-play -> core-raw replay export
├── replay_transform.py        # CodingGame->core and core->viewer transformations
├── viewer/                    # standalone TS visualizer (outside game core)
│   ├── ts/                    # copied/adapted viewer sources
│   └── view/                  # static harness + sprite assets
├── games/
│   └── cellularena/
│   ├── __init__.py            # exports CellularenaEnv
│   ├── env.py                 # PettingZoo ParallelEnv wrapper
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
- All display code lives under `viewer/`.

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

## Generic Rainbow framework (game-agnostic core)

The RL stack under `rl/` is structured so algorithm code is reusable across
different two-agent PettingZoo games:

- `rl/bots/dqn_bot.py` – Rainbow/QR-DQN bot (NoisyNet + dueling + PER update logic)
- `rl/rainbow_trainer.py` – generic off-policy training loop
- `rl/n_step.py` – reusable n-step transition wrapper
- `rl/prioritized_replay.py` – DuckDB/SQLite PER storage backend
- `prefill_replay_buffer.py` – generic offline replay prefill CLI via adapter interface

Game-specific replay parsing stays outside `rl/`:

- `games/cellularena/offline_replay_adapter.py` – converts `core_*.json` into transitions
- `games/cellularena/factories.py` – environment factory hook for generic training scripts

To port to a new PettingZoo game, keep algorithm modules unchanged and add:

1. A game package env factory (for `--env-factory module:func`).
2. A replay adapter implementing `rl.offline_adapter.ReplayTransitionAdapter`
  if you want offline prefill from historical games.

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
