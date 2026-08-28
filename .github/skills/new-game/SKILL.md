---
name: new-game
description: "Use when the user wants to add a new CodingGame to the rl_coding_game framework — from a game URL, create the scaffold, download replays, implement the engine, and run the first training experiment."
---

# New Game Onboarding

Use this skill to onboard a new CodingGame into the rl_coding_game framework end-to-end.

---

## Step 0 — Gather inputs interactively

Ask the user **only** what you don't already know.

Required inputs:
- Game URL
- Conda environment name to create/use for this workflow
- Board symmetry and player-perspective transform

**Ask:**
> What is the CodingGame URL for the game you want to train on?
> (e.g. `https://www.codingame.com/contests/fall-challenge-2024`)

> What conda environment name should I create/use for this game?
> (e.g. `cellularena`)

> What board symmetry does the game use between players, and how should an
> observation be transformed into the active player's perspective?
> Specify the spatial transform (for example: none, left-right, top-bottom,
> or 180-degree rotation) and the direction remapping (N/E/S/W). If unknown,
> inspect the game rules, replay coordinates, and map generator before
> implementing observations.

Then derive everything else automatically:
- **Puzzle slug** = last path segment of the URL (e.g. `fall-challenge-2024`)
- **Game name** = puzzle slug with `-` replaced by `_` (e.g. `fall_challenge_2024`)

If the user already provided a URL in their message, use it directly — do not ask again.
If the user already provided the conda env name, use it directly — do not ask again.

**Only ask if the user wants to override defaults:**
- Local game name (default: derived from URL)
- Algorithm: Rainbow DQN (default) or PPO?

Save the answer as the canonical game-level contract at:
`rl_coding_game/Games/<GAME>/symmetry.md`.
Create it before implementing map generation or observations, and require all
components that need player-relative coordinates to read it, including game
generation, replay conversion, self-play, and inference.
Document the board transform for each player perspective, coordinate origin,
N/E/S/W mapping, and whether player-indexed channels, storage, actions, and
replays are swapped.

---

## Step 1 — Create or reuse conda environment

```bash
cd /path/to/repo/rl_coding_game
conda env list
```

If `<CONDA_ENV>` does not exist:

```bash
cd /path/to/repo/rl_coding_game
conda create -n <CONDA_ENV> python=3.11 -y
conda run -n <CONDA_ENV> python -m pip install -r requirements.txt
```

Persist the chosen env by scaffolding with `--conda-env <CONDA_ENV>` (this updates `rl_coding_game/Games/<GAME>/env.sh` with `CONDA_ENV=<CONDA_ENV>`).

---

## Step 2 — Download game rules first (Markdown)

This is the first game-onboarding action after env setup. Run it before scaffolding or replay download.

```bash
cd /path/to/repo/rl_coding_game
conda run -n <CONDA_ENV> python Core/cli/download_rules.py \
    --url <GAME_URL> \
    --game <GAME>
```

Rules are saved to:
- `rl_coding_game/Games/<GAME>/rules.md` (primary, implementation notes)
- `rl_coding_game/data/games/<GAME>/rules.md` (shared data copy)
- `rl_coding_game/data/games/<GAME>/rules.html` (raw)
- `rl_coding_game/data/games/<GAME>/rules.txt` (plain text)

Before writing `game.py`, read `rl_coding_game/Games/<GAME>/rules.md` and extract these sections explicitly:
- Endgame rules (termination + victory/defeat)
- Order of actions / turn resolution order
- Constraints (input limits, time, map/turn limits)

Use those as acceptance criteria for engine behavior.

Also read `rl_coding_game/Games/<GAME>/symmetry.md` and use it as the single
source of truth for symmetric map generation and player-relative transforms.

> If the API fails, open the game page in a browser and copy the rules manually.

---

## Step 3 — Scaffold the game

```bash
cd /path/to/repo/rl_coding_game
conda run -n <CONDA_ENV> python Core/cli/scaffold_game.py \
    --puzzle-id <PUZZLE_ID> \
    --game <GAME> \
    --conda-env <CONDA_ENV>
```

This creates:
- `rl_coding_game/Games/<GAME>/` — env, factories, offline adapter, game engine stubs
- `rl_coding_game/Games/<GAME>/ray/dqn/feature_builder.py` — no-op DQN feature-builder class
- `rl_coding_game/Games/<GAME>/ray/sac/feature_builder.py` — no-op SAC feature-builder class
- `rl_coding_game/Games/<GAME>/ray/dqn/modules.py` — no-op DQN network customization class with an uncommentable model example
- `rl_coding_game/Games/<GAME>/ray/sac/modules.py` — no-op SAC network customization class for RLlib's current RLModule/catalog API
- `rl_coding_game/Games/<GAME>/policy/action_mask.py` — no-op discrete action-mask-builder class
- `rl_coding_game/Games/<GAME>/bots/action_mapper.py` — protocol command mapping stub
- `rl_coding_game/data/games/<GAME>/replays/` — empty replay store
- `rl_coding_game/test_<GAME>.py` — smoke tests

