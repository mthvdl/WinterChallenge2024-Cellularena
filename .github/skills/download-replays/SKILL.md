---
name: download-replays
description: "Use when the user wants to download CodingGame replays for any game — from the leaderboard, a specific game ID, or the live TV broadcast. Works for any puzzle, not just cellularena."
---

# Download Replays

Download top-player game replays from CodingGame for any puzzle.

---

## Step 0 — Gather inputs interactively

Ask the user **only** what you don't already know:

> What is the CodingGame URL (or puzzle slug) for the game?
> (e.g. `https://www.codingame.com/contests/fall-challenge-2024`)

Derive automatically:
- **Puzzle slug** = last path segment of URL
- **Game name** = slug with `-` → `_`

If the user already provided a URL in their message, use it directly.

---

## Prerequisites

Set your CodingGame session cookie in `rl_coding_game/.env`:

```
CG_SESSION=<paste your cgSession cookie value here>
```

To get the cookie:
1. Log in at https://www.codingame.com in your browser
2. Open DevTools (F12) → Application → Cookies → `https://www.codingame.com`
3. Copy the value of the `cgSession` cookie

---

## Step 0 — Identify the puzzle slug

From a CodingGame URL like `https://www.codingame.com/contests/fall-challenge-2024`,
the puzzle slug is the last path segment: `fall-challenge-2024`.

---

## Download replays

### From the top-N leaderboard

```bash
cd /path/to/repo
conda run -n cellularena python rl_coding_game/download_games.py \
    --game <GAME> \
    --puzzle-id <PUZZLE_ID> \
    --top 10 \
    --per-player 5
```

### Single game by ID

```bash
conda run -n cellularena python rl_coding_game/download_games.py \
    --game <GAME> \
    --puzzle-id <PUZZLE_ID> \
    --game-id <GAME_ID>
```

### Without auth (TV broadcast game only)

```bash
conda run -n cellularena python rl_coding_game/download_games.py \
    --game <GAME> \
    --puzzle-id <PUZZLE_ID>
```

---

## Output

Replays are saved to `rl_coding_game/data/games/<GAME>/replays/`:
- `core_<ID>.json` — structured replay used by the offline adapter
- `codingame_<ID>.json` — raw CodingGame JSON (kept for validation)

---

## For cellularena (default)

```bash
conda run -n cellularena python rl_coding_game/download_games.py \
    --top 5 --per-player 3
```

No need to specify `--game` or `--puzzle-id` for cellularena.

---

## Verify downloads

```bash
ls rl_coding_game/data/games/<GAME>/replays/
```

Expected: `core_*.json` files, one per downloaded game.
