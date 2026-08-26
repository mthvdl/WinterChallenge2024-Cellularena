"""DQN-specific Cellularena observation features."""
from __future__ import annotations

from typing import Any

from Games.cellularena.ray.sac.feature_builder import encode_observation


class DQNFeatureBuilder:
    """DQN feature extension point using the current canonical encoding."""

    def build(self, raw_observation: Any) -> Any:
        return encode_observation(raw_observation)
