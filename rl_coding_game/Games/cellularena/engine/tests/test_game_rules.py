"""Isolated unit tests for the core Cellularena game rules.

These lock down the individual rule mechanics that were previously only
exercised incidentally through random episodes or whole-replay validation:
protein absorption on growth, harvesting, tentacle combat with child-subtree
removal, growth collisions turning a cell into a wall, and sporing a new ROOT.

Deterministic boards are built directly through the engine's organ/grid
primitives so every assertion targets one rule in isolation.
"""
from __future__ import annotations

import pytest

from Games.cellularena.engine.coord import Coord, Direction
from Games.cellularena.engine.game import Game, GrowthCommand, PROTEIN_PER_ABSORB
from Games.cellularena.engine.grid import Grid, Protein
from Games.cellularena.engine.organ import Organ, OrganType


def _blank_game(width: int = 7, height: int = 5) -> Game:
    """A game with an explicit empty grid and two players, no random map."""
    g = Game()
    g.grid = Grid(width, height)
    from Games.cellularena.engine.game import PlayerState

    g.players = [PlayerState(idx=0), PlayerState(idx=1)]
    g.organ_by_id = {}
    g.organ_by_coord = {}
    g.turn = 0
    g.done = False
    g.terminal_reason = ""
    g._next_organ_id = 1
    g.harvested_by_player = [0, 0]
    return g


def _add_root(g: Game, player_idx: int, pos: Coord, direction: Direction = Direction.NORTH) -> Organ:
    root = g._make_organ(player_idx, OrganType.ROOT, direction)
    g._place_organ(root, pos)
    return root


# ---------------------------------------------------------------------------
# Protein absorption and cost
# ---------------------------------------------------------------------------

def test_growing_onto_protein_absorbs_three():
    g = _blank_game()
    root = _add_root(g, 0, Coord(1, 1))
    target = Coord(2, 1)
    g.grid.get(target).set_protein(Protein.B.value)
    g.set_storage([5, 5, 5, 5], [0, 0, 0, 0])

    cmd = GrowthCommand(
        player_idx=0,
        from_organ_id=root.id,
        target=target,
        organ_type=OrganType.BASIC,
        direction=Direction.NORTH,
    )
    # Mirror the engine's turn flow: cost is paid when the command is queued,
    # absorption happens when the organ is placed.
    g.players[0].pay_for(OrganType.BASIC)
    g._resolve_growth([cmd])

    storage = g.players[0].storage
    # BASIC costs 1A; growing onto a B tile grants +3B.
    assert storage[Protein.A] == 4
    assert storage[Protein.B] == 5 + PROTEIN_PER_ABSORB
    assert g.grid.get(target).has_organ()
    assert not g.grid.get(target).has_protein()


# ---------------------------------------------------------------------------
# Harvesting
# ---------------------------------------------------------------------------

def test_harvester_gains_one_per_turn_from_faced_protein():
    g = _blank_game()
    _add_root(g, 0, Coord(1, 1))
    harvester = g._make_organ(0, OrganType.HARVESTER, Direction.EAST)
    g._place_organ(harvester, Coord(2, 1))
    faced = harvester.get_faced_coord()  # (3,1)
    g.grid.get(faced).set_protein(Protein.C.value)
    g.set_storage([0, 0, 0, 0], [0, 0, 0, 0])

    g._do_harvests()

    assert g.players[0].storage[Protein.C] == 1
    assert g.harvested_by_player[0] == 1
    # Harvesting does not consume the protein tile.
    assert g.grid.get(faced).has_protein()


def test_harvester_facing_empty_tile_harvests_nothing():
    g = _blank_game()
    _add_root(g, 0, Coord(1, 1))
    harvester = g._make_organ(0, OrganType.HARVESTER, Direction.EAST)
    g._place_organ(harvester, Coord(2, 1))
    g.set_storage([0, 0, 0, 0], [0, 0, 0, 0])

    g._do_harvests()

    assert g.players[0].protein_total == 0
    assert g.harvested_by_player[0] == 0


# ---------------------------------------------------------------------------
# Tentacle combat + subtree cascade
# ---------------------------------------------------------------------------

