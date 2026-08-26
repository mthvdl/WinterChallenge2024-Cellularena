"""Observation mapper interface.

An :class:`ObsMapper` converts a raw gym observation (dict or array) into a
flat float tensor ready to be consumed by a neural network.

The generic training pipeline uses :class:`FlatObsMapper` by default, which
simply flattens and concatenates every sub-space value.  Game-specific code
can provide a custom mapper in ``Games/<game>/bots/obs_mapper.py`` to apply
domain preprocessing (normalisation, spatial encoding, feature selection,
etc.) before the tensor reaches the network.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Tuple

import numpy as np
import torch
import torch.nn as nn
from gymnasium import spaces


class ObsMapper(ABC):
    """Convert a single raw gym observation to a flat float tensor.

    Subclass this in ``Games/<game>/bots/obs_mapper.py`` to encode
    game-specific features, apply normalisation, or select a subset of
    channels before the observation reaches the neural network.
    """

    @abstractmethod
    def obs_to_tensor(self, obs: Any, device: torch.device) -> torch.Tensor:
        """Return a 1-D float tensor for a single *obs*.

        Parameters
        ----------
        obs:
            Raw observation returned by ``env.observe(agent)``.
        device:
            Target torch device.
        """
        ...

    @abstractmethod
    def output_dim(self, obs_space: spaces.Space) -> int:
        """Return the flat integer dimension of the mapped observation.

        Used by networks to size their input layer at build time.
        """
        ...

    def build_trunk(self, input_dim: int, hidden_dim: int) -> Tuple[nn.Module, int]:
        """Return ``(trunk_module, trunk_output_dim)`` for a PPO actor-critic.

        Override in game-specific mappers to provide a custom architecture
        (e.g. a CNN that reshapes the flat input internally).  The default
        builds the standard two-layer MLP with Tanh activations.

        Parameters
        ----------
        input_dim:
            Flat integer dimension produced by :meth:`output_dim`.
        hidden_dim:
            Desired width of hidden layers (and the returned output dim for
            the default MLP).
        """
        trunk = nn.Sequential(
            _mlp_layer(nn.Linear(input_dim, hidden_dim)),
            nn.Tanh(),
            _mlp_layer(nn.Linear(hidden_dim, hidden_dim)),
            nn.Tanh(),
        )
        return trunk, hidden_dim


def _mlp_layer(layer: nn.Linear, std: float = 2 ** 0.5) -> nn.Linear:
    nn.init.orthogonal_(layer.weight, std)
    nn.init.constant_(layer.bias, 0.0)
    return layer


class FlatObsMapper(ObsMapper):
    """Default mapper: flatten and concatenate all values of a Dict obs.

    Works with any ``spaces.Dict`` observation whose sub-spaces can be
    flattened to float32.  Keys are processed in sorted order for
    deterministic concatenation.
    """

    def obs_to_tensor(self, obs: Any, device: torch.device) -> torch.Tensor:
        if isinstance(obs, dict):
            parts = [
                np.asarray(obs[k], dtype=np.float32).ravel()
                for k in sorted(obs.keys())
            ]
            flat = np.concatenate(parts, axis=0)
        else:
            flat = np.asarray(obs, dtype=np.float32).ravel()
        return torch.from_numpy(flat).to(device)

    def output_dim(self, obs_space: spaces.Space) -> int:
        if isinstance(obs_space, spaces.Dict):
            return sum(
                int(np.prod(s.shape, dtype=np.int64))
                for s in obs_space.spaces.values()
            )
        return int(np.prod(obs_space.shape, dtype=np.int64))
