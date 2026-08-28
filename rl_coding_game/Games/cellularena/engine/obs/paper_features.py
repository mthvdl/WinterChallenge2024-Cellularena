"""Paper-style 12x24x93 observation encoding, shared across algorithms."""
from __future__ import annotations

from typing import Any

import numpy as np

MAX_H = 12
MAX_W = 24
N_CHANNELS = 93
FEATURE_DIM = MAX_H * MAX_W * N_CHANNELS

_BASE_EMPTY = 0
_BASE_WALL = 1
_BASE_PROTEIN = 2
_SELF_ORG = 6
_OPP_ORG = 20
_SELF_BLOCK = 34
_OPP_BLOCK = 63
_PROTEINS = slice(1, 5)
_P0_ORG = slice(5, 10)
_P1_ORG = slice(10, 15)
_P0_DIR = 15
_P1_DIR = 16
_ORGAN_OFFSETS = (0, 1, 2, 6, 10)
_COSTS = np.asarray(
    ((1, 1, 1, 1), (1, 0, 0, 0), (0, 1, 1, 0), (0, 0, 1, 1), (0, 1, 0, 1)),
    dtype=np.float32,
)
_MIRROR_DIR = np.asarray((0, 3, 2, 1), dtype=np.int64)


def _directions(values: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(values * 3.0), 0, 3).astype(np.int64)


def _next_cell(x: int, y: int, direction: int) -> tuple[int, int]:
    dx, dy = ((0, -1), (1, 0), (0, 1), (-1, 0))[direction]
    return x + dx, y + dy


def encode_observation(observation: dict[str, Any]) -> np.ndarray:
    """Convert compact game state into the paper-style 12x24x93 vector."""
    grid = np.asarray(observation["grid"], dtype=np.float32)
    if grid.ndim != 3 or grid.shape[0] < MAX_H or grid.shape[1] < MAX_W or grid.shape[2] < 17:
        raise ValueError(f"Expected grid at least (12, 24, 17); got {grid.shape}.")
    grid = grid[:MAX_H, :MAX_W, -17:].copy()
    if "storage" not in observation or "self_player_idx" not in observation:
        raise ValueError("Observation is missing required 'storage'/'self_player_idx' keys.")
    storage = np.asarray(observation["storage"], dtype=np.float32)
    self_index = int(np.asarray(observation["self_player_idx"]).reshape(-1)[0])
    self_index = max(0, min(self_index, 1))
    if self_index == 1:
        grid = grid[:, ::-1].copy()
        for channel in (_P0_DIR, _P1_DIR):
            grid[:, :, channel] = _MIRROR_DIR[_directions(grid[:, :, channel])] / 3.0
        storage = storage[[1, 0]]

    features = np.zeros((MAX_H, MAX_W, N_CHANNELS), dtype=np.float32)
    direction_maps = (_directions(grid[:, :, _P0_DIR]), _directions(grid[:, :, _P1_DIR]))
    for y in range(MAX_H):
        for x in range(MAX_W):
            cell = grid[y, x]
            if cell[0] > 0.5:
                features[y, x, _BASE_WALL] = 1.0
                continue
            protein = cell[_PROTEINS]
            if protein.max() > 0.5:
                features[y, x, _BASE_PROTEIN + int(protein.argmax())] = 1.0
                continue
            for player, organ_slice in enumerate((_P0_ORG, _P1_ORG)):
                organs = cell[organ_slice]
                if organs.max() <= 0.5:
                    continue
                organ = int(organs.argmax())
                base = _SELF_ORG if player == self_index else _OPP_ORG
                offset = _ORGAN_OFFSETS[organ]
                channel = base + offset
                if organ >= 2:
                    channel += int(direction_maps[player][y, x])
                features[y, x, channel] = 1.0
                break
            else:
                features[y, x, _BASE_EMPTY] = 1.0

    scaled_storage = np.clip(storage, 0.0, 1.0)
    income = np.zeros((2, 4), dtype=np.float32)
    for player, (organ_start, direction_map) in enumerate(((5, direction_maps[0]), (10, direction_maps[1]))):
        for y in range(MAX_H):
            for x in range(MAX_W):
                if grid[y, x, organ_start + 3] <= 0.5:
                    continue
                tx, ty = _next_cell(x, y, int(direction_map[y, x]))
                if 0 <= tx < MAX_W and 0 <= ty < MAX_H:
                    target = grid[ty, tx, _PROTEINS]
                    if target.max() > 0.5:
                        income[player, int(target.argmax())] += 1.0
    if self_index == 1:
        income = income[[1, 0]]

    target = features[:, :, _BASE_EMPTY] > 0.5
    target |= features[:, :, _BASE_PROTEIN:_BASE_PROTEIN + 4].any(axis=2)
    for player, block in ((0, _SELF_BLOCK), (1, _OPP_BLOCK)):
        base = _SELF_ORG if player == self_index else _OPP_ORG
        features[:, :, block + 18:block + 22] = scaled_storage[player]
        features[:, :, block + 22:block + 26] = income[player]
        features[:, :, block + 27] = features[:, :, base:base + 14].sum()
        features[:, :, block + 28] = scaled_storage[player].sum()
        affordable = np.all(scaled_storage[player, None] >= _COSTS, axis=1)
        for organ, offset in enumerate(_ORGAN_OFFSETS):
            if affordable[organ]:
                width = 1 if organ < 2 else 4
                features[:, :, block + 4 + offset:block + 4 + offset + width] = target[:, :, None]

    features[:, :, 92] = np.clip(
        float(np.asarray(observation.get("turn", 0)).reshape(-1)[0]), 0.0, 1.0
    )
    return features.reshape(-1)
