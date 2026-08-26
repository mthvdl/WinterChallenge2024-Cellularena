"""Generic action-mask contract for discrete RL algorithms."""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import torch


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


def mask_logits(logits: torch.Tensor, action_mask: torch.Tensor) -> torch.Tensor:
    """Disable illegal categorical actions before sampling or loss calculation."""
    if logits.shape[-1] != action_mask.shape[-1]:
        raise ValueError(
            f"Logit/action-mask dimensions differ: {logits.shape[-1]} != "
            f"{action_mask.shape[-1]}"
        )
    valid = action_mask.to(device=logits.device, dtype=torch.bool)
    if not torch.all(valid.any(dim=-1)):
        raise ValueError("Every action mask row must contain at least one legal action.")
    return logits.masked_fill(~valid, float("-inf"))


def mask_action_dist_inputs(batch: Dict[str, Any], outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the structured observation mask to RLlib distribution inputs."""
    from ray.rllib.core.columns import Columns

    logits = outputs.get(Columns.ACTION_DIST_INPUTS)
    if logits is None:
        return outputs
    observation = batch[Columns.OBS]
    outputs[Columns.ACTION_DIST_INPUTS] = mask_logits(
        logits, observation[ACTION_MASK_KEY]
    )
    return outputs


class ActionMaskingRLModuleMixin:
    """Reusable hook for discrete DQN/SAC RLModules."""

    @staticmethod
    def mask_action_dist_inputs(batch: Dict[str, Any], outputs: Dict[str, Any]) -> Dict[str, Any]:
        return mask_action_dist_inputs(batch, outputs)