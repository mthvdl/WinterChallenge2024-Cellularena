"""DQN env-to-module preprocessor for Cellularena."""
from __future__ import annotations

from typing import Any

import numpy as np
from gymnasium import spaces

from Core.ray_connectors import FeaturePreprocessor
from Games.cellularena.engine.obs.paper_features import FEATURE_DIM, encode_observation


class DQNPreprocessor(FeaturePreprocessor):
    """Encode raw observations into one flat vector with the action mask appended."""

    flatten = True

    def __init__(
        self,
        input_observation_space: spaces.Space | None = None,
        input_action_space: spaces.Space | None = None,
        history_steps: int = 1,
        **kwargs: Any,
    ) -> None:
        self.history_steps = int(history_steps)
        if self.history_steps < 1:
            raise ValueError("history_steps must be >= 1")
        super().__init__(input_observation_space, input_action_space, **kwargs)

    def feature_space(self, raw_space: spaces.Dict) -> spaces.Box:
        return spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(FEATURE_DIM * self.history_steps,),
            dtype=np.float32,
        )

    def build_features(self, raw_observation: dict[str, Any]) -> np.ndarray:
        return encode_observation(raw_observation, self.history_steps)
