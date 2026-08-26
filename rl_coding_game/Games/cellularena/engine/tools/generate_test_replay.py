"""
generate_test_replay.py – Generate synthetic CodingGame-format replays
using deterministic bot players.

These replays let the validator run without real downloaded games.

Usage
-----
    cd rl_coding_game
    python generate_test_replay.py          # generate 5 test replays
    python generate_test_replay.py --count 10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from Games.cellularena.engine.game import (
    Game, PlayerState, GrowthCommand, MAX_TURNS, PROTEIN_PER_ABSORB
)
from Games.cellularena.engine.coord import Coord, Direction, ADJACENCY
from Games.cellularena.engine.grid import Protein, Grid, Tile
from Games.cellularena.engine.organ import Organ, OrganType

REPLAY_DIR = Path(__file__).resolve().parents[2] / "experiments" / "shared" / "replays"

# ──────────────────────────────────────────────────────────────────────────────
# Deterministic bots
# ──────────────────────────────────────────────────────────────────────────────

_DIR_NAMES = [d.name[0] for d in [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]]


def greedy_commands(game: Game, player_idx: int) -> List[str]:
    """
    Simple greedy bot: for each organism, grow BASIC toward nearest protein;
    grow TENTACLE if adjacent to an enemy; WAIT otherwise.
    """
    player = game.players[player_idx]
    foe_idx = 1 - player_idx
    cmds: List[str] = []

    for root_organ in player.roots:
        root_id = game._get_root_id(root_organ)
        organs  = game._organism_organs(root_id, player_idx)

        best_cmd: Optional[str] = None

        # Try each organ, find a good growth target
        for organ in organs:
            for di, direction in enumerate([Direction.NORTH, Direction.EAST,
                                             Direction.SOUTH, Direction.WEST]):
                target = organ.pos.add(direction.coord)
                tile   = game.grid.get(target)
                if tile is None or tile.obstacle:
                    continue

                # Attack: grow TENTACLE toward enemy organ
                if (tile.has_organ() and tile.organ.owner_idx == foe_idx
                        and player.can_afford(OrganType.TENTACLE)):
                    # target must actually be FREE to grow into (enemy is there = attack)
                    # We grow the tentacle one cell BEFORE the enemy
                    # Try to find a cell adjacent to the enemy
                    pass

                if tile.has_organ():
                    continue

                # Grow toward protein → BASIC
                if tile.has_protein() and player.can_afford(OrganType.BASIC):
                    dir_letter = _DIR_NAMES[di]
                    best_cmd = (
                        f"GROW {organ.id} {target.x} {target.y} BASIC {dir_letter}"
                    )
                    break

                # Grow into free space → BASIC
                if not tile.obstacle and player.can_afford(OrganType.BASIC):
                    if best_cmd is None:
                        # Validate not in front of enemy tentacle
                        blocked = any(
                            game.grid.get(n) is not None
                            and game.grid.get(n).has_tentacle_targeting(foe_idx, target)
                            for n in game.grid.get_neighbours(target)
                        )
                        if not blocked:
                            dir_letter = _DIR_NAMES[di]
                            best_cmd = (
                                f"GROW {organ.id} {target.x} {target.y} BASIC {dir_letter}"
                            )

            if best_cmd and "protein" in best_cmd:
                break  # prefer protein growth

        cmds.append(best_cmd or "WAIT")

    return cmds if cmds else ["WAIT"]


# ──────────────────────────────────────────────────────────────────────────────
# Serialisers (mirror Java Serializer)
# ──────────────────────────────────────────────────────────────────────────────

def serialize_global_data(game: Game) -> str:
    lines: List[str] = []
    lines.append(f"{game.grid.width} {game.grid.height}")

    for y in range(game.grid.height):
        for x in range(game.grid.width):
            tile = game.grid.get(Coord(x, y))
            if tile.obstacle:
                lines.append(f"1 X")
            elif tile.protein is not None:
                lines.append(f"0 {tile.protein.name}")
            else:
                lines.append(f"0 X")

    for player in game.players:
        lines.append(str(len(player.organs)))
        for o in player.organs:
            pid = o.parent.id if o.parent else 0
            lines.append(
                f"{o.id} {o.pos.x} {o.pos.y} {o.type.name} "
                f"{o.direction.name[0]} {pid}"
            )

    return "\n".join(lines)


def serialize_frame_data(game: Game) -> str:
    """Serialise per-turn frame data (storage + minimal events)."""
    lines: List[str] = []
    for player in game.players:
        storage = " ".join(str(player.storage[p]) for p in Protein)
        lines.append(storage)
        lines.append("0")   # no messages

    lines.append("0")   # no events (simplified)
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Replay builder
# ──────────────────────────────────────────────────────────────────────────────

def build_replay(seed: int) -> Dict:
    game = Game(seed=seed)
    game.reset()

    frames = []

    # Frame 0: global data (initial state)
    frames.append({
        "key":      "0",
        "data":     serialize_global_data(game),
        "gameInfo": [],
        "summary":  None,
    })

    for turn in range(1, MAX_TURNS + 1):
        # Collect commands before stepping
        cmds: Dict[int, List[str]] = {}
        for p_idx in range(2):
            cmds[p_idx] = greedy_commands(game, p_idx)

        # Flatten for stdout storage
        stdout = ["\n".join(c) for c in cmds.values()]

        done, _ = game.step_replay(cmds)

        frame_data = serialize_frame_data(game)

        frames.append({
            "key":     str(turn),
            "data":    frame_data,
            "stdout":  stdout,
            "stderr":  ["", ""],
            "gameInfo": [],
            "summary": f"Turn {turn} | P0:{game.players[0].organ_count} P1:{game.players[1].organ_count}",
        })

        if done:
            break

    agents = [
        {"index": 0, "userId": 1000, "name": "GreedyBot_P0"},
        {"index": 1, "userId": 1001, "name": "GreedyBot_P1"},
    ]

    return {"agents": agents, "frames": frames}


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic Cellularena replays")
    parser.add_argument("--count", type=int, default=5, help="Number of replays to generate")
    parser.add_argument("--seed-offset", type=int, default=0)
    args = parser.parse_args()

    REPLAY_DIR.mkdir(exist_ok=True)

    for i in range(args.count):
        seed    = args.seed_offset + i
        game_id = 900000000 + seed   # synthetic ID space
        path    = REPLAY_DIR / f"synthetic_{game_id}.json"

        if path.exists():
            print(f"  [{game_id}] already exists, skipping")
            continue

        replay = build_replay(seed)
        path.write_text(json.dumps(replay, indent=2), encoding="utf-8")
        turns = len(replay["frames"]) - 1
        print(f"  [{game_id}] generated {turns} turns → {path.name}")

    print(f"\nDone. {args.count} replay(s) in {REPLAY_DIR}")


if __name__ == "__main__":
    main()
