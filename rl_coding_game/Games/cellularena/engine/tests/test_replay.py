"""Smoke-test replay infrastructure without real replays."""
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).parent))

from Games.cellularena.engine.game import Game
from Games.cellularena.engine.coord import Coord
from Games.cellularena.engine.grid import Grid, Protein
from Games.cellularena.engine.organ import OrganType
from Games.cellularena.engine.replay_loader import load_replay
from Games.cellularena.engine.tools.validate_engine import _reference_outcome

# ──────────────────────────────────────────────────────────────────────────────
# Build a synthetic global-data string to test init_from_global_data
# ──────────────────────────────────────────────────────────────────────────────
def make_synthetic_global_data():
    """5x3 grid: wall at (2,1), protein A at (3,1), organs at (0,0) and (4,2)."""
    lines = []
    lines.append("5 3")          # width height
    for y in range(3):
        for x in range(5):
            if x == 2 and y == 1:
                lines.append("1 X")   # wall
            elif x == 3 and y == 1:
                lines.append("0 A")   # protein A
            else:
                lines.append("0 X")   # empty
    # Player 0: 1 organ (ROOT id=1, (0,0), N, parent=0)
    lines.append("1")
    lines.append("1 0 0 ROOT N 0")
    # Player 1: 1 organ (ROOT id=2, (4,2), N, parent=0)
    lines.append("1")
    lines.append("2 4 2 ROOT N 0")
    return "\n".join(lines)


def test_init_from_global_data():
    gd = make_synthetic_global_data()
    g = Game()
    g.init_from_global_data(gd)

    assert g.grid.width == 5
    assert g.grid.height == 3
    assert g.grid.get(Coord(2,1)).obstacle, "wall missing"
    assert g.grid.get(Coord(3,1)).protein == Protein.A, "protein missing"
    assert len(g.players[0].organs) == 1
    assert len(g.players[1].organs) == 1
    assert g.organ_by_id[1].owner_idx == 0
    assert g.organ_by_id[2].owner_idx == 1
    print("  init_from_global_data OK")


def test_replay_step():
    """Run a few turns with raw command strings."""
    g = Game(seed=99)
    g.reset()
    g.set_storage([10,10,10,10], [10,10,10,10])

    # Find a valid adjacent cell for player 0's first organ
    root_p0 = g.players[0].roots[0]
    pos = root_p0.pos
    grid = g.grid
    
    # Find first free neighbour for player 0
    from Games.cellularena.engine.coord import ADJACENCY
    target_p0 = None
    for d in ADJACENCY:
        t = pos.add(d)
        tile = grid.get(t)
        if tile and not tile.obstacle and not tile.has_organ():
            target_p0 = t
            break

    root_p1 = g.players[1].roots[0]
    pos1 = root_p1.pos
    target_p1 = None
    for d in ADJACENCY:
        t = pos1.add(d)
        tile = grid.get(t)
        if tile and not tile.obstacle and not tile.has_organ():
            target_p1 = t
            break

    cmd0 = f"GROW {root_p0.id} {target_p0.x} {target_p0.y} BASIC N" if target_p0 else "WAIT"
    cmd1 = f"GROW {root_p1.id} {target_p1.x} {target_p1.y} BASIC N" if target_p1 else "WAIT"

    organs_before = [g.players[i].organ_count for i in range(2)]
    done, _ = g.step_replay({0: [cmd0], 1: [cmd1]})

    organs_after = [g.players[i].organ_count for i in range(2)]
    # Each player should have grown one organ (unless target was None)
    if target_p0:
        assert organs_after[0] > organs_before[0], "P0 organ not grown"
    if target_p1:
        assert organs_after[1] > organs_before[1], "P1 organ not grown"
    print(f"  step_replay OK — organs {organs_before} → {organs_after}")


def test_single_starvation_ends_game():
    """CodingGame ends when either player cannot evolve or harvest again."""
    g = Game(seed=7, map_width=20, map_height=10)
    g.reset()
    g.set_storage([0, 0, 0, 0], [1, 0, 0, 0])

    done, rewards = g.step({0: [0], 1: [0]})

    assert done
    assert g.terminal_reason == "player_starved"
    assert rewards == {0: -0.5, 1: 0.5}


def test_final_league_does_not_end_on_starvation():
    g = Game(seed=7, map_width=24, map_height=12)
    g.reset()
    g.set_storage([0, 0, 0, 0], [1, 0, 0, 0])

    done, _ = g.step({0: [0], 1: [0]})

    assert not done
    assert g.terminal_reason == ""


def test_missing_replay_command_disqualifies_player():
    g = Game(seed=7)
    g.reset()
    g.set_storage([10, 10, 10, 10], [10, 10, 10, 10])

    done, rewards = g.step_replay({0: [], 1: ["WAIT"]})

    assert done
    assert g.terminal_reason == "player_disqualified"
    assert rewards == {0: -1.0, 1: 1.0}


def test_both_starved_uses_normal_tiebreak():
    """Simultaneous starvation ends the game without a double-win reward."""
    g = Game(seed=8)
    g.reset()
    g.set_storage([0, 0, 0, 0], [0, 0, 0, 0])

    done, rewards = g.step({0: [0], 1: [0]})

    assert done
    assert g.terminal_reason == "both_players_starved"
    assert rewards == {0: 0.0, 1: 0.0}


def test_equal_codingame_ranks_are_a_tie():
    replay = SimpleNamespace(raw={"ranks": [0, 0]}, turns=[])

    assert _reference_outcome(replay, None) == "TIE"


def test_parse_commands():
    g = Game(seed=1)
    g.reset()
    # Parse WAIT — should return None
    c = g.parse_raw_command("WAIT", 0)
    assert c is None, "WAIT should return None"

    # Parse invalid command
    c = g.parse_raw_command("INVALID COMMAND", 0)
    assert c is None

    print("  parse_raw_command OK")


def test_state_snapshot():
    g = Game(seed=5)
    g.reset()
    snap = g.get_state_snapshot()
    assert "grid" in snap
    assert "storage" in snap
    assert "organs" in snap
    assert snap["turn"] == 0
    print("  get_state_snapshot OK")


if __name__ == "__main__":
    print("Testing replay infrastructure ...\n")
    tests = [
        test_init_from_global_data,
        test_replay_step,
        test_parse_commands,
        test_state_snapshot,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            import traceback; traceback.print_exc()

    print(f"\n{passed}/{len(tests)} tests passed.")
    sys.exit(0 if passed == len(tests) else 1)
