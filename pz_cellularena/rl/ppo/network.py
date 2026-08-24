from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from gymnasium import spaces
import numpy as np
import torch
import torch.nn as nn

from rl.base_network import BaseNetwork


def _layer_init(layer: nn.Linear, std: float = np.sqrt(2), bias_const: float = 0.0) -> nn.Linear:
    """Orthogonal weight initialisation (CleanRL style)."""
    nn.init.orthogonal_(layer.weight, std)
    nn.init.constant_(layer.bias, bias_const)
    return layer


def _flat_dim(space: spaces.Space) -> int:
    """Flat size of a single sample from *space*."""
    if isinstance(space, (spaces.Box, spaces.MultiBinary)):
        return int(np.prod(space.shape, dtype=np.int64))
    if isinstance(space, spaces.Discrete):
        return 1
    if isinstance(space, spaces.MultiDiscrete):
        return int(len(space.nvec))
    raise NotImplementedError(f"Unsupported sub-space type: {type(space).__name__}")


class PPOActorCriticNetwork(BaseNetwork):
    """Game-agnostic MLP actor-critic for Dict obs + Discrete/MultiDiscrete actions.

    ``forward(obs)`` returns ``(logits, value)`` where:

    * For ``Discrete(n)``: ``logits`` shape ``(B, n)``.
    * For ``MultiDiscrete(nvec)``: ``logits`` shape ``(B, n_slots, max_n_actions)``.
    * ``value`` shape ``(B, 1)``.

    Parameters
    ----------
    obs_space:
        :class:`gymnasium.spaces.Dict` describing the network's input (may be
        the agent-specific obs after applying an ``obs_preprocessor``).
    action_space:
        :class:`~gymnasium.spaces.Space` for a single agent.
    hidden_dim:
        Width of the two shared MLP hidden layers.
    """

    def __init__(
        self,
        obs_space: spaces.Dict,
        action_space: spaces.Space,
        hidden_dim: int = 256,
    ) -> None:
        super().__init__()

        if not isinstance(obs_space, spaces.Dict):
            raise NotImplementedError(
                f"PPOActorCriticNetwork expects a Dict observation space; got {type(obs_space).__name__}."
            )

        self.obs_keys = sorted(obs_space.spaces.keys())
        self.obs_dims = {k: _flat_dim(obs_space.spaces[k]) for k in self.obs_keys}
        input_dim = sum(self.obs_dims.values())
        self.hidden_dim = int(hidden_dim)

        if isinstance(action_space, spaces.Discrete):
            self._action_mode = "discrete"
            self.n_action_slots = 1
            self.max_actions = int(action_space.n)
            self.action_nvec: Optional[List[int]] = None
        elif isinstance(action_space, spaces.MultiDiscrete):
            self._action_mode = "multidiscrete"
            nvec = [int(v) for v in action_space.nvec.tolist()]
            self.n_action_slots = len(nvec)
            self.max_actions = max(nvec)
            self.action_nvec = nvec
            # Mask out padding positions where n_i < max_n_actions
            pad_mask = torch.zeros(self.n_action_slots, self.max_actions, dtype=torch.bool)
            for i, n in enumerate(nvec):
                pad_mask[i, :n] = True
            self.register_buffer("pad_mask", pad_mask)
        else:
            raise NotImplementedError(
                f"PPOActorCriticNetwork supports Discrete/MultiDiscrete; got {type(action_space).__name__}."
            )

        # Shared trunk with Tanh activations (standard for PPO)
        self.trunk = nn.Sequential(
            _layer_init(nn.Linear(input_dim, self.hidden_dim)),
            nn.Tanh(),
            _layer_init(nn.Linear(self.hidden_dim, self.hidden_dim)),
            nn.Tanh(),
        )

        # Actor head: small init std so the initial policy is near-uniform
        actor_out_dim = self.n_action_slots * self.max_actions
        self.actor_head = _layer_init(nn.Linear(self.hidden_dim, actor_out_dim), std=0.01)

        # Critic head
        self.critic_head = _layer_init(nn.Linear(self.hidden_dim, 1), std=1.0)

    def _flatten_obs(self, obs: Dict[str, torch.Tensor]) -> torch.Tensor:
        parts = []
        for key in self.obs_keys:
            t = obs[key].float()
            parts.append(t.view(t.shape[0], -1))
        return torch.cat(parts, dim=1)

    def forward(
        self, obs: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Return ``(logits, value)``."""
        x = self._flatten_obs(obs)
        hidden = self.trunk(x)

        logits = self.actor_head(hidden)
        value = self.critic_head(hidden)

        if self._action_mode == "multidiscrete":
            logits = logits.view(-1, self.n_action_slots, self.max_actions)

        return logits, value

    def get_action_and_value(
        self,
        obs: Dict[str, torch.Tensor],
        action: Optional[torch.Tensor] = None,
        action_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return ``(action, log_prob, entropy, value)``.

        Parameters
        ----------
        obs:
            Batched observation dict on the correct device.
        action:
            If provided, compute log-probs for this action instead of sampling.
        action_mask:
            Boolean mask of legal actions (``True`` = legal).
        """
        logits, value = self.forward(obs)

        if self._action_mode == "discrete":
            if action_mask is not None:
                logits = logits.masked_fill(~action_mask, float("-inf"))
            dist = torch.distributions.Categorical(logits=logits)
            if action is None:
                action = dist.sample()
            log_prob = dist.log_prob(action)
            entropy = dist.entropy()
        else:
            # Apply structural padding mask, then optional per-state legal mask
            logits = logits.masked_fill(~self.pad_mask.unsqueeze(0), float("-inf"))
            if action_mask is not None:
                logits = logits.masked_fill(~action_mask, float("-inf"))

            dist = torch.distributions.Categorical(logits=logits)
            if action is None:
                action = dist.sample()                      # (B, n_slots)
            log_prob = dist.log_prob(action).sum(dim=-1)    # (B,)
            entropy = dist.entropy().mean(dim=-1)           # (B,)

        return action, log_prob, entropy, value

    def get_value(self, obs: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Return the critic value estimate for *obs*."""
        _, value = self.forward(obs)
        return value

    def export_ops(self) -> list[dict]:
        raise NotImplementedError("PPO network export is not yet implemented.")
