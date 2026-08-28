"""SAC network customization hooks for Cellularena."""
from __future__ import annotations

import functools
from typing import Any

import torch
from gymnasium import spaces
from ray.rllib.algorithms.sac.sac_learner import (
    ACTION_LOG_PROBS,
    ACTION_LOG_PROBS_NEXT,
    ACTION_PROBS,
    ACTION_PROBS_NEXT,
    QF_PREDS,
    QF_TARGET_NEXT,
    QF_TWIN_PREDS,
)
from ray.rllib.algorithms.sac.sac_catalog import SACCatalog
from ray.rllib.algorithms.sac.torch.default_sac_torch_rl_module import DefaultSACTorchRLModule
from ray.rllib.core.models.base import ENCODER_OUT, Encoder
from ray.rllib.core.columns import Columns
from ray.rllib.core.models.configs import ModelConfig
from ray.rllib.core.models.torch.base import TorchModel
from ray.rllib.core.rl_module.rl_module import RLModuleSpec
from torch import nn

from ray.rllib.algorithms.sac import SACConfig
from Games.cellularena.engine.action_adapter import N_GROW_CHANNELS
from Games.cellularena.ray.sac.feature_builder import MAX_H, MAX_W, N_CHANNELS


def _orthogonal_init(module: nn.Module, gain: float) -> None:
    if isinstance(module, (nn.Conv2d, nn.Linear)):
        nn.init.orthogonal_(module.weight, gain=gain)
        if module.bias is not None:
            nn.init.zeros_(module.bias)


class SACNetwork:
    """No-op hook for customizing RLlib's current SAC RLModule stack."""

    def customize(self, config: SACConfig) -> SACConfig:
        return config


class _ResidualBlock(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(channels, channels, kernel_size=3, padding=1),
        )
        self.activation = nn.ReLU()
        _orthogonal_init(self.layers[0], gain=2**0.5)
        _orthogonal_init(self.layers[2], gain=1.0)
        nn.init.zeros_(self.layers[2].weight)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.activation(inputs + self.layers(inputs))


class _SpatialModelConfig(ModelConfig):
    def build(self, framework: str):
        raise NotImplementedError


