"""Proximal Policy Optimisation (PPO) bot.

Algorithm
---------
PPO is an on-policy actor-critic algorithm.  The bot collects a fixed rollout
of N steps per environment (via :class:`~rl.ppo_trainer.PPOTrainer`), computes
GAE advantages, then performs K epochs of minibatch gradient descent clipping
the probability ratio to stay within [1-ε, 1+ε].

Observation customization
--------------------------
Sometimes you want the agent to see a different (typically smaller) observation
than the one produced by the game environment.  Two parameters control this:

``agent_obs_space``
    A :class:`gymnasium.spaces.Dict` that describes the observation the network
    will receive.  Defaults to the game's ``obs_space`` when not provided.

``obs_preprocessor``
    An optional callable with signature::

        obs_preprocessor(obs: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]

    Applied to every batch of observations **after** conversion to tensors but
    **before** the forward pass.  Operates on batched tensors already on the
    correct device.  Typical use-cases: selecting a subset of channels, adding
    derived features, resizing the spatial grid.

    If ``obs_preprocessor`` is provided you *must* also supply
    ``agent_obs_space`` that matches the preprocessor's output shape so the
    network can derive its input dimension correctly.

Key hyper-parameters
--------------------
clip_eps      : Clipping range for probability ratio (default 0.2).
n_epochs      : Number of gradient epochs per rollout (default 4).
n_minibatches : Number of minibatches per epoch (default 4).
gamma         : Discount factor (default 0.99).
gae_lambda    : GAE lambda smoothing parameter (default 0.95).
vf_coef       : Value-function loss coefficient (default 0.5).
ent_coef      : Entropy bonus coefficient (default 0.01).
max_grad_norm : Gradient clipping norm (default 0.5).
lr            : Learning rate for Adam (default 3e-4).
target_kl     : Early-stop epoch when approx KL exceeds this (default None).
hidden_dim    : Width of the shared MLP trunk (default 256).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from gymnasium import spaces
import numpy as np
import torch
import torch.nn as nn

from pathlib import Path

from rl.base_bot import RLBot
from rl.base_network import BaseNetwork
from rl.base_trainer import BaseTrainer
from rl.buffer import AbstractBuffer, RolloutBuffer
from rl.env_runner import EnvRunner, EnvFactory, EpisodeEndCallback, OpponentSelector
from rl.experience import RolloutBatch, Transition
from rl.logger import TrainingLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _pack_obs(obs_list: List[Dict[str, np.ndarray]]) -> Dict[str, np.ndarray]:
    """Stack a list of single-sample obs dicts into a batched obs dict."""
    keys = obs_list[0].keys()
    return {k: np.stack([o[k] for o in obs_list]) for k in keys}


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

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

        # Shared trunk with Tanh activations (standard for PPO on continuous ctrl)
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

    # ------------------------------------------------------------------

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
        """Run a forward pass and return ``(action, log_prob, entropy, value)``.

        Parameters
        ----------
        obs:
            Batched observation dict (tensors on the correct device).
        action:
            If provided, compute log-probs for this action instead of sampling.
            Shape: ``(B,)`` for Discrete, ``(B, n_slots)`` for MultiDiscrete.
        action_mask:
            Boolean mask of legal actions.  Shape matches ``logits``.
            ``True`` = legal.  When ``None``, only padding masking applies.

        Returns
        -------
        action : ``(B,)`` or ``(B, n_slots)``
        log_prob : ``(B,)`` -- summed across slots for MultiDiscrete
        entropy : ``(B,)`` -- averaged across slots for MultiDiscrete
        value : ``(B, 1)``
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
                action = dist.sample()          # (B, n_slots)
            log_prob = dist.log_prob(action).sum(dim=-1)    # (B,)
            entropy = dist.entropy().mean(dim=-1)            # (B,)

        return action, log_prob, entropy, value

    def get_value(self, obs: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Return the critic value estimate for *obs*."""
        _, value = self.forward(obs)
        return value

    def export_ops(self) -> list[dict]:
        raise NotImplementedError("PPO network export is not yet implemented.")


# ---------------------------------------------------------------------------
# On-policy rollout buffer with GAE
# ---------------------------------------------------------------------------

class PPORolloutBuffer(RolloutBuffer):
    """Fixed-capacity on-policy buffer that computes GAE advantages in-place.

    Extends :class:`~rl.buffer.RolloutBuffer` with:

    * Per-environment transition ordering so GAE is computed correctly even
      when transitions from multiple envs are interleaved in the flat list.
    * :meth:`compute_advantages` which must be called after collection and
      before :meth:`sample`.
    """

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._advantages: Optional[np.ndarray] = None
        self._returns: Optional[np.ndarray] = None
        # env_idx -> list of indices into _storage (in collection order for that env)
        self._per_env_order: Dict[int, List[int]] = {}

    # ------------------------------------------------------------------

    def add(self, transition: Transition) -> None:
        idx = len(self._storage)
        super().add(transition)
        if len(self._storage) > idx:  # transition was accepted (buffer not full)
            env_idx = transition.info.get("env_idx", 0)
            self._per_env_order.setdefault(env_idx, []).append(idx)

    def compute_advantages(
        self,
        gamma: float,
        gae_lambda: float,
        bootstrap_values: Dict[int, float],
    ) -> None:
        """Compute GAE advantages and TD-lambda returns, stored in-place.

        Parameters
        ----------
        gamma:
            Discount factor.
        gae_lambda:
            GAE smoothing parameter lambda.
        bootstrap_values:
            Mapping ``env_idx -> V(s_{T+1})``.  Pass ``0.0`` for any
            environment whose last collected transition was terminal.
        """
        n = len(self._storage)
        advantages = np.zeros(n, dtype=np.float32)

        for env_idx, indices in self._per_env_order.items():
            bootstrap = float(bootstrap_values.get(env_idx, 0.0))
            gae = 0.0
            for i in reversed(range(len(indices))):
                t = indices[i]
                trans = self._storage[t]
                reward = float(trans.reward)
                value = float(trans.value) if trans.value is not None else 0.0
                done = bool(trans.done)

                if done:
                    # Terminal transition: next-state value is 0; reset GAE.
                    delta = reward - value
                    gae = delta
                elif i == len(indices) - 1:
                    # Last step of rollout, episode still ongoing: bootstrap.
                    delta = reward + gamma * bootstrap - value
                    gae = delta + gamma * gae_lambda * gae
                else:
                    next_t = indices[i + 1]
                    next_value = (
                        float(self._storage[next_t].value)
                        if self._storage[next_t].value is not None
                        else 0.0
                    )
                    delta = reward + gamma * next_value - value
                    gae = delta + gamma * gae_lambda * gae

                advantages[t] = gae

        self._advantages = advantages
        self._returns = advantages + np.array(
            [float(t.value) if t.value is not None else 0.0 for t in self._storage],
            dtype=np.float32,
        )

    @property
    def is_ready(self) -> bool:
        return self.is_full and self._advantages is not None

    def clear(self) -> None:
        super().clear()
        self._advantages = None
        self._returns = None
        self._per_env_order = {}

    def sample(self, batch_size: int = -1) -> RolloutBatch:
        """Pack the entire buffer into a :class:`~rl.experience.RolloutBatch`.

        :meth:`compute_advantages` must be called first.
        """
        if self._advantages is None:
            raise RuntimeError(
                "PPORolloutBuffer.compute_advantages() must be called before sample()."
            )

        storage = self._storage
        obs = _pack_obs([t.obs for t in storage])
        actions = np.stack([t.action for t in storage])
        rewards = np.array([t.reward for t in storage], dtype=np.float32)
        next_obs = _pack_obs([t.next_obs for t in storage])
        dones = np.array([t.done for t in storage], dtype=bool)
        log_probs = np.array(
            [t.log_prob if t.log_prob is not None else 0.0 for t in storage],
            dtype=np.float32,
        )
        values = np.array(
            [t.value if t.value is not None else 0.0 for t in storage],
            dtype=np.float32,
        )

        first_mask = next(
            (t.action_mask for t in storage if t.action_mask is not None), None
        )
        if first_mask is not None:
            action_masks = np.stack([
                t.action_mask if t.action_mask is not None else np.ones_like(first_mask)
                for t in storage
            ])
        else:
            action_masks = None

        return RolloutBatch(
            obs=obs,
            actions=actions,
            rewards=rewards,
            next_obs=next_obs,
            dones=dones,
            log_probs=log_probs,
            values=values,
            action_masks=action_masks,
            advantages=self._advantages.copy(),
            returns=self._returns.copy(),
        )


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

class PPOBot(RLBot):
    """PPO agent compatible with any two-agent PettingZoo ParallelEnv.

    The network is built from ``agent_obs_space`` (defaults to ``obs_space``)
    and ``action_space``.  An optional ``obs_preprocessor`` can transform the
    game's observation into the agent's view at inference time without changing
    what is stored in the replay buffer.

    Parameters
    ----------
    obs_space:
        :class:`gymnasium.spaces.Space` returned by the environment.
    action_space:
        :class:`gymnasium.spaces.Space` for a single agent.
    agent_obs_space:
        The observation space the *network* expects.  Provide this together
        with ``obs_preprocessor`` to customise the agent's view of the game.
        Defaults to ``obs_space``.
    obs_preprocessor:
        ``Callable[[Dict[str, Tensor]], Dict[str, Tensor]]`` applied to batched
        tensors on-device **before** every network forward pass.  Must produce
        observations matching ``agent_obs_space``.
    clip_eps:
        PPO surrogate clipping coefficient epsilon.
    n_epochs:
        Number of optimisation epochs per rollout.
    n_minibatches:
        Number of minibatches per epoch.
    gamma:
        Discount factor.
    gae_lambda:
        GAE lambda smoothing parameter.
    vf_coef:
        Value-function loss coefficient.
    ent_coef:
        Entropy bonus coefficient.
    max_grad_norm:
        Gradient clipping norm.
    lr:
        Adam learning rate.
    target_kl:
        If set, early-exit the inner epoch loop when approximate KL exceeds this.
    hidden_dim:
        Width of the MLP hidden layers.
    device:
        Torch device.
    """

    def __init__(
        self,
        obs_space: spaces.Space,
        action_space: spaces.Space,
        agent_obs_space: Optional[spaces.Space] = None,
        obs_preprocessor: Optional[
            Callable[[Dict[str, torch.Tensor]], Dict[str, torch.Tensor]]
        ] = None,
        clip_eps: float = 0.2,
        n_epochs: int = 4,
        n_minibatches: int = 4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        vf_coef: float = 0.5,
        ent_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        lr: float = 3e-4,
        target_kl: Optional[float] = None,
        hidden_dim: int = 256,
        device: str | torch.device = "cpu",
    ) -> None:
        super().__init__(obs_space=obs_space, action_space=action_space, device=device)
        self.agent_obs_space = agent_obs_space if agent_obs_space is not None else obs_space
        self._obs_preprocessor = obs_preprocessor
        self.clip_eps = clip_eps
        self.n_epochs = n_epochs
        self.n_minibatches = n_minibatches
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.vf_coef = vf_coef
        self.ent_coef = ent_coef
        self.max_grad_norm = max_grad_norm
        self.lr = lr
        self.target_kl = target_kl
        self.hidden_dim = hidden_dim

        self._optimizer: Optional[torch.optim.Optimizer] = None

    # ------------------------------------------------------------------
    # RLBot interface
    # ------------------------------------------------------------------

    def build(self) -> "PPOBot":
        self._network = self.create_network().to(self.device)
        self._optimizer = torch.optim.Adam(
            self.network.parameters(), lr=self.lr, eps=1e-5
        )
        return self

    def create_network(self) -> BaseNetwork:
        """Return a :class:`PPOActorCriticNetwork` using ``agent_obs_space``."""
        return PPOActorCriticNetwork(
            obs_space=self.agent_obs_space,
            action_space=self.action_space,
            hidden_dim=self.hidden_dim,
        )

    def select_action(
        self,
        obs: Dict[str, np.ndarray],
        deterministic: bool = False,
        action_mask: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Sample (or greedily select) an action; return ``(action, extras)``.

        ``extras`` contains ``"log_prob"`` (float) and ``"value"`` (float)
        which are stored in the transition and used for GAE computation.
        """
        obs_t = self._np_obs_to_tensor(obs)
        mask_t = self._np_mask_to_tensor(action_mask)

        with torch.no_grad():
            if deterministic:
                logits, value = self.network.forward(obs_t)
                if self._action_mode == "multidiscrete":
                    logits = logits.masked_fill(
                        ~self.network.pad_mask.unsqueeze(0), float("-inf")
                    )
                    if mask_t is not None:
                        logits = logits.masked_fill(~mask_t, float("-inf"))
                    action_t = logits.argmax(dim=-1)  # (1, n_slots)
                    dist = torch.distributions.Categorical(logits=logits)
                    log_prob_t = dist.log_prob(action_t).sum(dim=-1)
                else:
                    if mask_t is not None:
                        logits = logits.masked_fill(~mask_t, float("-inf"))
                    action_t = logits.argmax(dim=-1)
                    dist = torch.distributions.Categorical(logits=logits)
                    log_prob_t = dist.log_prob(action_t)
                value_scalar = float(value.squeeze().item())
                log_prob_scalar = float(log_prob_t.squeeze().item())
            else:
                action_t, log_prob_t, _, value_t = self.network.get_action_and_value(
                    obs_t, action_mask=mask_t
                )
                value_scalar = float(value_t.squeeze().item())
                log_prob_scalar = float(log_prob_t.squeeze().item())

        action_np = action_t.squeeze(0).cpu().numpy()
        return action_np, {"log_prob": log_prob_scalar, "value": value_scalar}

    def update(self, batch: RolloutBatch) -> Dict[str, float]:
        """Run PPO gradient updates on *batch*.

        *batch* must have ``advantages`` and ``returns`` populated
        (call :meth:`PPORolloutBuffer.compute_advantages` before sampling).
        """
        if batch.advantages is None or batch.returns is None:
            raise RuntimeError(
                "PPOBot.update() requires batch.advantages and batch.returns. "
                "Call PPORolloutBuffer.compute_advantages() before sampling."
            )
        if self._optimizer is None:
            raise RuntimeError("Call PPOBot.build() before update().")

        B = int(batch.rewards.shape[0])

        obs_t = self._batch_obs_to_tensor(batch.obs)
        actions_t = torch.tensor(batch.actions, dtype=torch.long, device=self.device)
        old_log_probs_t = torch.tensor(batch.log_probs, dtype=torch.float32, device=self.device)
        advantages_t = torch.tensor(batch.advantages, dtype=torch.float32, device=self.device)
        returns_t = torch.tensor(batch.returns, dtype=torch.float32, device=self.device)
        old_values_t = torch.tensor(batch.values, dtype=torch.float32, device=self.device)

        action_masks_t: Optional[torch.Tensor] = None
        if batch.action_masks is not None:
            action_masks_t = torch.tensor(
                batch.action_masks, dtype=torch.bool, device=self.device
            )

        # Normalise advantages over the whole rollout batch
        advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)

        minibatch_size = max(1, B // self.n_minibatches)
        all_indices = np.arange(B)
        all_metrics: List[Dict[str, float]] = []

        for _ in range(self.n_epochs):
            np.random.shuffle(all_indices)
            for start in range(0, B, minibatch_size):
                mb_idx = all_indices[start : start + minibatch_size]

                mb_obs = {k: v[mb_idx] for k, v in obs_t.items()}
                mb_actions = actions_t[mb_idx]
                mb_old_log_probs = old_log_probs_t[mb_idx]
                mb_advantages = advantages_t[mb_idx]
                mb_returns = returns_t[mb_idx]
                mb_old_values = old_values_t[mb_idx]
                mb_masks = action_masks_t[mb_idx] if action_masks_t is not None else None

                _, new_log_probs, entropy, new_values = self.network.get_action_and_value(
                    mb_obs, action=mb_actions, action_mask=mb_masks
                )

                log_ratio = new_log_probs - mb_old_log_probs
                ratio = log_ratio.exp()

                # PPO clipped surrogate objective
                pg_loss1 = -mb_advantages * ratio
                pg_loss2 = -mb_advantages * torch.clamp(
                    ratio, 1.0 - self.clip_eps, 1.0 + self.clip_eps
                )
                pg_loss = torch.max(pg_loss1, pg_loss2).mean()

                # Clipped value loss
                new_values = new_values.view(-1)
                v_loss_unclipped = (new_values - mb_returns) ** 2
                v_clipped = mb_old_values + torch.clamp(
                    new_values - mb_old_values, -self.clip_eps, self.clip_eps
                )
                v_loss = 0.5 * torch.max(
                    v_loss_unclipped, (v_clipped - mb_returns) ** 2
                ).mean()

                entropy_loss = entropy.mean()
                loss = pg_loss - self.ent_coef * entropy_loss + self.vf_coef * v_loss

                self._optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
                self._optimizer.step()

                with torch.no_grad():
                    approx_kl = float(((ratio - 1) - log_ratio).mean().item())

                all_metrics.append({
                    "loss/total": float(loss.item()),
                    "loss/policy": float(pg_loss.item()),
                    "loss/value": float(v_loss.item()),
                    "loss/entropy": float(entropy_loss.item()),
                    "approx_kl": approx_kl,
                    "clip_frac": float(
                        ((ratio - 1.0).abs() > self.clip_eps).float().mean().item()
                    ),
                })

                if self.target_kl is not None and approx_kl > self.target_kl:
                    break

        return {k: float(np.mean([m[k] for m in all_metrics])) for k in all_metrics[0]}

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def get_value(self, obs: Dict[str, np.ndarray]) -> float:
        """Return V(obs) as a Python float (used for GAE bootstrapping)."""
        obs_t = self._np_obs_to_tensor(obs)
        with torch.no_grad():
            value = self.network.get_value(obs_t)
        return float(value.squeeze().item())

    @property
    def _action_mode(self) -> str:
        """Convenience accessor for the network's action mode."""
        return self.network._action_mode

    # ------------------------------------------------------------------
    # Internal tensor conversion helpers
    # ------------------------------------------------------------------

    def _np_obs_to_tensor(
        self, obs: Dict[str, np.ndarray]
    ) -> Dict[str, torch.Tensor]:
        """Convert a single-sample obs dict to a batched tensor dict on device."""
        obs_t = {
            k: torch.tensor(v, dtype=torch.float32, device=self.device).unsqueeze(0)
            for k, v in obs.items()
        }
        if self._obs_preprocessor is not None:
            obs_t = self._obs_preprocessor(obs_t)
        return obs_t

    def _batch_obs_to_tensor(
        self, obs: Dict[str, np.ndarray]
    ) -> Dict[str, torch.Tensor]:
        """Convert a batched obs dict ``(B, ...)`` to device tensors."""
        obs_t = {
            k: torch.tensor(v, dtype=torch.float32, device=self.device)
            for k, v in obs.items()
        }
        if self._obs_preprocessor is not None:
            obs_t = self._obs_preprocessor(obs_t)
        return obs_t

    def _np_mask_to_tensor(
        self, mask: Optional[np.ndarray]
    ) -> Optional[torch.Tensor]:
        """Convert a numpy action mask to a batched bool tensor on device."""
        if mask is None:
            return None
        return torch.tensor(mask, dtype=torch.bool, device=self.device).unsqueeze(0)

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
            "target_kl": self.target_kl,
            "hidden_dim": self.hidden_dim,
        }

    def _restore_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        if self._optimizer is not None and "optimizer_state_dict" in checkpoint:
            self._optimizer.load_state_dict(checkpoint["optimizer_state_dict"])


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------