def test_tentacle_kills_faced_enemy_and_removes_child_subtree():
    g = _blank_game()
    # Player 0 tentacle at (2,2) facing east toward (3,2).
    _add_root(g, 0, Coord(1, 2))
    tentacle = g._make_organ(0, OrganType.TENTACLE, Direction.EAST)
    g._place_organ(tentacle, Coord(2, 2))

    # Player 1 organism: ROOT at (3,2) with a BASIC child at (4,2) and a
    # grandchild at (5,2). Killing the faced ROOT must cascade to both.
    enemy_root = _add_root(g, 1, Coord(3, 2))
    child = g._make_organ(1, OrganType.BASIC, Direction.NORTH)
    g._place_organ(child, Coord(4, 2))
    g._connect(enemy_root, child)
    grandchild = g._make_organ(1, OrganType.BASIC, Direction.NORTH)
    g._place_organ(grandchild, Coord(5, 2))
    g._connect(child, grandchild)

    assert g.players[1].organ_count == 3

    g._do_attacks()

    # Entire enemy subtree removed.
    assert g.players[1].organ_count == 0
    for coord in (Coord(3, 2), Coord(4, 2), Coord(5, 2)):
        assert not g.grid.get(coord).has_organ()
    for oid in (enemy_root.id, child.id, grandchild.id):
        assert oid not in g.organ_by_id
    # Attacker survives.
    assert g.players[0].organ_count == 2


def test_tentacle_does_not_kill_friendly_organ():
    g = _blank_game()
    root = _add_root(g, 0, Coord(1, 2))
    tentacle = g._make_organ(0, OrganType.TENTACLE, Direction.EAST)
    g._place_organ(tentacle, Coord(2, 2))
    friendly = g._make_organ(0, OrganType.BASIC, Direction.NORTH)
    g._place_organ(friendly, Coord(3, 2))
    g._connect(root, friendly)

    g._do_attacks()

    assert g.players[0].organ_count == 3
    assert g.grid.get(Coord(3, 2)).has_organ()


# ---------------------------------------------------------------------------
# Growth collision
# ---------------------------------------------------------------------------

def test_collision_makes_cell_a_wall_and_places_no_organ():
    g = _blank_game()
    root0 = _add_root(g, 0, Coord(1, 2))
    root1 = _add_root(g, 1, Coord(3, 2))
    contested = Coord(2, 2)
    g.set_storage([5, 5, 5, 5], [5, 5, 5, 5])

    cmd0 = GrowthCommand(0, root0.id, contested, OrganType.BASIC, Direction.NORTH)
    cmd1 = GrowthCommand(1, root1.id, contested, OrganType.BASIC, Direction.NORTH)
    g._resolve_growth([cmd0, cmd1])

    tile = g.grid.get(contested)
    assert tile.obstacle
    assert not tile.has_organ()
    # Neither player gained an organ from the contested cell.
    assert g.players[0].organ_count == 1
    assert g.players[1].organ_count == 1


# ---------------------------------------------------------------------------
# Sporing a new ROOT
# ---------------------------------------------------------------------------

def test_sporer_target_is_last_clear_cell_in_line():
    g = _blank_game(width=7, height=3)
    _add_root(g, 0, Coord(0, 1))
    sporer = g._make_organ(0, OrganType.SPORER, Direction.EAST)
    g._place_organ(sporer, Coord(1, 1))
    # Obstacle at (5,1) blocks the line; last reachable clear cell is (4,1).
    g.grid.get(Coord(5, 1)).set_obstacle()

    target = g._spore_target(sporer)

    assert target == Coord(4, 1)


def test_spore_command_creates_new_root_organism():
    g = _blank_game(width=7, height=3)
    _add_root(g, 0, Coord(0, 1))
    sporer = g._make_organ(0, OrganType.SPORER, Direction.EAST)
    g._place_organ(sporer, Coord(1, 1))
    g.set_storage([5, 5, 5, 5], [0, 0, 0, 0])

    cmd = g._find_spore_cmd(g.players[0], g._get_root_id(sporer), Direction.EAST)
    assert cmd is not None and cmd.is_spore and cmd.organ_type == OrganType.ROOT

    roots_before = len(g.players[0].roots)
    g.players[0].pay_for(OrganType.ROOT)
    g._resolve_growth([cmd])

    assert len(g.players[0].roots) == roots_before + 1
    new_root = g.grid.get(cmd.target).organ
    assert new_root is not None
    assert new_root.type == OrganType.ROOT
    # A spored ROOT starts a new organism (no parent link).
    assert new_root.parent is None


# ---------------------------------------------------------------------------
# Affordability
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "organ_type,cost",
    [
        (OrganType.ROOT, [1, 1, 1, 1]),
        (OrganType.BASIC, [1, 0, 0, 0]),
        (OrganType.TENTACLE, [0, 1, 1, 0]),
        (OrganType.HARVESTER, [0, 0, 1, 1]),
        (OrganType.SPORER, [0, 1, 0, 1]),
    ],
)
def test_can_afford_matches_exact_cost(organ_type, cost):
    g = _blank_game()
    player = g.players[0]
    # Exactly enough -> affordable.
    g.set_storage(cost, [0, 0, 0, 0])
    assert player.can_afford(organ_type)
    # One short on any required protein -> not affordable.
    for i, c in enumerate(cost):
        if c == 0:
            continue
        short = list(cost)
        short[i] -= 1
        g.set_storage(short, [0, 0, 0, 0])
        assert not player.can_afford(organ_type)