class _SpatialHead(TorchModel):
    def __init__(self, config: ModelConfig, output_gain: float = 1.0) -> None:
        super().__init__(config)
        self.grow = nn.Conv2d(32, N_GROW_CHANNELS, kernel_size=1)
        self.wait = nn.Linear(32 * MAX_H * MAX_W, 1)
        _orthogonal_init(self.grow, gain=output_gain)
        _orthogonal_init(self.wait, gain=output_gain)

    def _forward(self, inputs: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        del kwargs
        grow_values = self.grow(inputs).flatten(1)
        wait_value = self.wait(inputs.flatten(1))
        return torch.cat((grow_values, wait_value), dim=1)


class _SpatialEncoder(TorchModel, Encoder):
    def __init__(self, input_channels: int = N_CHANNELS) -> None:
        config = _SpatialModelConfig(input_dims=(input_channels, MAX_H, MAX_W))
        TorchModel.__init__(self, config)
        Encoder.__init__(self, config)
        self.net = nn.Sequential(
            nn.Conv2d(input_channels, 32, kernel_size=1),
            nn.ReLU(),
            _ResidualBlock(32),
            _ResidualBlock(32),
            _ResidualBlock(32),
            _ResidualBlock(32),
        )
        # Each `_ResidualBlock` already initializes itself (identity residual);
        # only the stem conv needs an explicit init here.
        _orthogonal_init(self.net[0], gain=2**0.5)

    def _forward(self, input_dict: dict, **kwargs: Any) -> dict:
        del kwargs
        observations = input_dict[Columns.OBS]["observations"]
        if observations.ndim == 3:
            observations = observations.unsqueeze(0)
        embedding = self.net(observations.float().permute(0, 3, 1, 2))
        return {ENCODER_OUT: embedding}


class CellularenaSACCatalog(SACCatalog):
    """Native SAC catalog using the spatial CNN for policy and Q networks."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def _determine_components_hook(self) -> None:
        self._action_dist_class_fn = functools.partial(
            self._get_dist_cls_from_action_space,
            action_space=self.action_space,
        )
        self._latent_dims = (32, MAX_H, MAX_W)

    def build_encoder(self, framework: str) -> Encoder:
        assert framework == "torch"
        observation_space = self.observation_space
        if isinstance(observation_space, spaces.Dict):
            observation_space = observation_space["observations"]
        input_channels = observation_space.shape[-1]
        return _SpatialEncoder(input_channels)

    def build_pi_head(self, framework: str) -> TorchModel:
        assert framework == "torch"
        return _SpatialHead(_SpatialModelConfig(input_dims=self.latent_dims), output_gain=0.01)

    def build_qf_head(self, framework: str) -> TorchModel:
        assert framework == "torch"
        return _SpatialHead(_SpatialModelConfig(input_dims=self.latent_dims), output_gain=1.0)


class CNNSACNetwork(SACNetwork):
    """Use the spatial CNN through RLlib's current SAC RLModule stack."""

    def customize(self, config: SACConfig) -> SACConfig:
        return config.rl_module(
            rl_module_spec=RLModuleSpec(
                module_class=MaskedSACTorchRLModule,
                catalog_class=CellularenaSACCatalog,
            )
        )


class MaskedSACTorchRLModule(DefaultSACTorchRLModule):
    """Native discrete SAC module with legal-action masking in every forward path."""

    def _mask_logits(self, logits: torch.Tensor, observations: dict) -> torch.Tensor:
        mask = observations["action_mask"]
        valid = mask > 0.0
        has_valid = valid.any(dim=-1, keepdim=True)
        valid = torch.where(has_valid, valid, torch.ones_like(valid))
        return logits.masked_fill(~valid, torch.finfo(logits.dtype).min)

    def _forward_inference(self, batch):
        output = super()._forward_inference(batch)
        output[Columns.ACTION_DIST_INPUTS] = self._mask_logits(
            output[Columns.ACTION_DIST_INPUTS], batch[Columns.OBS]
        )
        return output

    def _forward_train_discrete(self, batch):
        batch_curr = {Columns.OBS: batch[Columns.OBS]}
        batch_next = {Columns.OBS: batch[Columns.NEXT_OBS]}
        output = {}

        pi_encoder_next_outs = self.pi_encoder(batch_next)
        action_logits_next = self._mask_logits(
            self.pi(pi_encoder_next_outs[ENCODER_OUT]), batch[Columns.NEXT_OBS]
        )
        action_probs_next = torch.nn.functional.softmax(action_logits_next, dim=-1)
        output[ACTION_PROBS_NEXT] = action_probs_next
        output[ACTION_LOG_PROBS_NEXT] = action_probs_next.clamp_min(1e-12).log()
        output[QF_TARGET_NEXT] = self.forward_target(batch_next, squeeze=False)

        qf_preds = self._qf_forward_train_helper(batch_curr, self.qf_encoder, self.qf, squeeze=False)
        output[QF_PREDS] = qf_preds
        if self.twin_q:
            output[QF_TWIN_PREDS] = self._qf_forward_train_helper(
                batch_curr, self.qf_twin_encoder, self.qf_twin, squeeze=False
            )

        pi_encoder_outs = self.pi_encoder(batch_curr)
        action_logits = self._mask_logits(
            self.pi(pi_encoder_outs[ENCODER_OUT]), batch[Columns.OBS]
        )
        action_probs = torch.nn.functional.softmax(action_logits, dim=-1)
        output[ACTION_PROBS] = action_probs
        output[ACTION_LOG_PROBS] = action_probs.clamp_min(1e-12).log()
        return output