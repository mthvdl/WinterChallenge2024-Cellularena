"""
Export self-play episodes into core-raw replay files.

Viewer display data is generated externally via replay_transform.add_display_data,
so the core game remains the single source of truth at runtime.

Usage
-----
    cd rl_coding_game
    python export_episode_replay.py --seed 0 --policy greedy
    python export_episode_replay.py --seed 123 --policy random --viewer-output replays/train_123.viewer.json
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from Games.cellularena.engine.coord import Coord, Direction
from Games.cellularena.engine.game import Game, MAX_TURNS
from Games.cellularena.engine.grid import Protein
from Games.cellularena.engine.organ import Organ, OrganType
from Games.cellularena.engine.tools.replay_transform import add_display_data

REPLAY_DIR = Path(__file__).resolve().parents[2] / "experiments" / "shared" / "replays"

EV_GROW = 0
EV_SPORE = 1
EV_ATTACK = 2
EV_DEATH = 3
EV_HARVEST = 5
EV_ABSORB = 6
EV_CRASH = 7
EV_SPAWN_ROOT = 8

_DIRS = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
_DIR_CHARS = ["N", "E", "S", "W"]
_GROW_TYPES = [OrganType.BASIC, OrganType.TENTACLE, OrganType.HARVESTER, OrganType.SPORER]


@dataclass(frozen=True)
class OrganState:
    organ_id: int
    owner_idx: int
    organ_type: str
    direction: str
    pos: Coord
    parent_id: int


@dataclass(frozen=True)
class GameState:
    organs: Dict[int, OrganState]
    obstacle_coords: Set[Coord]
    storage: Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]


def _snapshot_state(game: Game) -> GameState:
    organs: Dict[int, OrganState] = {}
    for organ in game.organ_by_id.values():
        parent_id = organ.parent.id if organ.parent is not None else 0
        organs[organ.id] = OrganState(
            organ_id=organ.id,
            owner_idx=organ.owner_idx,
            organ_type=organ.type.name,
            direction=organ.direction.name[0],
            pos=organ.pos,
            parent_id=parent_id,
        )

    obstacle_coords: Set[Coord] = set()
    for coord, tile in game.grid.cells.items():
        if tile.obstacle:
            obstacle_coords.add(coord)

    storage = (
        tuple(game.players[0].storage[p] for p in Protein),
        tuple(game.players[1].storage[p] for p in Protein),
    )
    return GameState(organs=organs, obstacle_coords=obstacle_coords, storage=storage)


def _serialize_global_data(game: Game) -> str:
    lines: List[str] = []
    lines.append(f"{game.grid.width} {game.grid.height}")

    for y in range(game.grid.height):
        for x in range(game.grid.width):
            tile = game.grid.get(Coord(x, y))
            if tile.obstacle:
                lines.append("1 X")
            elif tile.protein is not None:
                lines.append(f"0 {tile.protein.name}")
            else:
                lines.append("0 X")

    for player in game.players:
        lines.append(str(len(player.organs)))
        for organ in player.organs:
            parent_id = organ.parent.id if organ.parent else 0
            lines.append(
                f"{organ.id} {organ.pos.x} {organ.pos.y} {organ.type.name} "
                f"{organ.direction.name[0]} {parent_id}"
            )

    return "\n".join(lines)


def _coord_list_text(coords: Sequence[Coord]) -> str:
    return "_".join(f"{c.x} {c.y}" for c in coords)


def _serialize_frame_data(game: Game, events: List[Dict]) -> str:
    lines: List[str] = []
    for player_idx in range(2):
        storage = " ".join(str(game.players[player_idx].storage[p]) for p in Protein)
        lines.append(storage)
        lines.append("0")

    lines.append(str(len(events)))
    for ev in events:
        lines.append(str(ev["type"]))
        lines.append(str(ev.get("start", 0)))
        lines.append(str(ev.get("end", 1000)))
        lines.append(str(ev.get("player_idx", 0)))
        lines.append(str(ev.get("id", 0)))
        lines.append(ev.get("organ_type", ""))
        lines.append(ev.get("direction", ""))
        lines.append(_coord_list_text(ev.get("coords", [])))

    return "\n".join(lines)


def _build_events(before: GameState, after: GameState) -> List[Dict]:
    events: List[Dict] = []

    before_ids = set(before.organs.keys())
    after_ids = set(after.organs.keys())

    removed = sorted(before_ids - after_ids)
    added = sorted(after_ids - before_ids)
    new_obstacles = sorted(after.obstacle_coords - before.obstacle_coords, key=lambda c: (c.y, c.x))

    for organ_id in removed:
        lost = before.organs[organ_id]
        events.append(
            {
                "type": EV_DEATH,
                "start": 0,
                "end": 1000,
                "player_idx": lost.owner_idx,
                "id": lost.organ_id,
                "organ_type": lost.organ_type,
                "direction": lost.direction,
                "coords": [lost.pos],
            }
        )

    for coord in new_obstacles:
        events.append(
            {
                "type": EV_CRASH,
                "start": 0,
                "end": 1000,
                "player_idx": 0,
                "id": 0,
                "organ_type": "",
                "direction": "",
                "coords": [coord],
            }
        )

    for organ_id in added:
        created = after.organs[organ_id]

        if created.organ_type == "ROOT" and created.parent_id == 0:
            events.append(
                {
                    "type": EV_SPAWN_ROOT,
                    "start": 0,
                    "end": 1000,
                    "player_idx": created.owner_idx,
                    "id": created.organ_id,
                    "organ_type": "ROOT",
                    "direction": created.direction,
                    "coords": [created.pos],
                }
            )
            continue

        parent = after.organs.get(created.parent_id) or before.organs.get(created.parent_id)
        if parent is None:
            continue

        events.append(
            {
                "type": EV_GROW,
                "start": 0,
                "end": 1000,
                "player_idx": created.owner_idx,
                "id": created.organ_id,
                "organ_type": created.organ_type,
                "direction": created.direction,
                "coords": [parent.pos, created.pos],
            }
        )

    return events


def _wait_policy(game: Game, player_idx: int, rng: random.Random) -> List[str]:
    root_count = len(game.players[player_idx].roots)
    return ["WAIT"] * max(root_count, 1)


def _greedy_policy(game: Game, player_idx: int, rng: random.Random) -> List[str]:
    player = game.players[player_idx]
    foe_idx = 1 - player_idx
    cmds: List[str] = []

    for root in player.roots:
        root_id = game._get_root_id(root)
        organs = game._organism_organs(root_id, player_idx)

        chosen: Optional[str] = None
        for organ in organs:
            for direction, dir_char in zip(_DIRS, _DIR_CHARS):
                target = organ.pos.add(direction.coord)
                tile = game.grid.get(target)
                if tile is None or tile.obstacle or tile.has_organ():
                    continue

                if tile.has_protein() and player.can_afford(OrganType.BASIC):
                    cmd = f"GROW {organ.id} {target.x} {target.y} BASIC {dir_char}"
                    if game.parse_raw_command(cmd, player_idx) is not None:
                        chosen = cmd
                        break

                if chosen is None:
                    blocked = any(
                        game.grid.get(n) is not None
                        and game.grid.get(n).has_tentacle_targeting(foe_idx, target)
                        for n in game.grid.get_neighbours(target)
                    )
                    if not blocked and player.can_afford(OrganType.BASIC):
                        cmd = f"GROW {organ.id} {target.x} {target.y} BASIC {dir_char}"
                        if game.parse_raw_command(cmd, player_idx) is not None:
                            chosen = cmd
            if chosen is not None:
                break

        cmds.append(chosen or "WAIT")

    return cmds if cmds else ["WAIT"]


def _random_policy(game: Game, player_idx: int, rng: random.Random) -> List[str]:
    player = game.players[player_idx]
    cmds: List[str] = []

    for root in player.roots:
        root_id = game._get_root_id(root)
        organism_organs = game._organism_organs(root_id, player_idx)
        candidates = ["WAIT"]

        for organ in organism_organs:
            for direction, dir_char in zip(_DIRS, _DIR_CHARS):
                target = organ.pos.add(direction.coord)
                tile = game.grid.get(target)
                if tile is None or tile.obstacle or tile.has_organ():
                    continue

                for organ_type in _GROW_TYPES:
                    cmd = f"GROW {organ.id} {target.x} {target.y} {organ_type.name} {dir_char}"
                    if game.parse_raw_command(cmd, player_idx) is not None:
                        candidates.append(cmd)

        sporer_organs = [o for o in organism_organs if o.is_sporer()]
        for sporer in sporer_organs:
            target = game._spore_target(sporer)
            if target is None:
                continue
            cmd = f"SPORE {sporer.id} {target.x} {target.y}"
            if game.parse_raw_command(cmd, player_idx) is not None:
                candidates.append(cmd)

        cmds.append(rng.choice(candidates))

    return cmds if cmds else ["WAIT"]


def _policy_factory(name: str):
    key = name.lower().strip()
    if key == "wait":
        return _wait_policy
    if key == "random":
        return _random_policy
    if key == "greedy":
        return _greedy_policy
    raise ValueError(f"Unknown policy: {name}")


def export_episode_core_raw(seed: int, policy_name: str, max_turns: int) -> Dict:
    game = Game(seed=seed)
    game.reset()
    initial_global_data = _serialize_global_data(game)

    rng = random.Random(seed)
    policy = _policy_factory(policy_name)

    initial_storage = [
        [game.players[0].storage[p] for p in Protein],
        [game.players[1].storage[p] for p in Protein],
    ]
    turns: List[Dict] = []

    for turn in range(1, max_turns + 1):
        commands = {
            0: policy(game, 0, rng),
            1: policy(game, 1, rng),
        }
        done, _ = game.step_replay(commands)
        turns.append(
            {
                "turn": turn,
                "commands": [commands[0], commands[1]],
            }
        )

        if done:
            break

    agents = [
        {"index": 0, "userId": 2000, "name": f"{policy_name}_P0"},
        {"index": 1, "userId": 2001, "name": f"{policy_name}_P1"},
    ]
    return {
        "format": "cellularena-core-raw-v1",
        "source": "selfplay",
        "gameId": f"selfplay_{policy_name}_{seed}",
        "agents": agents,
        "globalData": initial_global_data,
        "initialStorage": initial_storage,
        "turns": turns,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export one self-play episode as core-raw replay")
    parser.add_argument("--seed", type=int, default=0, help="Deterministic seed")
    parser.add_argument(
        "--policy",
        choices=["wait", "greedy", "random"],
        default="greedy",
        help="Per-player command policy",
    )
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS)
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output core-raw replay path (default: replays/selfplay_<policy>_<seed>.json)",
    )
    parser.add_argument(
        "--viewer-output",
        type=str,
        default="",
        help="Optional viewer replay output path generated from core replay",
    )
    args = parser.parse_args()

    REPLAY_DIR.mkdir(exist_ok=True)

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = REPLAY_DIR / f"selfplay_{args.policy}_{args.seed}.json"

    replay = export_episode_core_raw(seed=args.seed, policy_name=args.policy, max_turns=args.max_turns)
    out_path.write_text(json.dumps(replay, indent=2), encoding="utf-8")
    print(f"Exported core replay ({len(replay['turns'])} turns) to {out_path}")

    if args.viewer_output:
        viewer_path = Path(args.viewer_output)
        viewer_path.parent.mkdir(parents=True, exist_ok=True)
        viewer_replay = add_display_data(replay)
        viewer_path.write_text(json.dumps(viewer_replay, indent=2), encoding="utf-8")
        print(f"Generated viewer replay to {viewer_path}")


if __name__ == "__main__":
    main()
