---
name: validate-game
description: "Use when the user wants to validate that their PettingZoo game engine correctly reproduces CodingGame replay outcomes — comparing stored states after each turn against the reference replay."
---

# Validate Game Engine

Validate that the game engine produces the same state as the CodingGame referee,
by replaying downloaded games turn by turn and comparing outputs.

---

## Step 0 — Gather inputs interactively

Ask the user **only** what you don't already know:

> Which game do you want to validate? (provide the game name or URL)

If the game name is already clear from context, skip this question.
Derive game name from URL by taking the last path segment and replacing `-` with `_`.

Then check what exists:

```bash
ls rl_coding_game/games/
ls rl_coding_game/data/games/<GAME>/replays/core_*.json 2>/dev/null | wc -l
```

---

## Step 1 — Check prerequisites

```bash
# Replays must exist
ls rl_coding_game/data/games/<GAME>/replays/core_*.json | head -5

# Game module must exist
ls rl_coding_game/games/<GAME>/game/game.py

# Rules markdown must exist (implementation source of truth)
ls rl_coding_game/games/<GAME>/rules.md
```

Read `rl_coding_game/games/<GAME>/rules.md` before validating and verify these are reflected in `game.py` behavior:
- Endgame rules and victory/defeat conditions
- Order of actions / turn resolution order
- Constraints (turn limits, map limits, legal action constraints)

---

## Step 1 — Run smoke tests first

These test that the env/spaces compile correctly (they don't need replays):

```bash
conda run -n cellularena python rl_coding_game/test_<GAME>.py
```

Fix any import errors or NotImplementedError before proceeding.

---

## Step 2 — Run engine validation

### For cellularena (full validation script)

```bash
cd rl_coding_game
conda run -n cellularena python validate_engine.py
```

Or against a specific replay:

```bash
conda run -n cellularena python validate_engine.py \
    replays/codingame_884960630.json
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

## Step 3 — Interpret results

**All turns match:** Engine is correct. Proceed to training.

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

## Step 4 — Iterate

Replay validation is the fastest feedback loop for engine bugs. Common workflow:

```bash
while true; do
    conda run -n cellularena python validate_engine.py --loop  # --loop re-runs after fixes
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
