"""Cellularena observation feature builders.

This module centralizes the mapping from raw game observations to agent-facing
features so the same logic can be reused across:
- online training environments,
- offline replay prefill, and
- CodinGame runtime game loops.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List

import numpy as np
from gymnasium import spaces

from Games.cellularena.engine.game import MAX_H, MAX_W, N_CHANNELS


def flatten_obs_dict(obs: Dict[str, np.ndarray]) -> np.ndarray:
    """Flatten a dict observation using the same key order as Rainbow networks.

    Rainbow sorts observation keys lexicographically before flattening each
    tensor. Reusing the same order at CodinGame inference time guarantees
    train/inference parity.
    """
    parts: List[np.ndarray] = []
    for key in sorted(obs.keys()):
        parts.append(np.asarray(obs[key], dtype=np.float32).ravel())
    if not parts:
        return np.zeros((0,), dtype=np.float32)
    return np.concatenate(parts, axis=0)


class TemporalObservationBuilder:
    """Build stacked temporal observations from per-turn raw game observations.

    Parameters
    ----------
    history_steps:
        Number of recent frames to expose. Must be >= 1.

    Startup behavior
    ----------------
    When fewer than ``history_steps`` frames are available (early turns), the
    oldest available frame is duplicated to the left. This makes the output
    shape constant without introducing synthetic zeros.
    """

    def __init__(self, history_steps: int = 1) -> None:
        history_steps = int(history_steps)
        if history_steps < 1:
            raise ValueError("history_steps must be >= 1")

        self.history_steps = history_steps
        self._grid_history: Dict[int, Deque[np.ndarray]] = {}

    @property
    def grid_channels(self) -> int:
        return N_CHANNELS * self.history_steps

    def observation_space(self) -> spaces.Dict:
        return spaces.Dict(
            {
                "grid": spaces.Box(
                    low=0.0,
                    high=1.0,
                    shape=(MAX_H, MAX_W, self.grid_channels),
                    dtype=np.float32,
                ),
                "storage": spaces.Box(
                    low=0.0,
                    high=1.0,
                    shape=(2, 4),
                    dtype=np.float32,
                ),
                "turn": spaces.Box(
                    low=0.0,
                    high=1.0,
                    shape=(1,),
                    dtype=np.float32,
                ),
            }
        )

    def reset(self) -> None:
        self._grid_history = {}

    def transform(self, player_idx: int, raw_obs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        grid = np.asarray(raw_obs["grid"], dtype=np.float32)
        storage = np.asarray(raw_obs["storage"], dtype=np.float32)
        turn = np.asarray(raw_obs["turn"], dtype=np.float32)

        history = self._grid_history.get(player_idx)
        if history is None:
            history = deque(maxlen=self.history_steps)
            self._grid_history[player_idx] = history
        history.append(grid.copy())

        frames = list(history)
        while len(frames) < self.history_steps:
            # Duplicate the oldest available frame for early turns.
            frames.insert(0, frames[0])

        stacked = np.concatenate(frames, axis=2)

        return {
            "grid": stacked.astype(np.float32, copy=False),
            "storage": storage.astype(np.float32, copy=True),
            "turn": turn.astype(np.float32, copy=True),
        }
