---
name: validate-game
description: "Use when the user wants to validate that their PettingZoo game engine exactly reproduces CodingGame games turn by turn, including complete next observations, terminal turn count, and winner/loser/tie outcome."
---

# Validate Game Engine

Validate that the game engine produces the same next observation and terminal
result as the CodingGame referee by replaying downloaded top-player games with
the exact same player commands.

---

## Step 0 — Gather inputs interactively

Ask the user **only** what you don't already know:

> Which game do you want to validate? (provide the game name or URL)

If the game name is already clear from context, skip this question.
Derive game name from URL by taking the last path segment and replacing `-` with `_`.

Then check what exists. Exact validation requires raw `codingame_*.json` files;
`core_*.json` stores commands but not authoritative per-turn frame states.

```bash
ls rl_coding_game/games/
ls rl_coding_game/Games/<GAME>/experiments/shared/replays/codingame_*.json 2>/dev/null | wc -l
```

---

## Step 1 — Download top-player games

For cellularena, retain every raw replay selected for validation. `-1` disables
sample pruning and backfills raw data when a core replay already exists:

```bash
cd rl_coding_game
conda run -n cellularena env PYTHONPATH=. python -m Core.cli.download_games \
    --top 5 --per-player 3 --keep-samples -1
```

Never validate `core_*.json` for exactness: it lacks CodingGame frame storage,
events, and terminal metadata. Confirm the raw set exists:

```bash
ls Games/cellularena/experiments/shared/replays/codingame_*.json
```

## Step 2 — Check prerequisites

```bash
# Replays must exist
ls rl_coding_game/Games/<GAME>/experiments/shared/replays/codingame_*.json | head -5

# Game module must exist
ls rl_coding_game/Games/<GAME>/engine/game.py

# Rules markdown must exist (implementation source of truth)
ls rl_coding_game/Games/<GAME>/rules.md
```

Read `rl_coding_game/games/<GAME>/rules.md` before validating and verify these are reflected in `game.py` behavior:
- Endgame rules and victory/defeat conditions
- Order of actions / turn resolution order
- Constraints (turn limits, map limits, legal action constraints)

---

## Step 3 — Run smoke tests first

These test that the env/spaces compile correctly (they don't need replays):

```bash
cd rl_coding_game
conda run -n cellularena env PYTHONPATH=. python -m pytest \
    Games/<GAME>/engine/tests -q
```

Fix any import errors or NotImplementedError before proceeding.

---

## Step 4 — Run exact engine validation

### For cellularena (full validation script)

```bash
cd rl_coding_game
conda run -n cellularena env PYTHONPATH=. python \
    -m Games.cellularena.engine.tools.validate_engine
```

Or against a specific replay:

```bash
conda run -n cellularena env PYTHONPATH=. python \
    -m Games.cellularena.engine.tools.validate_engine \
    Games/cellularena/experiments/shared/replays/codingame_884960630.json
```

### For other games (custom validation)

Implement `validate_engine.py` support for your game, or write a custom script:

```python
# Minimal validation pattern
from pathlib import Path
from games.<GAME>.game.game import Game
from games.<GAME>.game.replay_loader import load_replay

replay = load_replay(Path("data/games/<GAME>/replays/core_<ID>.json"))
game = Game()
game.init_from_replay(replay.global_data)

for turn in replay.turns:
    done, rewards = game.step_replay({0: turn.commands[0], 1: turn.commands[1]})
    # TODO: compare game.get_observation(0) against expected state from replay

print("Validation done")
```

Save as `validate_<GAME>.py` in `rl_coding_game/`.

---

For every turn, validation must feed both players' recorded stdout commands and
assert exact equality for:

- Full next observation arrays: grid channels, protein storage, and turn
- Every wall, protein, organ position/type/owner/direction, and storage value
- No termination before the last CodingGame turn
- Engine is terminal on the last CodingGame turn
- Exact total turn count
- Winner, loser, or tie using final organ count then stored-protein tie-break

Any missing raw frame data is a validation error, not a pass or warning.

## Step 5 — Interpret results

**All observations and terminal checks match:** Engine is correct for the tested replay corpus.

**Storage mismatch:** Protein/resource counts differ.
- Check harvesting logic, initial resource parsing, cost deductions
- For cellularena: protein costs are A=1, B=1, C=1, D=1 for BASIC; see organ.py

**Organ mismatch:** Wrong organs placed/removed.
- Check GROW command parsing (direction encoding)
- Check death/collision resolution order
- Verify that the initial board layout is loaded correctly from global_data

**Turn count mismatch:** Game ends too early or too late.
- Check your MAX_TURNS constant
- Verify win/loss conditions

---

## Step 6 — Iterate

Replay validation is the fastest feedback loop for engine bugs. Common workflow:

```bash
while true; do
    conda run -n cellularena env PYTHONPATH=. python \
        -m Games.cellularena.engine.tools.validate_engine --loop
done
```

(cellularena has `--loop` mode; adapt for other games as needed)

---

## When the engine passes validation

Run the offline replay adapter to confirm transitions extract correctly:

```bash
conda run -n cellularena python prefill_replay_buffer.py \
    --adapter games.<GAME>.offline_replay_adapter:create_adapter \
    --game <GAME> \
    --experiment-name smoke_validate \
    --dry-run
```
