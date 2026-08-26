"""Cellularena paper-inspired observation mapper for PPO.

This mapper consumes the compact PettingZoo observation used by the local
Cellularena env and expands it into a fixed 12x24x93 tensor inspired by
reCurse's Winter Challenge 2024 feature layout.

Because the env observation does not expose full organ parent graphs, this is a
best-effort mapping:
- parent-direction and criticality channels are left at zero,
- grow-availability channels are approximated from empty/protein targets,
- incomes are derived from visible harvesters and front cells.
"""
from __future__ import annotations

from typing import Any, Tuple

import numpy as np
import torch
from gymnasium import spaces

from Core.obs_mapper import ObsMapper

MAX_H = 12
MAX_W = 24
N_CHANNELS = 93
FLAT_DIM = MAX_H * MAX_W * N_CHANNELS

_BASE_EMPTY = 0
_BASE_WALL = 1
_BASE_A = 2
_BASE_B = 3
_BASE_C = 4
_BASE_D = 5
_SELF_ORG_BASE = 6
_OPP_ORG_BASE = 20

_SELF_BLOCK = 34
_OPP_BLOCK = 63

# Compact env channels (single frame).
C_OBS = 0
C_PROT_A = 1
C_PROT_B = 2
C_PROT_C = 3
C_PROT_D = 4
C_P0_ROOT = 5
C_P0_BASIC = 6
C_P0_TENT = 7
C_P0_HARV = 8
C_P0_SPOR = 9
C_P1_ROOT = 10
C_P1_BASIC = 11
C_P1_TENT = 12
C_P1_HARV = 13
C_P1_SPOR = 14
C_P0_DIR = 15
C_P1_DIR = 16

_ORG_OFFSETS = {
    "ROOT": 0,
    "BASIC": 1,
    "TENTACLE": 2,
    "HARVESTER": 6,
    "SPORER": 10,
}

_ORGAN_COSTS = {
    "ROOT": np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32),
    "BASIC": np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
    "TENTACLE": np.array([0.0, 1.0, 1.0, 0.0], dtype=np.float32),
    "HARVESTER": np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32),
    "SPORER": np.array([0.0, 1.0, 0.0, 1.0], dtype=np.float32),
}

# 180-degree rotation (N<->S, E<->W).
_MIRROR_DIR = np.array([2, 3, 0, 1], dtype=np.int64)


def _clip_index(v: int, hi: int) -> int:
    return max(0, min(int(v), hi))


def _as_scalar_int(v: Any, default: int = 0) -> int:
    if v is None:
        return int(default)
    arr = np.asarray(v)
    if arr.size == 0:
        return int(default)
    return int(arr.reshape(-1)[0])


def _decode_dir(norm: np.ndarray) -> np.ndarray:
    idx = np.rint(np.asarray(norm, dtype=np.float32) * 3.0).astype(np.int64)
    return np.clip(idx, 0, 3)


def _can_afford(storage4: np.ndarray, organ_type: str) -> bool:
    return bool(np.all(storage4 >= _ORGAN_COSTS[organ_type]))