---

## Step 4 — Download expert replays

```bash
cd /path/to/repo/rl_coding_game
conda run -n <CONDA_ENV> python Core/cli/download_games.py \
    --game <GAME> \
    --puzzle-id <PUZZLE_ID> \
    --top 10 \
    --per-player 5
```

Requires `CG_SESSION` set in `rl_coding_game/.env`.
Replays are saved to `rl_coding_game/data/games/<GAME>/replays/`.

---

## Step 5 — Implement the game engine (manual step)

The user must implement the game logic. Guide them to fill in:

Non-negotiable architecture rules:
- The game engine must match the CodingGame protocol exactly for input and output semantics.
- Do not put ML features, engineered channels, normalization, or symmetry transforms inside the engine.
- Observation feature engineering belongs in an algorithm-specific feature builder.
- Legal-action mask construction belongs in an algorithm-independent action-mask builder.
- Action decoding/formatting to protocol commands belongs in an action mapper/runtime adapter.

### 4a. Core game engine
File: `rl_coding_game/Games/<GAME>/engine/game.py`

Key methods to implement:
- `reset()` — set up initial board/state
- `step(actions)` — apply both players' actions, advance turn, return `(done, [r0, r1])`
- `get_observation(player_idx)` — return raw protocol-faithful state only (no agent feature engineering)
- `init_from_replay(global_data)` — initialise from replay global data

Reference: `games/cellularena/game/game.py`

### 4b. Replay loader
File: `rl_coding_game/Games/<GAME>/engine/replay_loader.py`

- `load_replay(path)` — parse CodingGame JSON frames into `Replay` → `[ReplayTurn]`
- Each `ReplayTurn` has `commands: List[List[str]]` (stdout per player)

Reference: `games/cellularena/game/replay_loader.py`

### 4c. Symmetry contract

Keep the engine's raw coordinates protocol-faithful. Apply the transform from
`Games/<GAME>/symmetry.md` only in map generation, replay/self-play adapters,
and algorithm-specific observation builders where a player-relative view is
required. Add a regression test with an asymmetric marker to verify both the
spatial axis and direction remapping; comparing two identically transformed
player observations is not sufficient.

---

## Step 6 — Implement observation and action spaces

File: `rl_coding_game/Games/<GAME>/engine/env.py`

Key methods to implement:
- `observation_space(agent)` — define obs space (Dict, Box, etc.)
- `action_space(agent)` — define action space (MultiDiscrete, Discrete)
- `_observe(player_idx)` — encode raw game state into numpy arrays

**Design guidance:**
- Prefer `spaces.Dict` with a `"grid"` Box for spatial games and a `"storage"` Box for scalar state
- Normalize float features to [0, 1]
- Make the observation symmetric using the transform in `symmetry.md`:
    player_0 perspective = same encoding as player_1 perspective after the
    documented spatial and direction transform and player-index swap.
- Reference: `games/cellularena/env.py`

---

## Step 6b — Create algorithm-specific observation feature builders

Create one feature-builder class for every supported algorithm:

- `rl_coding_game/Games/<GAME>/ray/dqn/feature_builder.py`
- `rl_coding_game/Games/<GAME>/ray/sac/feature_builder.py`

For now, only discrete action spaces are supported. Do not scaffold or onboard
games whose action space is continuous.

Each class must initially be a no-op placeholder with the correct interface:

```python
class DQNFeatureBuilder:
    def build(self, raw_observation):
        """Return the raw observation unchanged until customized."""
        return raw_observation
```

The SAC class should use the same interface. Do not add feature engineering to
the scaffold implementation. The classes are extension points for:

- Per-channel normalization or clipping
- Spatial encoding / feature selection before the network
- A different flat shape than the default flatten

The agent must always run through the selected algorithm's feature builder in both:
- Learning (training rollouts and updates)
- Inference (runtime/CodingGame loop), once the inference runner is implemented

When a builder changes the raw observation shape, it must also expose a matching
Gymnasium `observation_space` so the wrapper and RLlib use the transformed shape.

## Step 6c — Create and wire the SAC network customization hook

When SAC is supported, keep the generated no-op class wired into the SAC
configuration and training entry point. The class must preserve RLlib's
current default RLModule when unchanged. Custom encoders and heads belong in a
`Catalog` subclass; do not use `SACTorchModel`, `ModelCatalog`, `custom_model`,
or deprecated policy/Q model configuration dictionaries.

File: `rl_coding_game/Games/<GAME>/ray/sac/modules.py`

