"""Abstract neural network base class.

All networks used by RL bots must subclass :class:`BaseNetwork`.  This
guarantees a consistent interface for observation encoding, action-head
outputs, and serialisation.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Dict, Tuple

import torch
import torch.nn as nn


class BaseNetwork(nn.Module):
    """Abstract PyTorch module for RL policies / value functions.

    Subclasses receive the observation dict produced by the PettingZoo env
    and must return at minimum a *logits* or *quantiles* tensor over the
    action space.  Actor-critic architectures should also return a *value*
    scalar.

    The observation dict structure and action-space shape are environment-
    dependent.  Concrete subclasses should accept ``obs_space`` and
    ``action_space`` (:class:`gymnasium.spaces.Space`) at construction time
    so that input/output dimensions can be derived without importing any
    game-specific module.

    Notes
    -----
    Implementations are free to use any architecture (CNN, MLP, Transformer,
    …).  The only hard contract is :meth:`forward`.
    """

    @abstractmethod
    def forward(
        self, obs: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, ...]:
        """Run a forward pass.

        Parameters
        ----------
        obs:
            Batch of observations as a dict of tensors (already on the correct
            device and in channels-first format for "grid").

        Returns
        -------
        A tuple whose contents depend on the algorithm:
        - **Value-based** (DQN / QR-DQN): ``(q_values,)`` or ``(quantiles,)``
        - **Actor-critic** (PPO/A2C): ``(action_logits, value)``
        - **SAC / continuous**: ``(mean, log_std, value)``

        The exact tuple layout is documented by the concrete subclass.
        """

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def count_parameters(self) -> int:
        """Return the total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def export_ops(self) -> list[dict]:
        """Return a serialisable description of the forward-pass graph.

        Implement this in every concrete subclass to enable
        ``export_to_codingame.py`` to generate a pure-numpy bot that runs
        inside CodinGame (Python 3 + numpy only, no PyTorch).

        Returns a list of op dicts executed in order. Two op types are
        supported:

        **``"linear"`` op** (covers ``nn.Linear`` and ``NoisyLinear`` – for
        NoisyLinear export only the *mean* parameters ``weight_mu`` /
        ``bias_mu``; the noise is training-only)::

            {
                "op"  : "linear",
                "id"  : int,          # unique integer ID; used as array key
                "W"   : np.ndarray,   # shape (out, in), float32
                "b"   : np.ndarray,   # shape (out,),    float32
                "act" : str | None,   # "relu" | "tanh" | "lrelu" | None
            }

        **``"dueling"`` op** (QR-DQN Rainbow dueling head)::

            {
                "op"          : "dueling",
                "n_quantiles" : int,
                "action_shape": list[int],  # e.g. [4] for Discrete(4)
                                            # or [3, 4] for MultiDiscrete([3,4])
                "v_layers"    : [linear_op, ...],  # value stream
                "a_layers"    : [linear_op, ...],  # advantage stream
            }

        The inference engine computes::

            Q(s,a) = mean_quantile( V(s) + A(s,a) − mean_a A(s,a) )

        and returns ``argmax_a Q`` per action dimension.

        Example – 2-layer torso + dueling head for ``Discrete(5)``::

            [
                {"op": "linear", "id": 0, "W": ..., "b": ..., "act": "relu"},
                {"op": "linear", "id": 1, "W": ..., "b": ..., "act": "relu"},
                {
                    "op": "dueling", "n_quantiles": 32,
                    "action_shape": [5],
                    "v_layers": [
                        {"op": "linear", "id": 2, "W": ..., "b": ..., "act": "relu"},
                        {"op": "linear", "id": 3, "W": ..., "b": ..., "act": None},
                    ],
                    "a_layers": [
                        {"op": "linear", "id": 4, "W": ..., "b": ..., "act": "relu"},
                        {"op": "linear", "id": 5, "W": ..., "b": ..., "act": None},
                    ],
                },
            ]

        Raises
        ------
        NotImplementedError
            If the concrete subclass has not overridden this method.
        """
        raise NotImplementedError(
            f"{type(self).__name__}.export_ops() is not implemented. "
            "Override this method to enable export_to_codingame.py."
        )
