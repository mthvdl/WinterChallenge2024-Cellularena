"""Abstract RL bot base class.

All concrete bots (PPO, DQN, …) must inherit from :class:`RLBot` and
implement the three abstract methods:
- :meth:`select_action`
- :meth:`update`
- :meth:`create_network`

This base class is intentionally game-agnostic.  It stores the
``obs_space`` and ``action_space`` obtained from the PettingZoo env so that
concrete bots and networks can derive input/output shapes at build time
without importing any game-specific module.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
from gymnasium import spaces

from rl.base_network import BaseNetwork
from rl.experience import RolloutBatch


class RLBot(ABC):
    """Abstract base class for all RL agents.

    A bot encapsulates:
    - A :class:`~rl.base_network.BaseNetwork` (the policy / value model).
    - An optimiser.
    - Algorithm-specific hyper-parameters.
    - The :meth:`select_action` and :meth:`update` logic.

    The bot does **not** manage the training loop, environment creation, or
    logging – those responsibilities belong to :class:`~rl.base_trainer.BaseTrainer`.

    Compatible with any PettingZoo :class:`~pettingzoo.ParallelEnv`; game-
    specific knowledge lives only in the concrete network returned by
    :meth:`create_network`.

    Parameters
    ----------
    obs_space:
        :class:`gymnasium.spaces.Space` returned by
        ``env.observation_space(agent)``.  Stored as :attr:`obs_space` so
        that :meth:`create_network` can derive input shapes without importing
        any game module.
    action_space:
        :class:`gymnasium.spaces.Space` returned by
        ``env.action_space(agent)``.  Stored as :attr:`action_space`.
    device:
        Torch device to run the network on (``"cpu"``, ``"cuda"``, …).
    """

    def __init__(
        self,
        obs_space: Optional[spaces.Space] = None,
        action_space: Optional[spaces.Space] = None,
        device: str | torch.device = "cpu",
    ) -> None:
        self.device = torch.device(device)
        self.obs_space = obs_space
        self.action_space = action_space
        self._network: Optional[BaseNetwork] = None

    # ------------------------------------------------------------------
    # Abstract interface – must be implemented by every algorithm
    # ------------------------------------------------------------------

    @abstractmethod
    def create_network(self) -> BaseNetwork:
        """Instantiate and return the neural network used by this bot.

        Called once during initialisation.  The returned network will be
        stored in :attr:`network` and moved to :attr:`device`.
        """

    @abstractmethod
    def select_action(
        self,
        obs: Dict[str, np.ndarray],
        deterministic: bool = False,
        action_mask: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Choose an action given an observation.

        Parameters
        ----------
        obs:
            Observation dict for one agent as returned by the PettingZoo env
            (numpy arrays, not yet converted to tensors).  The dict structure
            matches :attr:`obs_space`.
        deterministic:
            When True, return the greedy / mode action (used during
            evaluation).  When False, sample from the policy distribution
            (used during training).
        action_mask:
            Optional boolean array whose shape matches ``action_space``.
            ``True`` indicates a legal action; illegal actions are assigned
            a very large negative Q-value so they are never selected.
            ``None`` (default) disables masking (all actions are treated as
            legal).

        Returns
        -------
        action:
            Action array whose shape and dtype match :attr:`action_space`,
            ready to pass to ``env.step()``.
        extras:
            Dict of algorithm-specific data to store alongside the transition
            (e.g. ``{"log_prob": …, "value": …}`` for PPO).
        """

    @abstractmethod
    def update(self, batch: RolloutBatch) -> Dict[str, float]:
        """Perform one gradient-update step on *batch*.

        Parameters
        ----------
        batch:
            A :class:`~rl.experience.RolloutBatch` already converted to
            tensors on the correct device.

        Returns
        -------
        metrics:
            Dict of scalar metrics to log (e.g.
            ``{"loss/policy": 0.42, "loss/value": 0.07, …}``).
        """

    # ------------------------------------------------------------------
    # Shared helpers – concrete implementations are provided
    # ------------------------------------------------------------------

    @property
    def network(self) -> BaseNetwork:
        """The underlying neural network.

        Raises ``RuntimeError`` if :meth:`build` has not been called yet.
        """
        if self._network is None:
            raise RuntimeError(
                "Network is not initialised. Call RLBot.build() before use."
            )
        return self._network

    def build(self) -> "RLBot":
        """Instantiate the network and move it to the target device.

        Call this after construction and before the first :meth:`select_action`
        or :meth:`update` call.

        Returns *self* to allow method chaining::

            bot = PPOBot(...).build()
        """
        self._network = self.create_network().to(self.device)
        return self

    def save(self, path: str | Path) -> None:
        """Persist the network weights and optimiser state to *path*.

        The file is a plain ``torch.save`` checkpoint dict with at minimum:
        - ``"network_state_dict"``
        - ``"algorithm"`` (class name string for integrity checks)

        Subclasses should call ``super().save(path)`` and then add their own
        keys (e.g. optimiser state, hyper-parameters) to the checkpoint.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint: Dict[str, Any] = {
            "algorithm": type(self).__name__,
            "network_state_dict": self.network.state_dict(),
        }
        self._populate_checkpoint(checkpoint)
        torch.save(checkpoint, path)

    def load(self, path: str | Path) -> None:
        """Restore network weights (and optionally optimiser state) from *path*.

        Subclasses should call ``super().load(path)`` then restore their own
        keys from the returned checkpoint dict.
        """
        path = Path(path)
        checkpoint: Dict[str, Any] = torch.load(path, map_location=self.device)
        if checkpoint.get("algorithm") != type(self).__name__:
            raise ValueError(
                f"Checkpoint was saved by '{checkpoint.get('algorithm')}' "
                f"but this bot is '{type(self).__name__}'."
            )
        self.network.load_state_dict(checkpoint["network_state_dict"])
        self._restore_checkpoint(checkpoint)

    # ------------------------------------------------------------------
    # Extension hooks for save / load (override in subclasses)
    # ------------------------------------------------------------------

    def _populate_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """Add algorithm-specific entries to *checkpoint* before saving.

        Override in subclasses to persist optimiser state, hyper-parameters,
        step counters, etc.
        """

    def _restore_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """Restore algorithm-specific entries from *checkpoint* after loading.

        Override in subclasses to restore optimiser state, step counters, etc.
        """

    # ------------------------------------------------------------------
    # Training / eval mode forwarding
    # ------------------------------------------------------------------

    def train_mode(self) -> None:
        """Switch the network to training mode (enables dropout / BatchNorm)."""
        self.network.train()

    def eval_mode(self) -> None:
        """Switch the network to evaluation mode."""
        self.network.eval()
