"""Cellularena action-mask customisation."""
from __future__ import annotations

import numpy as np
from Games.cellularena.engine.action_adapter import N_ACTIONS, build_action_mask
from Games.cellularena.engine.game import Game
from Core.action_mask import mask_logits


class ActionMaskBuilder:
    """Build legal masks for the discrete paper action space."""

    action_count = N_ACTIONS

    def build(self, game: Game, player_idx: int) -> np.ndarray:
        return build_action_mask(game, player_idx).astype(np.float32, copy=False)



__all__ = ["ActionMaskBuilder", "mask_logits"]
