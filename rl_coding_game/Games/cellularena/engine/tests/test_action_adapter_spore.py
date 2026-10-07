"""Cover the Discrete(4033) SPORE/ROOT decode branch of the action adapter.

The grow-channel decode path is exercised by the iterative-runtime tests, but
the ROOT channel (channel 0), which turns a discrete action into a SPORE slot
command, had no direct coverage. SPORE is the only way new organisms are
created, so a regression here would silently break multi-organism play.
"""
from __future__ import annotations

import numpy as np

from Games.cellularena.engine.action_adapter import (
    _action_index_from_channel_and_coord,
    choose_slot_action_for_action,
    discrete_action_to_slot_actions,
)
from Games.cellularena.engine.coord import Coord, Direction
from Games.cellularena.engine.game import Game, MAX_ROOTS, PlayerState
from Games.cellularena.engine.grid import Grid
from Games.cellularena.engine.organ import OrganType


def _sporer_game() -> tuple[Game, Coord]:
    """A ROOT + east-facing SPORER for player 0; returns the game and the
    last clear landing cell along the sporer's line of sight."""
    g = Game()
    g.grid = Grid(12, 5)
    g.players = [PlayerState(idx=0), PlayerState(idx=1)]
    g.organ_by_id = {}
    g.organ_by_coord = {}
    g.turn = 0
    g.done = False
    g.terminal_reason = ""
    g._next_organ_id = 1
    g.harvested_by_player = [0, 0]

    root = g._make_organ(0, OrganType.ROOT, Direction.NORTH)
    g._place_organ(root, Coord(0, 2))
    sporer = g._make_organ(0, OrganType.SPORER, Direction.EAST)
    g._place_organ(sporer, Coord(1, 2))
    g._connect(root, sporer)
    g.set_storage([5, 5, 5, 5], [0, 0, 0, 0])

    target = g._spore_target(sporer)
    assert target is not None
    return g, target


def test_discrete_root_channel_decodes_to_spore_slot_action():
    g, target = _sporer_game()
    # Channel 0 == place a ROOT (via SPORE) at `target`.
    action_index = _action_index_from_channel_and_coord(0, target)

    choice = choose_slot_action_for_action(g, 0, action_index)

    assert choice is not None, "ROOT/spore action should decode to a slot choice"
    assert choice.organ_type == OrganType.ROOT
    assert choice.target == target
    # SPORE slot actions live in the 65..68 range (direction encoded).
    assert 65 <= choice.action_int <= 68


def test_spore_action_executes_and_creates_new_root():
    g, target = _sporer_game()
    action_index = _action_index_from_channel_and_coord(0, target)

    slot_actions = discrete_action_to_slot_actions(g, 0, action_index)
    assert slot_actions.shape == (MAX_ROOTS,)
    assert np.count_nonzero(slot_actions) == 1

    roots_before = len(g.players[0].roots)
    done, _ = g.step({0: list(slot_actions), 1: [0] * MAX_ROOTS})

    assert len(g.players[0].roots) == roots_before + 1
    landed = g.grid.get(target).organ
    assert landed is not None and landed.type == OrganType.ROOT


def test_unaffordable_root_decodes_to_no_action():
    g, target = _sporer_game()
    g.set_storage([0, 0, 0, 0], [0, 0, 0, 0])  # cannot afford ROOT (1A1B1C1D)
    action_index = _action_index_from_channel_and_coord(0, target)

    choice = choose_slot_action_for_action(g, 0, action_index)

    assert choice is None
