"""Cellularena action-mask customisation."""
from __future__ import annotations

import numpy as np
from Games.cellularena.engine.action_adapter import (
    N_ACTIONS,
    build_action_mask,
    transform_action_mask,
)
from Games.cellularena.engine.game import Game


class ActionMaskBuilder:
    """Build legal masks for the discrete paper action space."""

    action_count = N_ACTIONS

    def build(self, game: Game, player_idx: int, action_count: int) -> np.ndarray:
        if action_count != self.action_count:
            raise ValueError(f"Expected {self.action_count} actions, got {action_count}.")
        return transform_action_mask(
            build_action_mask(game, player_idx), player_idx
        ).astype(np.float32, copy=False)



__all__ = ["ActionMaskBuilder"]