class PPOTrainer(BaseTrainer):
    """On-policy PPO trainer with multi-environment rollout collection.

    Parameters
    ----------
    bot:
        A :class:`PPOBot` instance.
    opponent:
        The opponent bot used during training.
    env_factory:
        Zero-argument callable that returns a fresh
        :class:`~pettingzoo.ParallelEnv`.
    n_envs:
        Number of parallel environments.
    n_steps_per_rollout:
        Steps per environment per rollout.  Total rollout size =
        ``n_envs * n_steps_per_rollout``.
    learning_agent:
        Name of the PettingZoo agent being trained (default: ``"player_0"``).
    logger:
        :class:`~rl.logger.TrainingLogger` instance.
    eval_env_factory:
        Separate factory for evaluation environments.
    checkpoint_dir:
        Directory for periodic checkpoint files.
    eval_interval:
        Save checkpoint and evaluate every *eval_interval* training steps.
    self_play_manager:
        Optional league self-play manager.
    opponent_selector:
        Optional callback to select a per-episode opponent.
    on_episode_end:
        Optional callback invoked at the end of each episode.
    initial_global_step:
        Resume training from this step count.
    progress_interval_steps:
        How often to log progress to the console.
    """

    def __init__(
        self,
        bot: PPOBot,
        opponent: RLBot,
        env_factory: EnvFactory,
        n_envs: int = 4,
        n_steps_per_rollout: int = 128,
        learning_agent: str = "player_0",
        logger: Optional[TrainingLogger] = None,
        eval_env_factory: Optional[EnvFactory] = None,
        checkpoint_dir: Optional[str | Path] = None,
        eval_interval: Optional[int] = 10_000,
        self_play_manager: Optional[Any] = None,
        opponent_selector: Optional[OpponentSelector] = None,
        on_episode_end: Optional[EpisodeEndCallback] = None,
        initial_global_step: int = 0,
        progress_interval_steps: int = 1000,
    ) -> None:
        super().__init__(
            bot=bot,
            opponent=opponent,
            env_factory=env_factory,
            n_envs=n_envs,
            learning_agent=learning_agent,
            logger=logger,
            eval_env_factory=eval_env_factory,
            checkpoint_dir=checkpoint_dir,
            eval_interval=eval_interval,
            self_play_manager=self_play_manager,
            opponent_selector=opponent_selector,
            on_episode_end=on_episode_end,
            initial_global_step=initial_global_step,
            progress_interval_steps=progress_interval_steps,
        )
        if not isinstance(bot, PPOBot):
            raise TypeError(f"PPOTrainer requires a PPOBot; got {type(bot).__name__}.")
        self.n_steps_per_rollout = int(n_steps_per_rollout)

    # ------------------------------------------------------------------
    # BaseTrainer interface
    # ------------------------------------------------------------------

    def create_buffer(self) -> PPORolloutBuffer:
        capacity = self.n_envs * self.n_steps_per_rollout
        return PPORolloutBuffer(capacity=capacity)

    def collect_experience(
        self,
        runner: EnvRunner,
        buffer: AbstractBuffer,
    ) -> int:
        """Fill *buffer* with one rollout and compute GAE advantages."""
        assert isinstance(buffer, PPORolloutBuffer)
        buffer.clear()

        self.bot.eval_mode()
        runner.collect(buffer, self.n_steps_per_rollout)
        self.bot.train_mode()

        bootstrap_values: Dict[int, float] = {}
        for env_idx, indices in buffer._per_env_order.items():
            if not indices:
                bootstrap_values[env_idx] = 0.0
                continue
            last_trans = buffer._storage[indices[-1]]
            if last_trans.done:
                bootstrap_values[env_idx] = 0.0
            else:
                bootstrap_values[env_idx] = self.bot.get_value(last_trans.next_obs)

        buffer.compute_advantages(
            gamma=self.bot.gamma,
            gae_lambda=self.bot.gae_lambda,
            bootstrap_values=bootstrap_values,
        )
        return len(buffer)

    def train_step(self, buffer: AbstractBuffer) -> Dict[str, float]:
        """Consume the full rollout buffer and perform PPO gradient updates."""
        assert isinstance(buffer, PPORolloutBuffer)
        batch = buffer.sample()
        return self.bot.update(batch)
