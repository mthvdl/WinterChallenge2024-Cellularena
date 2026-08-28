"""DQN-specific Cellularena observation features."""
from __future__ import annotations

from typing import Any

from Games.cellularena.engine.obs.paper_features import FEATURE_DIM, encode_observation
from gymnasium import spaces


class DQNFeatureBuilder:
    """DQN feature extension point using the current canonical encoding."""

    def __init__(self, history_steps: int = 1) -> None:
        self.history_steps = int(history_steps)
        if self.history_steps < 1:
            raise ValueError("history_steps must be >= 1")
        self.observation_space = spaces.Box(
            low=-float("inf"),
            high=float("inf"),
            shape=(FEATURE_DIM * self.history_steps,),
            dtype="float32",
        )

    def build(self, raw_observation: Any) -> Any:
        return encode_observation(raw_observation, self.history_steps)
