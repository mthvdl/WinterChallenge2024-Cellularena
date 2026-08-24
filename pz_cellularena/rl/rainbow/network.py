from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from gymnasium import spaces
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from rl.base_network import BaseNetwork


def _space_flat_dim(space: spaces.Space) -> int:
    if isinstance(space, spaces.Box):
        return int(np.prod(space.shape, dtype=np.int64))
    if isinstance(space, spaces.Discrete):
        return 1
    if isinstance(space, spaces.MultiBinary):
        return int(np.prod(space.shape, dtype=np.int64))
    if isinstance(space, spaces.MultiDiscrete):
        return int(len(space.nvec))
    raise NotImplementedError(f"Unsupported observation sub-space type: {type(space).__name__}")


class NoisyLinear(nn.Module):
    """Factorised Gaussian NoisyLinear layer."""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        sigma0: float = 0.5,
    ) -> None:
        super().__init__()
        self.in_features = int(in_features)
        self.out_features = int(out_features)

        self.weight_mu = nn.Parameter(torch.empty(self.out_features, self.in_features))
        self.weight_sigma = nn.Parameter(torch.empty(self.out_features, self.in_features))
        self.register_buffer("weight_epsilon", torch.zeros(self.out_features, self.in_features))

        self.bias_mu = nn.Parameter(torch.empty(self.out_features))
        self.bias_sigma = nn.Parameter(torch.empty(self.out_features))
        self.register_buffer("bias_epsilon", torch.zeros(self.out_features))

        self.sigma0 = float(sigma0)
        self.reset_parameters()
        self.reset_noise()

    def reset_parameters(self) -> None:
        bound = 1.0 / math.sqrt(self.in_features)
        nn.init.uniform_(self.weight_mu, -bound, bound)
        nn.init.uniform_(self.bias_mu, -bound, bound)

        sigma = self.sigma0 / math.sqrt(self.in_features)
        nn.init.constant_(self.weight_sigma, sigma)
        nn.init.constant_(self.bias_sigma, sigma)

    @staticmethod
    def _scale_noise(size: int, device: torch.device) -> torch.Tensor:
        x = torch.randn(size, device=device)
        return torch.sign(x) * torch.sqrt(torch.abs(x))

    def reset_noise(self) -> None:
        eps_in = self._scale_noise(self.in_features, self.weight_mu.device)
        eps_out = self._scale_noise(self.out_features, self.weight_mu.device)
        self.weight_epsilon = eps_out.unsqueeze(1) * eps_in.unsqueeze(0)
        self.bias_epsilon = eps_out

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.training:
            weight = self.weight_mu + self.weight_sigma * self.weight_epsilon
            bias = self.bias_mu + self.bias_sigma * self.bias_epsilon
        else:
            weight = self.weight_mu
            bias = self.bias_mu
        return F.linear(x, weight, bias)


class QRDuelingNoisyNetwork(BaseNetwork):
    """Game-agnostic QR-DQN dueling network with NoisyLinear layers."""

    def __init__(
        self,
        obs_space: spaces.Space,
        action_space: spaces.Space,
        n_quantiles: int,
        hidden_dim: int = 256,
    ) -> None:
        super().__init__()
        if not isinstance(obs_space, spaces.Dict):
            raise NotImplementedError(
                "QRDuelingNoisyNetwork expects Dict observation spaces. "
                f"Got: {type(obs_space).__name__}."
            )

        self.obs_keys = sorted(list(obs_space.spaces.keys()))
        self.obs_dims = {k: _space_flat_dim(obs_space.spaces[k]) for k in self.obs_keys}
        input_dim = int(sum(self.obs_dims.values()))

        self.n_quantiles = int(n_quantiles)
        self.hidden_dim = int(hidden_dim)

        if isinstance(action_space, spaces.Discrete):
            self._action_mode = "discrete"
            self.action_shape: List[int] = [int(action_space.n)]
            self.n_action_slots = 1
            self.max_actions = int(action_space.n)
            self.valid_action_mask = None
        elif isinstance(action_space, spaces.MultiDiscrete):
            self._action_mode = "multidiscrete"
            nvec = [int(v) for v in action_space.nvec.tolist()]
            self.action_shape = nvec
            self.n_action_slots = len(nvec)
            self.max_actions = max(nvec)
            mask = torch.zeros(self.n_action_slots, self.max_actions, dtype=torch.bool)
            for i, n in enumerate(nvec):
                mask[i, :n] = True
            self.register_buffer("valid_action_mask", mask)
        else:
            raise NotImplementedError(
                "Only Discrete and MultiDiscrete action spaces are currently supported. "
                f"Got: {type(action_space).__name__}."
            )

        self.fc1 = NoisyLinear(input_dim, self.hidden_dim)
        self.fc2 = NoisyLinear(self.hidden_dim, self.hidden_dim)

        self.v1 = NoisyLinear(self.hidden_dim, self.hidden_dim)
        self.v2 = NoisyLinear(self.hidden_dim, self.n_quantiles)

        adv_out = self.n_action_slots * self.max_actions * self.n_quantiles
        self.a1 = NoisyLinear(self.hidden_dim, self.hidden_dim)
        self.a2 = NoisyLinear(self.hidden_dim, adv_out)

    @property
    def is_discrete(self) -> bool:
        return self._action_mode == "discrete"

    def _flatten_obs(self, obs: Dict[str, torch.Tensor]) -> torch.Tensor:
        parts = []
        for key in self.obs_keys:
            t = obs[key].float()
            parts.append(t.view(t.shape[0], -1))
        return torch.cat(parts, dim=1)

    def reset_noise(self) -> None:
        for module in self.modules():
            if isinstance(module, NoisyLinear):
                module.reset_noise()

    def forward(self, obs: Dict[str, torch.Tensor]) -> Tuple[torch.Tensor]:
        x = self._flatten_obs(obs)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))

        v = F.relu(self.v1(x))
        v = self.v2(v)

        a = F.relu(self.a1(x))
        a = self.a2(a)

        if self.is_discrete:
            a = a.view(x.shape[0], self.max_actions, self.n_quantiles)
            q_quantiles = v.unsqueeze(1) + a - a.mean(dim=1, keepdim=True)
        else:
            a = a.view(x.shape[0], self.n_action_slots, self.max_actions, self.n_quantiles)
            q_quantiles = v.unsqueeze(1).unsqueeze(1) + a - a.mean(dim=2, keepdim=True)
        return (q_quantiles,)

    @staticmethod
    def _export_linear(layer: NoisyLinear, layer_id: int, act: Optional[str]) -> dict:
        return {
            "op": "linear",
            "id": int(layer_id),
            "W": layer.weight_mu.detach().cpu().numpy().astype(np.float32),
            "b": layer.bias_mu.detach().cpu().numpy().astype(np.float32),
            "act": act,
        }

    def export_ops(self) -> list[dict]:
        return [
            self._export_linear(self.fc1, 0, "relu"),
            self._export_linear(self.fc2, 1, "relu"),
            {
                "op": "dueling",
                "n_quantiles": self.n_quantiles,
                "action_shape": list(self.action_shape),
                "v_layers": [
                    self._export_linear(self.v1, 2, "relu"),
                    self._export_linear(self.v2, 3, None),
                ],
                "a_layers": [
                    self._export_linear(self.a1, 4, "relu"),
                    self._export_linear(self.a2, 5, None),
                ],
            },
        ]
