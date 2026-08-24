---
name: new-game
description: "Use when the user wants to add a new CodingGame to the rl_coding_game framework — from a game URL, create the scaffold, download replays, implement the engine, and run the first training experiment."
---

# New Game Onboarding

Use this skill to onboard a new CodingGame into the rl_coding_game framework end-to-end.

---

## Step 0 — Gather inputs interactively

Ask the user **only** what you don't already know. The only required input is the game URL.

**Ask:**
> What is the CodingGame URL for the game you want to train on?
> (e.g. `https://www.codingame.com/contests/fall-challenge-2024`)

Then derive everything else automatically:
- **Puzzle slug** = last path segment of the URL (e.g. `fall-challenge-2024`)
- **Game name** = puzzle slug with `-` replaced by `_` (e.g. `fall_challenge_2024`)

If the user already provided a URL in their message, use it directly — do not ask again.

**Only ask if the user wants to override defaults:**
- Local game name (default: derived from URL)
- Algorithm: Rainbow DQN (default) or PPO?

---

## Step 1 — Scaffold the game

```bash
cd /path/to/repo
conda run -n cellularena python rl_coding_game/scaffold_game.py \
    --puzzle-id <PUZZLE_ID> \
    --game <GAME>
```

This creates:
- `rl_coding_game/games/<GAME>/` — env, factories, offline adapter, game engine stubs
- `rl_coding_game/data/games/<GAME>/replays/` — empty replay store
- `rl_coding_game/test_<GAME>.py` — smoke tests

---

## Step 2 — Download game rules

```bash
conda run -n cellularena python rl_coding_game/download_rules.py \
    --puzzle-id <PUZZLE_ID> \
    --game <GAME>
```

Rules are saved to `rl_coding_game/data/games/<GAME>/rules.txt` (plain text) and `.html`.

> If the API fails, open the game page in a browser and copy the rules manually.

---

## Step 3 — Download expert replays

```bash
conda run -n cellularena python rl_coding_game/download_games.py \
    --game <GAME> \
    --puzzle-id <PUZZLE_ID> \
    --top 10 \
    --per-player 5
```

Requires `CG_SESSION` set in `rl_coding_game/.env`.
Replays are saved to `rl_coding_game/data/games/<GAME>/replays/`.

---

## Step 4 — Implement the game engine (manual step)

The user must implement the game logic. Guide them to fill in:

### 4a. Core game engine
File: `rl_coding_game/games/<GAME>/game/game.py`

Key methods to implement:
- `reset()` — set up initial board/state
- `step(actions)` — apply both players' actions, advance turn, return `(done, [r0, r1])`
- `get_observation(player_idx)` — return raw state for building observations
- `init_from_replay(global_data)` — initialise from replay global data

Reference: `games/cellularena/game/game.py`

### 4b. Replay loader
File: `rl_coding_game/games/<GAME>/game/replay_loader.py`

- `load_replay(path)` — parse CodingGame JSON frames into `Replay` → `[ReplayTurn]`
- Each `ReplayTurn` has `commands: List[List[str]]` (stdout per player)

Reference: `games/cellularena/game/replay_loader.py`

---

## Step 5 — Implement observation and action spaces

File: `rl_coding_game/games/<GAME>/env.py`

Key methods to implement:
- `observation_space(agent)` — define obs space (Dict, Box, etc.)
- `action_space(agent)` — define action space (MultiDiscrete, Discrete)
- `_observe(player_idx)` — encode raw game state into numpy arrays

**Design guidance:**
- Prefer `spaces.Dict` with a `"grid"` Box for spatial games and a `"storage"` Box for scalar state
- Normalize float features to [0, 1]
- Make the observation symmetric: player_0 perspective = same encoding as player_1 perspective (swap player indices)
- Reference: `games/cellularena/env.py`

---

## Step 6 — Implement offline replay adapter (optional but recommended)

File: `rl_coding_game/games/<GAME>/offline_replay_adapter.py`

Key method to implement:
- `iter_transitions(replay_path)` — yield `Transition` objects from a replay file
- `_encode_action(commands)` — convert stdout command strings to action integers

This enables offline pretraining from expert replays before self-play.

Reference: `games/cellularena/offline_replay_adapter.py`

---

## Step 7 — Validate the game engine

```bash
conda run -n cellularena python rl_coding_game/validate_engine.py \
    --game <GAME>
```

> If `validate_engine.py` doesn't support your game yet, run the smoke tests:

```bash
conda run -n cellularena python rl_coding_game/test_<GAME>.py
```

Expected output: all tests pass.

---

## Step 8 — (Optional) Offline pretraining

Use the `offline-training` skill to pretrain from expert replays before self-play.

---

## Step 9 — Run first self-play experiment

```bash
conda run -n cellularena python rl_coding_game/train_rainbow.py \
    --env-factory games.<GAME>.factories:make_env \
    --game <GAME> \
    --experiment-name exp_001_baseline \
    --total-steps 500000 \
    --n-envs 4 \
    --self-play \
    --reset-replay
```

Artifacts: `rl_coding_game/experiments/<GAME>/exp_001_baseline/`

Use the `run-experiment` skill for full local/remote training workflows.

---

## Tips

- Keep `MAX_TURNS` in `game.py` slightly larger than the actual game limit to avoid off-by-one issues
- Use sparse rewards (+1/-1 at terminal) — dense rewards can slow learning
- Add action masking if the game has legal-move constraints (see `env_runner.py` for masking hooks)
- For PPO instead of Rainbow DQN, use `--trainer rl.ppo.trainer:PPOTrainer` in train_rainbow.py
