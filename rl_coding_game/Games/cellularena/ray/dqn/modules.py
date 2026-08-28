"""DQN network customization hooks for Cellularena."""
from __future__ import annotations

from typing import Any

import torch
from ray.rllib.algorithms.dqn import DQNConfig
from ray.rllib.algorithms.dqn.default_dqn_rl_module import QF_PREDS
from ray.rllib.algorithms.dqn.torch.default_dqn_torch_rl_module import DefaultDQNTorchRLModule
from ray.rllib.core.columns import Columns


class DQNNetwork:
    """Base hook for changing RLlib Rainbow DQN's network."""

    def customize(self, config: DQNConfig) -> DQNConfig:
        # Uncomment this block to configure the shared DQN encoder and head.
        # return config.training(
        #     model={
        #         "fcnet_hiddens": [512, 256],
        #         "fcnet_activation": "relu",
        #         "post_fcnet_hiddens": [256],
        #     },
        # )
        return config


class MaskedDQNTorchRLModule(DefaultDQNTorchRLModule):
    """New-stack DQN module that masks the action tail in flattened observations."""

    @staticmethod
    def apply_action_mask(q_values: torch.Tensor, action_mask: torch.Tensor) -> torch.Tensor:
        valid = action_mask > 0.0
        has_valid = valid.any(dim=-1, keepdim=True)
        valid = torch.where(has_valid, valid, torch.ones_like(valid))
        return q_values.masked_fill(~valid, torch.finfo(q_values.dtype).min)

    def compute_q_values(self, batch: dict[str, Any]):
        outputs = super().compute_q_values(batch)
        mask = batch[Columns.OBS][..., -self.action_space.n :]
        outputs[QF_PREDS] = self.apply_action_mask(outputs[QF_PREDS], mask)
        return outputs