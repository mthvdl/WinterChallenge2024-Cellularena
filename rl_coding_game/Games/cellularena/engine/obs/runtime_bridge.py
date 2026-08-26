"""Runtime bridge for protocol-faithful Cellularena inference loops."""

from __future__ import annotations

import numpy as np

from Games.cellularena.engine.action_adapter import iterative_policy_masking_to_slot_actions
from Games.cellularena.engine.game import Game


class IterativeActionRuntime:
    """Convert one paper policy logit vector into per-root engine actions."""

    def build_joint_action(
        self,
        game: Game,
        player_idx: int,
        policy_logits: np.ndarray,
    ) -> np.ndarray:
        return iterative_policy_masking_to_slot_actions(
            game=game,
            player_idx=player_idx,
            policy_logits=policy_logits,
        )