```python
from ray.rllib.algorithms.sac import SACConfig


class <Game>SACNetwork:
    """Customize RLlib's current SAC RLModule/catalog here."""

    def customize(self, config: SACConfig) -> SACConfig:
        # Install a custom RLModuleSpec(catalog_class=...) here when needed.
        return config
```

The SAC config must accept a `network_factory`, call
`network_factory().customize(config)`, and return the customized config. The
SAC training entry point must pass the generated `<Game>SACNetwork` factory to
`build_config`. `policy_model_config` configures the actor; `q_model_config`
configures both critics. Run the SAC one-iteration smoke test after changing
the network.

## Step 6d — Create and wire the DQN network customization hook

When Rainbow DQN is supported, keep the generated no-op class wired into the
DQN configuration and training entry point:

File: `rl_coding_game/Games/<GAME>/ray/dqn/modules.py`

```python
from ray.rllib.algorithms.dqn import DQNConfig


class <Game>DQNNetwork:
    def customize(self, config: DQNConfig) -> DQNConfig:
        # Uncomment this block to configure the shared DQN encoder and head.
        # return config.training(
        #     model={
        #         "fcnet_hiddens": [512, 256],
        #         "fcnet_activation": "relu",
        #         "post_fcnet_hiddens": [256],
        #     },
        # )
        return config
```

The DQN config must accept a `network_factory`, call
`network_factory().customize(config)`, and return the customized config. The
DQN training entry point must pass the generated `<Game>DQNNetwork` factory to
`build_config`. The `model` mapping configures the shared encoder and output
head. Run the DQN one-iteration smoke test after changing the network.

## Step 6e — Create the action-mask builder

Create an algorithm-independent placeholder:

File: `rl_coding_game/Games/<GAME>/policy/action_mask.py`

```python
import numpy as np


class ActionMaskBuilder:
    def build(self, game, player_idx, action_count):
        """Return an all-valid mask until customized for the game."""
        return np.ones(action_count, dtype=np.float32)
```

The scaffold must not invent game-specific legality rules. The placeholder
class only establishes where the implementation belongs. Once implemented,
the same mask builder must be explicitly wired into:

- The PettingZoo/RLlib wrapper during training
- The CodingGame inference runner, if one is implemented

For discrete games, the mask length must equal `action_space.n`, and the policy
must apply it to action logits before categorical sampling.

## Step 6f — Add action mapper (required)

File: `rl_coding_game/Games/<GAME>/bots/action_mapper.py`

Implement action conversion from agent output to protocol commands:
- Input: model action tensor/array
- Output: exact protocol commands (`GROW ...`, `SPORE ...`, `WAIT`)

Reference: `Games/cellularena/bots/action_mapper.py` (when available)

The scaffold creates the mapper stub, but does not create a complete inference
runner or automatically connect it to `export_to_codingame.py`. Wire those
pieces together when deploying a trained agent.

---

## Step 7 — Implement offline replay adapter (optional but recommended)

File: `rl_coding_game/Games/<GAME>/engine/offline_replay_adapter.py`

Key method to implement:
- `iter_transitions(replay_path)` — yield `Transition` objects from a replay file
- `_encode_action(commands)` — convert stdout command strings to action integers

This enables offline pretraining from expert replays before self-play.

Reference: `Games/cellularena/engine/offline_replay_adapter.py`

---

## Step 8 — Validate the game engine

```bash
conda run -n <CONDA_ENV> python rl_coding_game/Games/<GAME>/engine/tools/validate_engine.py \
    --game <GAME>
```

> If `validate_engine.py` doesn't support your game yet, run the smoke tests:

```bash
conda run -n <CONDA_ENV> python rl_coding_game/test_<GAME>.py
```

Expected output: all tests pass.

---

## Step 9 — (Optional) Offline pretraining

Offline pretraining is deferred during the Ray migration. The supported first
run is online Ray RLlib self-play.

---

## Step 10 — Run first self-play experiment

```bash
conda run -n <CONDA_ENV> python -m Games.<GAME>.ray.dqn.train \
    --iterations 1 \
    --num-env-runners 0 \
    --checkpoint-dir Games/<GAME>/experiments/exp_001_baseline
```

Increase `--iterations` and `--num-env-runners` after the smoke run passes.

Use the `run-experiment` skill for the full local Ray training workflow.

---

## Tips

- Keep `MAX_TURNS` in `game.py` slightly larger than the actual game limit to avoid off-by-one issues
- Use sparse rewards (+1/-1 at terminal) — dense rewards can slow learning
- Add action masking if the game has legal-move constraints (see `env_runner.py` for masking hooks)
- Keep engine and model concerns separate:
    - Engine: protocol-faithful game simulation only
    - Obs mapper: game obs -> agent obs
    - Action mapper: agent action -> protocol command strings
