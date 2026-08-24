from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from gymnasium import spaces
import numpy as np
import torch
import torch.nn as nn

from rl.base_bot import RLBot
from rl.base_network import BaseNetwork
from rl.experience import RolloutBatch
from rl.ppo.network import PPOActorCriticNetwork


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
        """Return a :class:`~rl.ppo.network.PPOActorCriticNetwork` using ``agent_obs_space``."""
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
                    action_t = logits.argmax(dim=-1)
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
        (call :meth:`~rl.ppo.buffer.PPORolloutBuffer.compute_advantages` before sampling).
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
        return self.network._action_mode

    # ------------------------------------------------------------------
    # Internal tensor conversion helpers
    # ------------------------------------------------------------------

    def _np_obs_to_tensor(self, obs: Dict[str, np.ndarray]) -> Dict[str, torch.Tensor]:
        obs_t = {
            k: torch.tensor(v, dtype=torch.float32, device=self.device).unsqueeze(0)
            for k, v in obs.items()
        }
        if self._obs_preprocessor is not None:
            obs_t = self._obs_preprocessor(obs_t)
        return obs_t

    def _batch_obs_to_tensor(self, obs: Dict[str, np.ndarray]) -> Dict[str, torch.Tensor]:
        obs_t = {
            k: torch.tensor(v, dtype=torch.float32, device=self.device)
            for k, v in obs.items()
        }
        if self._obs_preprocessor is not None:
            obs_t = self._obs_preprocessor(obs_t)
        return obs_t

    def _np_mask_to_tensor(self, mask: Optional[np.ndarray]) -> Optional[torch.Tensor]:
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
