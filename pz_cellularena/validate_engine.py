"""
validate_engine.py – Validate the PettingZoo engine against CodingGame replays.

For each downloaded replay the script:
  1. Initialises the engine from the replay's initial state
  2. Infers initial protein storage (brute-force over 8^4 candidates)
  3. Feeds each turn's player commands (from replay stdout) into the engine
  4. After every turn compares the engine state against the reference state
     derived from the replay's GROW / DEATH / CRASH events + storage fields

Two comparison layers are performed:
  * Storage comparison  – exact A/B/C/D protein counts per player
  * Full organ comparison – every organ's (x, y, type, owner, direction)

Usage
-----
    cd pz_cellularena
    python validate_engine.py                                # default test replays in replays/
    python validate_engine.py replays/codingame_884960630.json # one file
    python validate_engine.py --loop                 # re-run after fixes

Exit 0 = 100% accurate, Exit 1 = discrepancies found.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from games.cellularena.game.game import Game, MAX_TURNS
from games.cellularena.game.coord import Coord
from games.cellularena.game.grid import Protein
from games.cellularena.game.organ import OrganType
from games.cellularena.game.replay_loader import (
    EventData, FrameData, GlobalData, Replay, ReplayTurn,
    load_replay, _extract_graphics_from_view,
)

REPLAY_DIR = Path(__file__).parent / "replays"

# ──────────────────────────────────────────────────────────────────────────────
# Event-type constants (from Java EventData)
# ──────────────────────────────────────────────────────────────────────────────
EV_GROW           = 0
EV_SPORE          = 1   # animation only; ROOT appears via EV_SPAWN_NUCLEUS
EV_ATTACK         = 2   # animation only; organ removal via EV_DEATH
EV_DEATH          = 3
EV_HARVEST        = 5   # animation only
EV_ABSORB         = 6   # animation only
EV_CRASH          = 7   # collision → cell becomes wall
EV_SPAWN_NUCLEUS  = 8   # new ROOT from SPORE command


# ──────────────────────────────────────────────────────────────────────────────
# Reference state tracker (maintained from events)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class RefOrgan:
    organ_id:   int
    owner:      int
    x:          int
    y:          int
    organ_type: str   # 'ROOT', 'BASIC', 'TENTACLE', 'HARVESTER', 'SPORER'
    direction:  str   # 'N', 'E', 'S', 'W'


class RefState:
    """
    Reconstructs the authoritative game state turn-by-turn using the
    GROW / DEATH / CRASH events from the CodingGame replay.
    """

    def __init__(self, global_data: GlobalData) -> None:
        self.organs: Dict[int, RefOrgan] = {}
        self.walls:  Set[Tuple[int, int]] = set()
        self.proteins: Dict[Tuple[int, int], str] = {}

        for tile in global_data.tiles:
            if tile.obstacle:
                self.walls.add((tile.x, tile.y))
            elif tile.protein:
                self.proteins[(tile.x, tile.y)] = tile.protein

        for player_idx, player_organs in enumerate(global_data.organs):
            for od in player_organs:
                self.organs[od.organ_id] = RefOrgan(
                    organ_id   = od.organ_id,
                    owner      = player_idx,
                    x          = od.x,
                    y          = od.y,
                    organ_type = od.organ_type,
                    direction  = od.direction if od.direction not in ('X', '') else 'N',
                )

    def apply(self, events: List[EventData]) -> None:
        """Apply one turn's events to advance the reference state."""
        for ev in events:

            # ── New organ placed (GROW or SPAWN_NUCLEUS) ──────────────────────
            if ev.type in (EV_GROW, EV_SPAWN_NUCLEUS):
                if not ev.coords:
                    continue
                new_xy = ev.coords[1] if (ev.type == EV_GROW and len(ev.coords) >= 2) \
                         else ev.coords[0]

                self.proteins.pop(new_xy, None)  # organ absorbs protein on arrival

                self.organs[ev.organ_id] = RefOrgan(
                    organ_id   = ev.organ_id,
                    owner      = ev.player_idx if ev.player_idx is not None else 0,
                    x          = new_xy[0],
                    y          = new_xy[1],
                    organ_type = ev.organ_type or ('ROOT' if ev.type == EV_SPAWN_NUCLEUS else 'BASIC'),
                    direction  = (ev.direction or 'N').upper()[:1],
                )

            # ── Organ removed ─────────────────────────────────────────────────
            elif ev.type == EV_DEATH:
                if ev.organ_id is not None:
                    self.organs.pop(ev.organ_id, None)

            # ── Collision → wall ─────────────────────────────────────────────
            elif ev.type == EV_CRASH:
                if ev.coords:
                    self.walls.add(ev.coords[0])

    def organ_by_pos(self) -> Dict[Tuple[int, int], RefOrgan]:
        return {(o.x, o.y): o for o in self.organs.values()}


