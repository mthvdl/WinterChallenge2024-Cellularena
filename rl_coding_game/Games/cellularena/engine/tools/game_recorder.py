"""Record a single episode and export viewer-ready JSON.

Runs one sequential episode between two bots in a fresh CellularenaActionEnv,
snapshots the Game state before and after each step, computes events, and
serialises everything to the viewer JSON format used by viewer_server.py.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from Games.cellularena.engine.coord import Coord
from Games.cellularena.engine.game import Game
from Games.cellularena.engine.grid import Protein

log = logging.getLogger(__name__)

EV_GROW = 0
EV_DEATH = 3
EV_CRASH = 7
EV_SPAWN_ROOT = 8


@dataclass(frozen=True)
class _OrganState:
    organ_id: int
    owner_idx: int
    organ_type: str
    direction: str
    pos: Coord
    parent_id: int


@dataclass(frozen=True)
class _GameSnapshot:
    organs: Dict[int, _OrganState]
    obstacle_coords: frozenset  # frozenset[Coord]


def _snapshot(game: Game) -> _GameSnapshot:
    organs: Dict[int, _OrganState] = {}
    for organ in game.organ_by_id.values():
        parent_id = organ.parent.id if organ.parent is not None else 0
        organs[organ.id] = _OrganState(
            organ_id=organ.id,
            owner_idx=organ.owner_idx,
            organ_type=organ.type.name,
            direction=organ.direction.name[0],
            pos=organ.pos,
            parent_id=parent_id,
        )
    obstacles = frozenset(
        coord for coord, tile in game.grid.cells.items() if tile.obstacle
    )
    return _GameSnapshot(organs=organs, obstacle_coords=obstacles)


def _build_events(before: _GameSnapshot, after: _GameSnapshot) -> List[Dict]:
    events: List[Dict] = []
    before_ids = set(before.organs)
    after_ids = set(after.organs)

    for organ_id in sorted(before_ids - after_ids):
        lost = before.organs[organ_id]
        events.append({"type": EV_DEATH, "start": 0, "end": 1000,
                        "player_idx": lost.owner_idx, "id": lost.organ_id,
                        "organ_type": lost.organ_type, "direction": lost.direction,
                        "coords": [lost.pos]})

    new_obstacles = sorted(after.obstacle_coords - before.obstacle_coords,
                           key=lambda c: (c.y, c.x))
    for coord in new_obstacles:
        events.append({"type": EV_CRASH, "start": 0, "end": 1000,
                        "player_idx": 0, "id": 0, "organ_type": "",
                        "direction": "", "coords": [coord]})

    for organ_id in sorted(after_ids - before_ids):
        created = after.organs[organ_id]
        if created.organ_type == "ROOT" and created.parent_id == 0:
            events.append({"type": EV_SPAWN_ROOT, "start": 0, "end": 1000,
                            "player_idx": created.owner_idx, "id": created.organ_id,
                            "organ_type": "ROOT", "direction": created.direction,
                            "coords": [created.pos]})
            continue
        parent = after.organs.get(created.parent_id) or before.organs.get(created.parent_id)
        if parent is None:
            continue
        events.append({"type": EV_GROW, "start": 0, "end": 1000,
                        "player_idx": created.owner_idx, "id": created.organ_id,
                        "organ_type": created.organ_type, "direction": created.direction,
                        "coords": [parent.pos, created.pos]})
    return events


def _coord_list_text(coords: List[Coord]) -> str:
    return "_".join(f"{c.x} {c.y}" for c in coords)


def _derive_commands(events: List[Dict], before: "_GameSnapshot") -> List[str]:
    """Derive per-player command strings from the turn's events."""
    cmds = ["WAIT", "WAIT"]
    for ev in events:
        pidx = ev["player_idx"]
        if ev["type"] == EV_GROW:
            coords = ev.get("coords", [])
            if len(coords) >= 2:
                parent_pos, target = coords[0], coords[1]
                parent_id = next(
                    (o.organ_id for o in before.organs.values()
                     if o.pos == parent_pos and o.owner_idx == pidx),
                    0,
                )
                cmds[pidx] = (f"GROW {parent_id} {target.x} {target.y}"
                               f" {ev['organ_type']} {ev['direction']}")
        elif ev["type"] == EV_SPAWN_ROOT:
            coords = ev.get("coords", [])
            if coords:
                pos = coords[0]
                cmds[pidx] = f"SPORE ({pos.x},{pos.y})"
    return cmds


