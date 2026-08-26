"""Runtime bridge for protocol-faithful Cellularena inference loops."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import torch

from Games.cellularena.bots.action_adapter import iterative_policy_masking_to_slot_actions
from Games.cellularena.bots.obs_mapper import CellularenaObsMapper
from Games.cellularena.engine.game import Game


class CodingameObsRuntime:
    """Protocol observation -> mapped flat tensor runtime helper."""

    def __init__(self, obs_mapper: CellularenaObsMapper | None = None) -> None:
        self._mapper = obs_mapper if obs_mapper is not None else CellularenaObsMapper()
        self._device = torch.device("cpu")

    def reset(self) -> None:
        return None

    def build_flat(self, raw_obs: Dict[str, Any]) -> np.ndarray:
        flat = self._mapper.obs_to_tensor(raw_obs, self._device)
        return flat.detach().cpu().numpy()


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
