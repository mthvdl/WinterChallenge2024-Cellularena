"""Paper-policy action adapters for Cellularena.

This module bridges the paper policy head (Discrete 4033) and the engine's
native per-root MultiDiscrete actions.

Action indexing (paper head)
----------------------------
- 0..4031: 14 grow channels over a 12x24 map (channel-major order)
- 4032   : WAIT
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

from Games.cellularena.engine.coord import Coord, Direction
from Games.cellularena.engine.game import ACTIONS_PER_ORG, Game, MAX_H, MAX_ROOTS, MAX_W
from Games.cellularena.engine.grid import Protein
from Games.cellularena.engine.organ import Organ, OrganType

N_GROW_CHANNELS = 14
N_GROW_ACTIONS = N_GROW_CHANNELS * MAX_H * MAX_W
WAIT_ACTION_INDEX = N_GROW_ACTIONS
N_ACTIONS = WAIT_ACTION_INDEX + 1

_DIRS = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
_ORG_TYPE_TO_SLOT_IDX = {
    OrganType.BASIC: 0,
    OrganType.TENTACLE: 1,
    OrganType.HARVESTER: 2,
    OrganType.SPORER: 3,
}


@dataclass(frozen=True)
class ActionSpec:
    is_wait: bool
    target: Optional[Coord]
    organ_type: Optional[OrganType]
    face_dir: Optional[Direction]


@dataclass(frozen=True)
class SlotActionChoice:
    slot: int
    action_int: int
    target: Optional[Coord]
    organ_type: Optional[OrganType]


@dataclass(frozen=True)
class IterativeMaskState:
    remaining_storage: np.ndarray
    used_slots: frozenset[int]
    blocked_targets: frozenset[Coord]


def _coord_to_linear(c: Coord) -> int:
    return c.y * MAX_W + c.x


def _action_index_from_channel_and_coord(channel_idx: int, coord: Coord) -> int:
    return channel_idx * (MAX_H * MAX_W) + _coord_to_linear(coord)


def _decode_action_index(action_index: int) -> ActionSpec:
    idx = int(action_index)
    if idx < 0 or idx >= N_ACTIONS:
        return ActionSpec(is_wait=True, target=None, organ_type=None, face_dir=None)
    if idx == WAIT_ACTION_INDEX:
        return ActionSpec(is_wait=True, target=None, organ_type=None, face_dir=None)

    per_channel = MAX_H * MAX_W
    channel_idx = idx // per_channel
    rem = idx % per_channel
    y = rem // MAX_W
    x = rem % MAX_W
    target = Coord(x, y)

    if channel_idx == 0:
        return ActionSpec(is_wait=False, target=target, organ_type=OrganType.ROOT, face_dir=Direction.NORTH)
    if channel_idx == 1:
        return ActionSpec(is_wait=False, target=target, organ_type=OrganType.BASIC, face_dir=Direction.NORTH)
    if 2 <= channel_idx <= 5:
        return ActionSpec(
            is_wait=False,
            target=target,
            organ_type=OrganType.TENTACLE,
            face_dir=_DIRS[channel_idx - 2],
        )
    if 6 <= channel_idx <= 9:
        return ActionSpec(
            is_wait=False,
            target=target,
            organ_type=OrganType.HARVESTER,
            face_dir=_DIRS[channel_idx - 6],
        )
    return ActionSpec(
        is_wait=False,
        target=target,
        organ_type=OrganType.SPORER,
        face_dir=_DIRS[channel_idx - 10],
    )


def _storage_vec_for_player(game: Game, player_idx: int) -> np.ndarray:
    p = game.players[player_idx]
    return np.asarray(
        [
            float(p.storage[Protein.A]),
            float(p.storage[Protein.B]),
            float(p.storage[Protein.C]),
            float(p.storage[Protein.D]),
        ],
        dtype=np.float32,
    )


def _can_afford(storage: np.ndarray, organ_type: OrganType) -> bool:
    cost = np.asarray(organ_type.cost, dtype=np.float32)
    return bool(np.all(storage >= cost))


def _growth_dir_from_parent_to_target(parent: Coord, target: Coord) -> Optional[Direction]:
    dx = target.x - parent.x
    dy = target.y - parent.y
    if dx == 0 and dy == -1:
        return Direction.NORTH
    if dx == 1 and dy == 0:
        return Direction.EAST
    if dx == 0 and dy == 1:
        return Direction.SOUTH
    if dx == -1 and dy == 0:
        return Direction.WEST
    return None


def _slot_action_from_grow(organ_type: OrganType, growth_dir: Direction, face_dir: Direction) -> int:
    type_idx = _ORG_TYPE_TO_SLOT_IDX[organ_type]
    return 1 + growth_dir.to_index() * 16 + face_dir.to_index() * 4 + type_idx


def _slot_action_from_spore_dir(spore_dir: Direction) -> int:
    return 65 + spore_dir.to_index()


def _iter_slot_roots(game: Game, player_idx: int) -> Iterable[tuple[int, int]]:
    roots = game.players[player_idx].roots
    for slot, root in enumerate(roots[:MAX_ROOTS]):
        yield slot, game._get_root_id(root)


def _valid_target_with_state(game: Game, player_idx: int, target: Coord, state: IterativeMaskState) -> bool:
    if target in state.blocked_targets:
        return False
    player = game.players[player_idx]
    return bool(game._valid_growth_target(player, target))


def choose_slot_action_for_action(
    game: Game,
    player_idx: int,
    action_index: int,
    state: Optional[IterativeMaskState] = None,
) -> Optional[SlotActionChoice]:
    """Map one paper action index to one executable slot action.

    Returns None when the action cannot be executed in the current state.
    """
    decoded = _decode_action_index(int(action_index))
    if decoded.is_wait:
        return None

    if state is None:
        state = IterativeMaskState(
            remaining_storage=_storage_vec_for_player(game, player_idx),
            used_slots=frozenset(),
            blocked_targets=frozenset(),
        )

    if decoded.target is None or decoded.organ_type is None:
        return None

    storage = state.remaining_storage
    if not _can_afford(storage, decoded.organ_type):
        return None

    player = game.players[player_idx]

    if decoded.organ_type == OrganType.ROOT:
        for slot, root_id in _iter_slot_roots(game, player_idx):
            if slot in state.used_slots:
                continue
            organs = game._organism_organs(root_id, player_idx)
            for organ in organs:
                if not organ.is_sporer():
                    continue
                target = game._spore_target(organ)
                if target is None or target != decoded.target:
                    continue
                if not _valid_target_with_state(game, player_idx, target, state):
                    continue
                return SlotActionChoice(
                    slot=slot,
                    action_int=_slot_action_from_spore_dir(organ.direction),
                    target=target,
                    organ_type=decoded.organ_type,
                )
        return None

    for slot, root_id in _iter_slot_roots(game, player_idx):
        if slot in state.used_slots:
            continue
        organs = game._organism_organs(root_id, player_idx)
        for organ in organs:
            if organ.pos is None:
                continue
            growth_dir = _growth_dir_from_parent_to_target(organ.pos, decoded.target)
            if growth_dir is None:
                continue
            if not _valid_target_with_state(game, player_idx, decoded.target, state):
                continue
            if not player.can_afford(decoded.organ_type):
                continue
            return SlotActionChoice(
                slot=slot,
                action_int=_slot_action_from_grow(decoded.organ_type, growth_dir, decoded.face_dir or Direction.NORTH),
                target=decoded.target,
                organ_type=decoded.organ_type,
            )

    return None


def discrete_action_to_slot_actions(game: Game, player_idx: int, action_index: int) -> np.ndarray:
    """Convert one Discrete(4033) action to engine MultiDiscrete slot actions."""
    out = np.zeros((MAX_ROOTS,), dtype=np.int64)
    choice = choose_slot_action_for_action(game, player_idx, int(action_index))
    if choice is None:
        return out
    out[choice.slot] = int(choice.action_int)
    return out


def build_action_mask(
    game: Game,
    player_idx: int,
    state: Optional[IterativeMaskState] = None,
) -> np.ndarray:
    """Build a legal-action mask for the 4033 paper action space."""
    if state is None:
        state = IterativeMaskState(
            remaining_storage=_storage_vec_for_player(game, player_idx),
            used_slots=frozenset(),
            blocked_targets=frozenset(),
        )

    mask = np.zeros((N_ACTIONS,), dtype=bool)
    mask[WAIT_ACTION_INDEX] = True

    # Enumerate legal indices by searching executable actions from each organism.
    roots = game.players[player_idx].roots[:MAX_ROOTS]
    for slot, root in enumerate(roots):
        if slot in state.used_slots:
            continue
        root_id = game._get_root_id(root)
        organs = game._organism_organs(root_id, player_idx)

        for organ in organs:
            if organ.pos is None:
                continue

            for growth_dir in _DIRS:
                target = organ.pos.add(growth_dir.coord)
                if not _valid_target_with_state(game, player_idx, target, state):
                    continue

                # BASIC (channel 1)
                if _can_afford(state.remaining_storage, OrganType.BASIC):
                    mask[_action_index_from_channel_and_coord(1, target)] = True

                # TENTACLE (channels 2..5)
                if _can_afford(state.remaining_storage, OrganType.TENTACLE):
                    for d_idx in range(4):
                        mask[_action_index_from_channel_and_coord(2 + d_idx, target)] = True

                # HARVESTER (channels 6..9)
                if _can_afford(state.remaining_storage, OrganType.HARVESTER):
                    for d_idx in range(4):
                        mask[_action_index_from_channel_and_coord(6 + d_idx, target)] = True

                # SPORER (channels 10..13)
                if _can_afford(state.remaining_storage, OrganType.SPORER):
                    for d_idx in range(4):
                        mask[_action_index_from_channel_and_coord(10 + d_idx, target)] = True

            if organ.is_sporer() and _can_afford(state.remaining_storage, OrganType.ROOT):
                spore_target = game._spore_target(organ)
                if spore_target is not None and _valid_target_with_state(game, player_idx, spore_target, state):
                    mask[_action_index_from_channel_and_coord(0, spore_target)] = True

    return mask


def iterative_policy_masking_to_slot_actions(
    game: Game,
    player_idx: int,
    policy_logits: np.ndarray,
) -> np.ndarray:
    """Convert one 4033-logit policy into per-root actions.

    The same policy is reused while progressively masking unavailable actions:
    - one action per root at most,
    - costs deducted from temporary storage,
    - already targeted cells are blocked for subsequent picks,
    - stops when WAIT is selected or no non-WAIT actions remain.
    """
    logits = np.asarray(policy_logits, dtype=np.float32).reshape(-1)
    if logits.shape[0] != N_ACTIONS:
        raise ValueError(f"Expected {N_ACTIONS} logits, got {logits.shape[0]}.")

    selected = np.zeros((MAX_ROOTS,), dtype=np.int64)
    state = IterativeMaskState(
        remaining_storage=_storage_vec_for_player(game, player_idx),
        used_slots=frozenset(),
        blocked_targets=frozenset(),
    )

    for _ in range(MAX_ROOTS):
        mask = build_action_mask(game, player_idx, state)
        non_wait = mask.copy()
        non_wait[WAIT_ACTION_INDEX] = False
        if not bool(np.any(non_wait)):
            break

        masked = np.where(mask, logits, -np.inf)
        action_idx = int(np.argmax(masked))
        if action_idx == WAIT_ACTION_INDEX:
            break

        choice = choose_slot_action_for_action(
            game=game,
            player_idx=player_idx,
            action_index=action_idx,
            state=state,
        )
        if choice is None:
            # In case of decode mismatch, prevent selecting this index again.
            logits[action_idx] = -np.inf
            continue

        selected[choice.slot] = int(choice.action_int)
        new_storage = state.remaining_storage - np.asarray(choice.organ_type.cost, dtype=np.float32)
        new_used = set(state.used_slots)
        new_used.add(choice.slot)
        new_blocked = set(state.blocked_targets)
        if choice.target is not None:
            new_blocked.add(choice.target)
        state = IterativeMaskState(
            remaining_storage=new_storage,
            used_slots=frozenset(new_used),
            blocked_targets=frozenset(new_blocked),
        )

    return selected
