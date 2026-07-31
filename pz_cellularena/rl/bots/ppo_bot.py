"""Proximal Policy Optimisation (PPO) bot – stub.

Algorithm overview
------------------
PPO is an on-policy actor-critic algorithm.  It collects a rollout of N steps,
computes advantages (GAE), then performs K epochs of minibatch gradient descent
clipping the probability ratio to stay within [1-ε, 1+ε].

This bot is game-agnostic: input/output shapes are derived from ``obs_space``
and ``action_space`` passed at construction time.  It is compatible with any
two-agent PettingZoo :class:`~pettingzoo.ParallelEnv`.

Key hyper-parameters
--------------------
clip_eps      : Clipping range for probability ratio (default 0.2).
n_epochs      : Number of gradient epochs per rollout (default 4).
n_minibatches : Number of minibatches per epoch (default 4).
gamma         : Discount factor (default 0.99).
gae_lambda    : GAE λ smoothing parameter (default 0.95).
vf_coef       : Value-function loss coefficient (default 0.5).
ent_coef      : Entropy bonus coefficient (default 0.01).
max_grad_norm : Gradient clipping norm (default 0.5).
lr            : Learning rate for Adam (default 3e-4).

Implementation checklist
------------------------
To implement PPOBot you need to:
1. Implement :meth:`create_network` – return an actor-critic network that
   outputs ``(action_logits, value)`` from :meth:`~rl.base_network.BaseNetwork.forward`.
2. Implement :meth:`select_action` – sample from the Categorical distribution
   over ``(action_logits,)`` and return ``log_prob`` + ``value`` in *extras*.
3. Implement :meth:`update` –
   a. Build a ``PPORolloutBuffer`` subclass that computes GAE advantages.
   b. For each epoch × minibatch: compute surrogate loss, value loss,
      entropy bonus, call ``loss.backward()`` + ``optimizer.step()``.
4. Implement :meth:`_populate_checkpoint` / :meth:`_restore_checkpoint`
   to persist the optimiser state.
5. Create a ``PPOTrainer(BaseTrainer)`` that sets ``collect_experience`` to
   fill a ``PPORolloutBuffer`` and ``train_step`` to call ``bot.update()``.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from gymnasium import spaces
import numpy as np
import torch

from rl.base_bot import RLBot
from rl.base_network import BaseNetwork
from rl.experience import RolloutBatch


class PPOBot(RLBot):
    """PPO agent compatible with any two-agent PettingZoo ParallelEnv.

    Input/output shapes are derived from ``obs_space`` and ``action_space``
    at build time.

    Parameters
    ----------
    obs_space:
        :class:`gymnasium.spaces.Space` for a single agent, obtained from
        ``env.observation_space(agent)``.
    action_space:
        :class:`gymnasium.spaces.Space` for a single agent, obtained from
        ``env.action_space(agent)``.
    clip_eps:
        PPO clipping parameter ε.
    n_epochs:
        Number of optimisation epochs per rollout.
    n_minibatches:
        Number of minibatches per epoch.
    gamma:
        Discount factor.
    gae_lambda:
        GAE λ smoothing parameter.
    vf_coef:
        Coefficient for the value-function loss term.
    ent_coef:
        Coefficient for the entropy bonus.
    max_grad_norm:
        Maximum gradient norm for clipping.
    lr:
        Adam learning rate.
    device:
        Torch device.
    """

    def __init__(
        self,
        obs_space: spaces.Space,
        action_space: spaces.Space,
        clip_eps: float = 0.2,
        n_epochs: int = 4,
        n_minibatches: int = 4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        vf_coef: float = 0.5,
        ent_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        lr: float = 3e-4,
        device: str | torch.device = "cpu",
    ) -> None:
        super().__init__(obs_space=obs_space, action_space=action_space, device=device)
        self.clip_eps = clip_eps
        self.n_epochs = n_epochs
        self.n_minibatches = n_minibatches
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.vf_coef = vf_coef
        self.ent_coef = ent_coef
        self.max_grad_norm = max_grad_norm
        self.lr = lr

        # Initialised in _populate_checkpoint / after build()
        self._optimizer: Optional[torch.optim.Optimizer] = None

    # ------------------------------------------------------------------
    # RLBot interface
    # ------------------------------------------------------------------

    def create_network(self) -> BaseNetwork:
        """Return an actor-critic network.

        TODO: implement a concrete network (e.g. CNN encoder → shared MLP →
              policy head + value head).  Derive input shape from
              ``self.obs_space`` and output shape from ``self.action_space``.

        The network's :meth:`~rl.base_network.BaseNetwork.forward` should
        return ``(action_logits, value)`` where:
        - ``action_logits`` shape matches the action space (e.g.
          ``(B, n_actions)`` for ``Discrete``, or
          ``(B, len(nvec), max(nvec))`` for ``MultiDiscrete``).
        - ``value`` has shape ``(B, 1)``.
        """
        raise NotImplementedError(
            "PPOBot.create_network() is not yet implemented. "
            "Create a concrete BaseNetwork subclass and return it here."
        )

    def select_action(
        self,
        obs: Dict[str, np.ndarray],
        deterministic: bool = False,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Sample (or greedily select) an action given *obs*.

        TODO: implement
        - Convert *obs* to tensors on :attr:`device`.
        - Run :attr:`network` forward to get ``(action_logits, value)``.
        - Build a ``torch.distributions.Categorical`` per organism slot.
        - If *deterministic*: take argmax; else sample.
        - Return ``(action_array, {"log_prob": lp, "value": v})``.
        """
        raise NotImplementedError("PPOBot.select_action() is not yet implemented.")

    def update(self, batch: RolloutBatch) -> Dict[str, float]:
        """Run PPO gradient updates on *batch*.

        TODO: implement
        - Compute advantages (or expect pre-computed from PPORolloutBuffer).
        - For each epoch × minibatch:
            * Compute ``ratio = exp(new_log_prob - old_log_prob)``.
            * ``policy_loss = -min(ratio * adv, clip(ratio, 1±ε) * adv).mean()``
            * ``value_loss = F.mse_loss(new_value, returns)``
            * ``entropy_loss = -entropy.mean()``
            * ``loss = policy_loss + vf_coef * value_loss + ent_coef * entropy_loss``
            * ``optimizer.zero_grad(); loss.backward(); clip_grad_norm_; optimizer.step()``
        - Return metrics dict.
        """
        raise NotImplementedError("PPOBot.update() is not yet implemented.")

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------

    def _populate_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        if self._optimizer is not None:
            checkpoint["optimizer_state_dict"] = self._optimizer.state_dict()
        checkpoint["hparams"] = {
            "clip_eps": self.clip_eps,
            "n_epochs": self.n_epochs,
            "n_minibatches": self.n_minibatches,
            "gamma": self.gamma,
            "gae_lambda": self.gae_lambda,
            "vf_coef": self.vf_coef,
            "ent_coef": self.ent_coef,
            "max_grad_norm": self.max_grad_norm,
            "lr": self.lr,
        }

    def _restore_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        if self._optimizer is not None and "optimizer_state_dict" in checkpoint:
            self._optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