# ──────────────────────────────────────────────────────────────────────────────
# Storage inference (same as before)
# ──────────────────────────────────────────────────────────────────────────────

def _infer_initial_storage(
    global_data_str: str, replay: Replay
) -> Optional[List[List[int]]]:
    if not replay.turns:
        return None
    fd = replay.turns[0].frame_data
    if not fd.storage or not fd.storage[0]:
        return None

    target = fd.storage
    t1     = replay.turns[0]
    cmds   = {p: (t1.stdout[p] if p < len(t1.stdout) else []) for p in range(2)}
    events = t1.frame_data.events   # use reference events for correct organ IDs

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


# ──────────────────────────────────────────────────────────────────────────────
# Per-turn comparison
# ──────────────────────────────────────────────────────────────────────────────

def _storage_str(s: List[int]) -> str:
    return f"A:{s[0]} B:{s[1]} C:{s[2]} D:{s[3]}"


def compare_turn(
    engine:   Game,
    ref:      RefState,
    ref_storage: List[List[int]],
    turn:     int,
) -> List[str]:
    """
    Return a list of discrepancy strings (empty = perfect match).
    Compares storage and full organ state.
    """
    issues: List[str] = []

    # ── Storage ───────────────────────────────────────────────────────────────
    for p_idx in range(2):
        if p_idx >= len(ref_storage):
            continue
        ref_s = ref_storage[p_idx]
        act_s = [engine.players[p_idx].storage[p] for p in Protein]
        if act_s != ref_s:
            issues.append(
                f"T{turn:03d} P{p_idx} STORAGE  engine={_storage_str(act_s)}  "
                f"ref={_storage_str(ref_s)}"
            )

    # ── Organ count ───────────────────────────────────────────────────────────
    for p_idx in range(2):
        ref_cnt = sum(1 for o in ref.organs.values() if o.owner == p_idx)
        act_cnt = engine.players[p_idx].organ_count
        if ref_cnt != act_cnt:
            issues.append(
                f"T{turn:03d} P{p_idx} COUNT    engine={act_cnt}  ref={ref_cnt}"
            )

    # ── Organ positions & types ───────────────────────────────────────────────
    ref_by_pos = ref.organ_by_pos()     # {(x,y): RefOrgan}

    # Check every engine organ against reference
    for coord, tile in engine.grid.cells.items():
        if not tile.has_organ():
            continue
        eng_o = tile.organ
        key   = (coord.x, coord.y)
        ref_o = ref_by_pos.get(key)
        if ref_o is None:
            issues.append(
                f"T{turn:03d} EXTRA    engine has {eng_o.type.name}(P{eng_o.owner_idx}) "
                f"at {key} but ref doesn't"
            )
        else:
            if ref_o.owner != eng_o.owner_idx:
                issues.append(
                    f"T{turn:03d} OWNER    at {key}: engine=P{eng_o.owner_idx}  ref=P{ref_o.owner}"
                )
            if ref_o.organ_type != eng_o.type.name:
                issues.append(
                    f"T{turn:03d} TYPE     at {key}: engine={eng_o.type.name}  ref={ref_o.organ_type}"
                )
            eng_dir = eng_o.direction.name[0]
            ref_dir = (ref_o.direction or 'N')[0].upper()
            if ref_dir != 'X' and ref_dir != eng_dir:
                issues.append(
                    f"T{turn:03d} DIR      at {key}: engine={eng_dir}  ref={ref_dir}"
                )

    # Check every reference organ is in the engine
    for key, ref_o in ref_by_pos.items():
        tile = engine.grid.get(Coord(key[0], key[1]))
        if tile is None or not tile.has_organ():
            issues.append(
                f"T{turn:03d} MISSING  ref has {ref_o.organ_type}(P{ref_o.owner}) "
                f"at {key} but engine doesn't"
            )

    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Per-replay validation
# ──────────────────────────────────────────────────────────────────────────────

