"""Generic action-mask contract for discrete RL algorithms."""
from __future__ import annotations

from typing import Any

import numpy as np


OBSERVATIONS_KEY = "observations"
ACTION_MASK_KEY = "action_mask"


def full_action_mask(action_count: int, dtype: np.dtype = np.float32) -> np.ndarray:
    """Return the legal-action mask used by a new game before customisation."""
    if action_count <= 0:
        raise ValueError("action_count must be positive")
    return np.ones(action_count, dtype=dtype)


class ActionMaskBuilder:
    """Base mask builder; new games are valid with every action enabled."""

    def build(self, game: Any, player_idx: int, action_count: int) -> np.ndarray:
        del game, player_idx
        return full_action_mask(action_count)