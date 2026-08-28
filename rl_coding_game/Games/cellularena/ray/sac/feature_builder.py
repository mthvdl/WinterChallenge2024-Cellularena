"""SAC-specific Cellularena observation features."""
from __future__ import annotations

from typing import Any

import numpy as np
from gymnasium import spaces

from Games.cellularena.engine.obs.paper_features import (
    FEATURE_DIM,
    MAX_H,
    MAX_W,
    N_CHANNELS,
    encode_observation,
)

__all__ = [
    "FEATURE_DIM",
    "MAX_H",
    "MAX_W",
    "N_CHANNELS",
    "encode_observation",
    "SACFeatureBuilder",
]


class SACFeatureBuilder:
    """Build SAC's customizable fixed-size feature vector."""

    def __init__(self, history_steps: int = 1) -> None:
        self.history_steps = int(history_steps)
        if self.history_steps < 1:
            raise ValueError("history_steps must be >= 1")
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(MAX_H, MAX_W, N_CHANNELS * self.history_steps),
            dtype=np.float32,
        )

    def build(self, raw_observation: dict[str, Any]) -> np.ndarray:
        return encode_observation(raw_observation, self.history_steps).reshape(
            MAX_H, MAX_W, N_CHANNELS * self.history_steps
        )