def _serialize_global_data(game: Game) -> str:
    lines = [f"{game.grid.width} {game.grid.height}"]
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


def record_episode(
    env_factory: Callable,
    main_bot: Any,
    main_agent: str,
    opponent_bot: Any,
) -> List[Dict[str, Any]]:
    """Run one deterministic episode and return viewer-ready frames.

    Parameters
    ----------
    env_factory:
        Zero-argument callable that returns a fresh CellularenaActionEnv.
    main_bot:
        The learning bot (player_0 by convention).
    main_agent:
        PettingZoo agent name for the learning bot.
    opponent_bot:
        The frozen opponent bot.

    Returns
    -------
    list[dict]
        Viewer frames list (frame 0 = global data, 1..N = per-turn data).
    """
    env = env_factory()
    obs, _ = env.reset()

    global_data_str = _serialize_global_data(env._game)
    frames: List[Dict[str, Any]] = [
        {"key": "0", "data": global_data_str, "stdout": ["", ""],
         "stderr": ["", ""], "gameInfo": [], "summary": None}
    ]

    before = _snapshot(env._game)
    turn = 1
    _supports_mask = hasattr(env, "action_mask")

    while env.agents:
        actions: Dict[str, Any] = {}
        for agent in env.agents:
            mask = env.action_mask(agent) if _supports_mask else None
            if agent == main_agent:
                action, _ = main_bot.select_action(obs[agent], deterministic=True, action_mask=mask)
            else:
                action, _ = opponent_bot.select_action(obs[agent], deterministic=True, action_mask=mask)
            actions[agent] = action

        obs, _, terms, truncs, _ = env.step(actions)

        after = _snapshot(env._game)
        events = _build_events(before, after)
        cmds = _derive_commands(events, before)
        frame_data_str = _serialize_frame_data(env._game, events)
        frames.append({
            "key": str(turn),
            "data": frame_data_str,
            "stdout": cmds,
            "stderr": ["", ""],
            "gameInfo": [],
            "summary": f"Turn {turn}",
        })
        before = after
        turn += 1

        if all(terms.values()) or all(truncs.values()):
            break

    env.close()
    return frames


def save_checkpoint_replay(
    checkpoint_path: Path,
    env_factory: Callable,
    main_bot: Any,
    main_agent: str,
    opponent_bot: Any,
    experiment_name: str,
    global_step: int,
    opponent_name: str,
    output_dir: Optional[Path] = None,
) -> Path:
    """Record one episode and save a viewer JSON file next to the checkpoint.

    The file is named ``<checkpoint_stem>_vs_<opponent_name>.viewer.json``.
    Agent 0 in the viewer is labelled ``<experiment_name>@step_<N>``;
    agent 1 is labelled with the league opponent name.
    """
    try:
        frames = record_episode(env_factory, main_bot, main_agent, opponent_bot)
    except Exception:
        log.exception("game_recorder: episode recording failed — skipping replay save.")
        return checkpoint_path  # non-fatal

    safe_opp = opponent_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    viewer_data = {
        "gameId": None,
        "agents": [
            {"index": 0, "name": f"{experiment_name}@step_{global_step}"},
            {"index": 1, "name": safe_opp},
        ],
        "frames": frames,
    }

    output_dir = output_dir or (checkpoint_path if checkpoint_path.is_dir() else checkpoint_path.parent)
    checkpoint_name = checkpoint_path.name if checkpoint_path.is_dir() else checkpoint_path.stem
    out_path = output_dir / f"{checkpoint_name}_vs_{safe_opp}.viewer.json"
    out_path.write_text(json.dumps(viewer_data))
    log.info("Checkpoint replay saved: %s (%d turns)", out_path.name, len(frames) - 1)
    return out_path
