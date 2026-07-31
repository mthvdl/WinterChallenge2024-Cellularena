"""
Replay transformation utilities.

This module keeps visualization generation outside core game logic:
1) Convert CodingGame replay JSON to a compact core-raw format.
2) Rebuild viewer display data by running the core game and serializing frames.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

_REPLAY_LOADER_PATH = Path(__file__).parent / "games" / "cellularena" / "game" / "replay_loader.py"
_spec = importlib.util.spec_from_file_location("replay_loader_local", _REPLAY_LOADER_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot load replay loader from {_REPLAY_LOADER_PATH}")
_replay_loader = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _replay_loader
_spec.loader.exec_module(_replay_loader)

Replay = _replay_loader.Replay
load_replay = _replay_loader.load_replay
_extract_graphics_from_view = _replay_loader._extract_graphics_from_view

try:
    from games.cellularena.game.coord import Coord
    from games.cellularena.game.game import Game
    from games.cellularena.game.grid import Protein
    _CORE_SIM_AVAILABLE = True
except Exception:
    Coord = object  # type: ignore[assignment]
    Game = None  # type: ignore[assignment]
    Protein = None  # type: ignore[assignment]
    _CORE_SIM_AVAILABLE = False

EV_GROW = 0
EV_DEATH = 3
EV_CRASH = 7
EV_SPAWN_ROOT = 8


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


def _extract_global_data_str(replay: Replay) -> str:
    raw_frame0 = replay.raw.get("frames", [{}])[0]
    return raw_frame0.get("data") or _extract_graphics_from_view(raw_frame0.get("view", "")) or ""


def _infer_initial_storage(global_data_str: str, replay: Replay) -> Optional[List[List[int]]]:
    if not _CORE_SIM_AVAILABLE:
        return None

    if not replay.turns:
        return None

    fd = replay.turns[0].frame_data
    if not fd.storage or len(fd.storage) < 2:
        return None

    target = fd.storage
    t1 = replay.turns[0]
    cmds = {p: (t1.stdout[p] if p < len(t1.stdout) else []) for p in range(2)}
    events = t1.frame_data.events

    for a in range(3, 11):
        for b in range(3, 11):
            for c in range(3, 11):
                for d in range(3, 11):
                    candidate = [a, b, c, d]
                    g = Game()
                    g.init_from_global_data(global_data_str)
                    g.set_storage(candidate, candidate)
                    g.step_replay(cmds, reference_events=events)
                    actual = [[g.players[i].storage[p] for p in Protein] for i in range(2)]
                    if actual == target:
                        return [list(candidate), list(candidate)]
    return None


def codingame_to_core_raw(codingame_data: Dict, source_label: str = "download") -> Dict:
    wrapped = codingame_data if "success" in codingame_data else {"success": codingame_data}
    replay = load_replay_from_dict(wrapped)

    global_data_str = _extract_global_data_str(replay)
    if not global_data_str:
        raise ValueError("Cannot extract global data string from replay")

    initial_storage = _infer_initial_storage(global_data_str, replay)

    turns = []
    for t in replay.turns:
        turns.append(
            {
                "turn": t.turn,
                "commands": [
                    t.stdout[0] if len(t.stdout) > 0 else [],
                    t.stdout[1] if len(t.stdout) > 1 else [],
                ],
            }
        )

    return {
        "format": "cellularena-core-raw-v1",
        "source": source_label,
        "gameId": codingame_data.get("gameId"),
        "agents": codingame_data.get("agents", []),
        "globalData": global_data_str,
        "initialStorage": initial_storage,
        "turns": turns,
    }


def load_replay_from_dict(raw_data: Dict) -> Replay:
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(raw_data, tmp)
        tmp_path = Path(tmp.name)
    try:
        return load_replay(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


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

    return GameState(organs=organs, obstacle_coords=obstacle_coords)


def _coord_list_text(coords: Sequence[Coord]) -> str:
    return "_".join(f"{c.x} {c.y}" for c in coords)


def _serialize_frame_data(game: Game, events: List[Dict]) -> str:
    if not _CORE_SIM_AVAILABLE:
        raise RuntimeError("Core simulation dependencies are not available")

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


def _events_from_reference(ref_events) -> List[Dict]:
    """Convert replay-loader EventData objects to serialized event dicts."""
    out: List[Dict] = []
    for ev in ref_events:
        coords = [Coord(x, y) for x, y in ev.coords]
        out.append(
            {
                "type": int(ev.type),
                "start": int(ev.start),
                "end": int(ev.end),
                "player_idx": int(ev.player_idx if ev.player_idx is not None else 0),
                "id": int(ev.organ_id if ev.organ_id is not None else 0),
                "organ_type": ev.organ_type or "",
                "direction": ev.direction or "",
                "coords": coords,
            }
        )
    return out


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


def add_display_data(core_raw: Dict, reference_turn_events: Optional[Dict[int, List]] = None) -> Dict:
    if not _CORE_SIM_AVAILABLE:
        raise RuntimeError("Core simulation dependencies are not available; install environment.yml deps first")

    if core_raw.get("format") != "cellularena-core-raw-v1":
        raise ValueError("Expected cellularena-core-raw-v1 input")

    global_data = core_raw.get("globalData", "")
    if not global_data:
        raise ValueError("Missing globalData")

    game = Game()
    game.init_from_global_data(global_data)

    init_storage = core_raw.get("initialStorage")
    if init_storage and len(init_storage) == 2:
        game.set_storage(init_storage[0], init_storage[1])

    frames = [{"key": "0", "data": global_data, "gameInfo": [], "summary": None}]

    for turn_entry in core_raw.get("turns", []):
        cmds0 = turn_entry.get("commands", [[], []])[0]
        cmds1 = turn_entry.get("commands", [[], []])[1]
        commands = {0: cmds0, 1: cmds1}
        turn = int(turn_entry.get("turn", len(frames)))

        ref_events = None
        if reference_turn_events is not None:
            ref_events = reference_turn_events.get(turn)

        before = _snapshot_state(game)
        if ref_events is not None:
            done, _ = game.step_replay(commands, reference_events=ref_events)
        else:
            done, _ = game.step_replay(commands)
        after = _snapshot_state(game)

        if ref_events is not None:
            events = _events_from_reference(ref_events)
        else:
            events = _build_events(before, after)
        frame_data = _serialize_frame_data(game, events)

        frames.append(
            {
                "key": str(turn),
                "data": frame_data,
                "stdout": ["\n".join(cmds0), "\n".join(cmds1)],
                "stderr": ["", ""],
                "gameInfo": [],
                "summary": (
                    f"Turn {turn} | P0:{game.players[0].organ_count} "
                    f"P1:{game.players[1].organ_count}"
                ),
            }
        )

        if done:
            break

    return {
        "gameId": core_raw.get("gameId"),
        "agents": core_raw.get("agents", []),
        "frames": frames,
    }


def codingame_to_viewer(codingame_data: Dict) -> Dict:
    wrapped = codingame_data if "success" in codingame_data else {"success": codingame_data}
    replay = load_replay_from_dict(wrapped)

    global_data = _extract_global_data_str(replay)
    if not global_data:
        raise ValueError("Cannot extract global data from CodingGame replay")

    frames: List[Dict] = [
        {
            "key": "0",
            "data": global_data,
            "gameInfo": [],
            "summary": None,
        }
    ]

    for turn in replay.turns:
        frame_data = _serialize_replay_frame_data(turn.frame_data)
        stdout0 = "\n".join(turn.stdout[0]) if len(turn.stdout) > 0 else ""
        stdout1 = "\n".join(turn.stdout[1]) if len(turn.stdout) > 1 else ""
        frames.append(
            {
                "key": str(turn.turn),
                "data": frame_data,
                "stdout": [stdout0, stdout1],
                "stderr": ["", ""],
                "gameInfo": [],
                "summary": turn.summary or "",
            }
        )

    return {
        "gameId": codingame_data.get("gameId"),
        "agents": codingame_data.get("agents", []),
        "frames": frames,
    }


def _serialize_replay_frame_data(frame_data) -> str:
    lines: List[str] = []

    for player_idx in range(2):
        storage = frame_data.storage[player_idx] if player_idx < len(frame_data.storage) else [0, 0, 0, 0]
        lines.append(" ".join(str(x) for x in storage))

        messages = frame_data.messages[player_idx] if player_idx < len(frame_data.messages) else {}
        lines.append(str(len(messages)))
        for organ_id, text in messages.items():
            lines.append(f"{organ_id} {text}".rstrip())

    lines.append(str(len(frame_data.events)))
    for ev in frame_data.events:
        lines.append(str(ev.type))
        lines.append(str(int(ev.start)))
        lines.append(str(int(ev.end)))
        lines.append(str(ev.player_idx if ev.player_idx is not None else 0))
        lines.append(str(ev.organ_id if ev.organ_id is not None else 0))
        lines.append(ev.organ_type or "")
        lines.append(ev.direction or "")
        lines.append("_".join(f"{x} {y}" for x, y in ev.coords))

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay transformations")
    parser.add_argument("--input", required=True, help="Input replay path")
    parser.add_argument("--output", required=True, help="Output replay path")
    parser.add_argument(
        "--mode",
        choices=["to-core", "to-viewer", "cg-to-viewer"],
        required=True,
        help="to-core: CodingGame -> core raw, to-viewer: core raw -> viewer replay, cg-to-viewer: CodingGame -> viewer replay",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    data = json.loads(in_path.read_text(encoding="utf-8"))

    if args.mode == "to-core":
        out = codingame_to_core_raw(data)
    elif args.mode == "to-viewer":
        out = add_display_data(data)
    else:
        out = codingame_to_viewer(data)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