class CellularenaObsMapper(ObsMapper):
    """Build a flattened paper-style 93-channel map from env observations."""

    def __init__(self, default_self_player_idx: int = 0, mirror_player_1: bool = True) -> None:
        self.default_self_player_idx = int(default_self_player_idx)
        self.mirror_player_1 = bool(mirror_player_1)

    @staticmethod
    def _latest_grid(grid: np.ndarray) -> np.ndarray:
        g = np.asarray(grid, dtype=np.float32)
        if g.ndim != 3:
            raise ValueError(f"Expected grid with 3 dims (H,W,C); got shape {g.shape}.")
        if g.shape[0] < MAX_H or g.shape[1] < MAX_W or g.shape[2] < 17:
            raise ValueError(f"Expected grid at least (12,24,17); got {g.shape}.")
        # If temporal stacking is enabled, keep the most recent frame.
        return g[:MAX_H, :MAX_W, -17:]

    @staticmethod
    def _mirror_grid_and_dirs(grid17: np.ndarray) -> np.ndarray:
        out = grid17[::-1, ::-1, :].copy()
        d0 = _decode_dir(out[:, :, C_P0_DIR])
        d1 = _decode_dir(out[:, :, C_P1_DIR])
        out[:, :, C_P0_DIR] = (_MIRROR_DIR[d0] / 3.0).astype(np.float32)
        out[:, :, C_P1_DIR] = (_MIRROR_DIR[d1] / 3.0).astype(np.float32)
        return out

    @staticmethod
    def _mark_org_channel(dst: np.ndarray, y: int, x: int, base: int, organ_name: str, d: int) -> None:
        offset = _ORG_OFFSETS[organ_name]
        if organ_name in {"ROOT", "BASIC"}:
            dst[y, x, base + offset] = 1.0
        else:
            dst[y, x, base + offset + d] = 1.0

    @staticmethod
    def _next_xy(x: int, y: int, d: int) -> Tuple[int, int]:
        if d == 0:
            return x, y - 1
        if d == 1:
            return x + 1, y
        if d == 2:
            return x, y + 1
        return x - 1, y

    def _build_from_compact(self, obs: dict[str, Any]) -> np.ndarray:
        grid17 = self._latest_grid(obs["grid"])
        storage = np.asarray(obs.get("storage", np.zeros((2, 4), dtype=np.float32)), dtype=np.float32)
        turn = float(np.asarray(obs.get("turn", np.zeros((1,), dtype=np.float32)), dtype=np.float32).reshape(-1)[0])

        self_idx = _clip_index(_as_scalar_int(obs.get("self_player_idx", self.default_self_player_idx)), 1)
        opp_idx = 1 - self_idx

        if self_idx == 1 and self.mirror_player_1:
            grid17 = self._mirror_grid_and_dirs(grid17)
            storage = storage[[1, 0], :]

        out = np.zeros((MAX_H, MAX_W, N_CHANNELS), dtype=np.float32)

        p0_dir = _decode_dir(grid17[:, :, C_P0_DIR])
        p1_dir = _decode_dir(grid17[:, :, C_P1_DIR])

        for y in range(MAX_H):
            for x in range(MAX_W):
                cell = grid17[y, x]

                if cell[C_OBS] > 0.5:
                    out[y, x, _BASE_WALL] = 1.0
                    continue
                if cell[C_PROT_A] > 0.5:
                    out[y, x, _BASE_A] = 1.0
                    continue
                if cell[C_PROT_B] > 0.5:
                    out[y, x, _BASE_B] = 1.0
                    continue
                if cell[C_PROT_C] > 0.5:
                    out[y, x, _BASE_C] = 1.0
                    continue
                if cell[C_PROT_D] > 0.5:
                    out[y, x, _BASE_D] = 1.0
                    continue

                p0_org = cell[C_P0_ROOT:C_P0_SPOR + 1]
                p1_org = cell[C_P1_ROOT:C_P1_SPOR + 1]

                if float(np.max(p0_org)) > 0.5:
                    t = int(np.argmax(p0_org))
                    owner_is_self = self_idx == 0
                    base = _SELF_ORG_BASE if owner_is_self else _OPP_ORG_BASE
                    d = int(p0_dir[y, x])
                    if t == 0:
                        self._mark_org_channel(out, y, x, base, "ROOT", d)
                    elif t == 1:
                        self._mark_org_channel(out, y, x, base, "BASIC", d)
                    elif t == 2:
                        self._mark_org_channel(out, y, x, base, "TENTACLE", d)
                    elif t == 3:
                        self._mark_org_channel(out, y, x, base, "HARVESTER", d)
                    else:
                        self._mark_org_channel(out, y, x, base, "SPORER", d)
                    continue

                if float(np.max(p1_org)) > 0.5:
                    t = int(np.argmax(p1_org))
                    owner_is_self = self_idx == 1
                    base = _SELF_ORG_BASE if owner_is_self else _OPP_ORG_BASE
                    d = int(p1_dir[y, x])
                    if t == 0:
                        self._mark_org_channel(out, y, x, base, "ROOT", d)
                    elif t == 1:
                        self._mark_org_channel(out, y, x, base, "BASIC", d)
                    elif t == 2:
                        self._mark_org_channel(out, y, x, base, "TENTACLE", d)
                    elif t == 3:
                        self._mark_org_channel(out, y, x, base, "HARVESTER", d)
                    else:
                        self._mark_org_channel(out, y, x, base, "SPORER", d)
                    continue

                out[y, x, _BASE_EMPTY] = 1.0

        # Scalars per player.
        self_storage = np.clip(storage[0] * 50.0, 0.0, 99.0)
        opp_storage = np.clip(storage[1] * 50.0, 0.0, 99.0)

        # Approximate scores from visible organ counts.
        self_score = float(np.sum(out[:, :, _SELF_ORG_BASE:_SELF_ORG_BASE + 14]))
        opp_score = float(np.sum(out[:, :, _OPP_ORG_BASE:_OPP_ORG_BASE + 14]))
        self_tiebreak = float(np.sum(self_storage))
        opp_tiebreak = float(np.sum(opp_storage))

        # Approximate incomes from visible harvesters facing proteins.
        self_income = np.zeros((4,), dtype=np.float32)
        opp_income = np.zeros((4,), dtype=np.float32)

        def _acc_income(owner_self: bool, dmap: np.ndarray, ch_start: int, income: np.ndarray) -> None:
            for yy in range(MAX_H):
                for xx in range(MAX_W):
                    if grid17[yy, xx, ch_start + 3] <= 0.5:
                        continue
                    tx, ty = self._next_xy(xx, yy, int(dmap[yy, xx]))
                    if 0 <= tx < MAX_W and 0 <= ty < MAX_H:
                        p = grid17[ty, tx, C_PROT_A:C_PROT_D + 1]
                        if float(np.max(p)) > 0.5:
                            income[int(np.argmax(p))] += 1.0

        _acc_income(True, p0_dir if self_idx == 0 else p1_dir, C_P0_ROOT if self_idx == 0 else C_P1_ROOT, self_income)
        _acc_income(False, p1_dir if self_idx == 0 else p0_dir, C_P1_ROOT if self_idx == 0 else C_P0_ROOT, opp_income)

        # Parent-dir and criticality channels are unavailable from compact obs.
        out[:, :, _SELF_BLOCK + 18:_SELF_BLOCK + 22] = self_storage.reshape(1, 1, 4)
        out[:, :, _SELF_BLOCK + 22:_SELF_BLOCK + 26] = self_income.reshape(1, 1, 4)
        out[:, :, _SELF_BLOCK + 27] = self_score
        out[:, :, _SELF_BLOCK + 28] = self_tiebreak

        out[:, :, _OPP_BLOCK + 18:_OPP_BLOCK + 22] = opp_storage.reshape(1, 1, 4)
        out[:, :, _OPP_BLOCK + 22:_OPP_BLOCK + 26] = opp_income.reshape(1, 1, 4)
        out[:, :, _OPP_BLOCK + 27] = opp_score
        out[:, :, _OPP_BLOCK + 28] = opp_tiebreak

        # Approximate grow-availability channels from affordable types and target emptiness.
        self_grow_base = _SELF_BLOCK + 4
        opp_grow_base = _OPP_BLOCK + 4
        self_afford = {
            "ROOT": _can_afford(self_storage, "ROOT"),
            "BASIC": _can_afford(self_storage, "BASIC"),
            "TENTACLE": _can_afford(self_storage, "TENTACLE"),
            "HARVESTER": _can_afford(self_storage, "HARVESTER"),
            "SPORER": _can_afford(self_storage, "SPORER"),
        }
        opp_afford = {
            "ROOT": _can_afford(opp_storage, "ROOT"),
            "BASIC": _can_afford(opp_storage, "BASIC"),
            "TENTACLE": _can_afford(opp_storage, "TENTACLE"),
            "HARVESTER": _can_afford(opp_storage, "HARVESTER"),
            "SPORER": _can_afford(opp_storage, "SPORER"),
        }

        target_ok = (
            (out[:, :, _BASE_EMPTY] > 0.5)
            | (out[:, :, _BASE_A] > 0.5)
            | (out[:, :, _BASE_B] > 0.5)
            | (out[:, :, _BASE_C] > 0.5)
            | (out[:, :, _BASE_D] > 0.5)
        )

        for yy in range(MAX_H):
            for xx in range(MAX_W):
                if not target_ok[yy, xx]:
                    continue

                if self_afford["BASIC"]:
                    out[yy, xx, self_grow_base + 1] = 1.0
                if self_afford["ROOT"]:
                    out[yy, xx, self_grow_base + 0] = 1.0
                if self_afford["TENTACLE"]:
                    out[yy, xx, self_grow_base + 2:self_grow_base + 6] = 1.0
                if self_afford["HARVESTER"]:
                    out[yy, xx, self_grow_base + 6:self_grow_base + 10] = 1.0
                if self_afford["SPORER"]:
                    out[yy, xx, self_grow_base + 10:self_grow_base + 14] = 1.0

                if opp_afford["BASIC"]:
                    out[yy, xx, opp_grow_base + 1] = 1.0
                if opp_afford["ROOT"]:
                    out[yy, xx, opp_grow_base + 0] = 1.0
                if opp_afford["TENTACLE"]:
                    out[yy, xx, opp_grow_base + 2:opp_grow_base + 6] = 1.0
                if opp_afford["HARVESTER"]:
                    out[yy, xx, opp_grow_base + 6:opp_grow_base + 10] = 1.0
                if opp_afford["SPORER"]:
                    out[yy, xx, opp_grow_base + 10:opp_grow_base + 14] = 1.0

        out[:, :, 92] = turn * 100.0
        return out

    def obs_to_tensor(self, obs: Any, device: torch.device) -> torch.Tensor:
        if not isinstance(obs, dict):
            raise TypeError("CellularenaObsMapper expects a dict observation.")
        mapped = self._build_from_compact(obs)
        flat = mapped.reshape(-1)
        return torch.from_numpy(flat).to(device)

    def output_dim(self, obs_space: spaces.Space) -> int:
        del obs_space
        return FLAT_DIM