def validate_replay(path: Path, verbose: bool = True) -> Dict:
    print(f"\n{'='*70}")
    print(f"Replay: {path.name}")

    try:
        replay = load_replay(path)
    except Exception as exc:
        print(f"  ERROR loading replay: {exc}")
        return {"path": path, "error": str(exc), "issues": [str(exc)]}

    agents = " vs ".join(
        a.get("name") or a.get("pseudo") or "?"
        for a in replay.agents[:2]
    ) or "(unknown players)"
    print(f"  Players: {agents}   Turns: {len(replay.turns)}")

    # ── Extract global data string ────────────────────────────────────────────
    raw_frame0 = replay.raw.get("frames", [{}])[0]
    global_data_str = (
        raw_frame0.get("data")
        or _extract_graphics_from_view(raw_frame0.get("view", ""))
        or ""
    )
    if not global_data_str:
        msg = "Cannot extract global data from replay"
        print(f"  ERROR: {msg}")
        return {"path": path, "error": msg, "issues": [msg]}

    # ── Init engine ───────────────────────────────────────────────────────────
    game = Game()
    game.init_from_global_data(global_data_str)

    initial_storage = _infer_initial_storage(global_data_str, replay)
    if initial_storage:
        game.set_storage(initial_storage[0], initial_storage[1])
        print(f"  Initial storage: {_storage_str(initial_storage[0])}")
    else:
        print("  WARN: could not infer initial storage -- using zeros")

    # ── Init reference state tracker ─────────────────────────────────────────
    ref = RefState(replay.global_data)

    # ── Run turns ─────────────────────────────────────────────────────────────
    all_issues: List[str] = []
    storage_ok = organ_ok = 0

    for turn_data in replay.turns:
        turn_num = turn_data.turn
        cmds: Dict[int, List[str]] = {
            p: (turn_data.stdout[p] if p < len(turn_data.stdout) else [])
            for p in range(2)
        }

        # Advance engine — pass reference events so organ IDs match exactly
        done, _ = game.step_replay(cmds, reference_events=turn_data.frame_data.events)

        # Advance reference state
        ref.apply(turn_data.frame_data.events)

        # Compare
        turn_issues = compare_turn(
            game, ref, turn_data.frame_data.storage, turn_num
        )
        all_issues.extend(turn_issues)

        # Track per-metric accuracy
        storage_issue = any("STORAGE" in i for i in turn_issues)
        organ_issue   = any(k in i for k in ("EXTRA", "MISSING", "COUNT", "OWNER", "TYPE", "DIR") for i in turn_issues)
        if not storage_issue:
            storage_ok += 1
        if not organ_issue:
            organ_ok += 1

        if done:
            break

    total = len(replay.turns)
    print(f"  Storage match: {storage_ok}/{total} ({100*storage_ok/max(total,1):.0f}%)")
    print(f"  Organ   match: {organ_ok}/{total}  ({100*organ_ok/max(total,1):.0f}%)")

    if all_issues:
        print(f"  First 10 issues:")
        for issue in all_issues[:10]:
            print(f"    FAIL  {issue}")
    else:
        print(f"  OK    All {total} turns match exactly!")

    return {
        "path":          path,
        "turns":         total,
        "issues":        all_issues,
        "storage_pct":   storage_ok / max(total, 1),
        "organ_pct":     organ_ok   / max(total, 1),
        "agents":        agents,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Cellularena PettingZoo engine against replays"
    )
    parser.add_argument("replays", nargs="*", help="Replay JSON(s); default = CodingGame/synthetic samples in replays/")
    parser.add_argument("--loop",    action="store_true", help="Re-run after manual fixes")
    parser.add_argument("--verbose", action="store_true", default=True)
    args = parser.parse_args()

    if args.replays:
        paths = [Path(p) for p in args.replays]
    else:
        codingame = sorted(REPLAY_DIR.glob("codingame_*.json"))
        synthetic = sorted(REPLAY_DIR.glob("synthetic_*.json"))
        fallback = [
            p for p in sorted(REPLAY_DIR.glob("*.json"))
            if not p.name.startswith("core_")
        ]
        paths = codingame + synthetic
        if not paths:
            paths = fallback
    if not paths:
        print(f"No replays found in {REPLAY_DIR}")
        print("Run  python download_games.py  first.")
        return 1

    print(f"Validating {len(paths)} replay(s) ...")

    def run_all() -> int:
        results = [validate_replay(p, args.verbose) for p in paths]
        total_issues = sum(len(r.get("issues", [])) for r in results)
        perfect = sum(1 for r in results if not r.get("issues"))

        print(f"\n{'='*70}")
        print(f"Summary: {perfect}/{len(results)} replays 100% accurate")
        for r in results:
            status = "OK  " if not r.get("issues") else f"FAIL ({len(r.get('issues',[]))} issues)"
            sp = r.get("storage_pct", 0)
            op = r.get("organ_pct", 0)
            print(f"  {status}  {r['path'].name}  "
                  f"storage={sp*100:.0f}%  organs={op*100:.0f}%")

        if total_issues == 0:
            print("\nEngine is 100% accurate on all replays!")
            return 0
        else:
            print(f"\n{total_issues} discrepancies found.")
            print("Fix games/cellularena/game/game.py and re-run.")
            return 1

    if not args.loop:
        return run_all()

    while True:
        rc = run_all()
        if rc == 0:
            return 0
        try:
            if input("\nRe-run after fixes? [y/N] ").strip().lower() != "y":
                return rc
        except EOFError:
            return rc


if __name__ == "__main__":
    sys.exit(main())
