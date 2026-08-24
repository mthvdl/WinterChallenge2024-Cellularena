from __future__ import annotations

import copy
from typing import Any, Dict, Optional, Tuple

from gymnasium import spaces
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from rl.base_bot import RLBot
from rl.base_network import BaseNetwork
from rl.experience import RolloutBatch
from rl.rainbow.network import QRDuelingNoisyNetwork


class DQNBot(RLBot):
    """QR-DQN / Rainbow agent compatible with any two-agent PettingZoo ParallelEnv.

    The bot is fully game-agnostic: input and output shapes are derived from
    ``obs_space`` and ``action_space`` at build time.  No game-specific module
    is imported here.

    Parameters
    ----------
    obs_space:
        :class:`gymnasium.spaces.Space` for a single agent, obtained from
        ``env.observation_space(agent)``.
    action_space:
        :class:`gymnasium.spaces.Space` for a single agent, obtained from
        ``env.action_space(agent)``.
    lr:
        Adam learning rate.
    gamma:
        Discount factor.
    target_update:
        Hard target-network update frequency (in gradient steps).
    device:
        Torch device.
    """

    def __init__(
        self,
        obs_space: spaces.Space,
        action_space: spaces.Space,
        lr: float = 6.25e-5,
        gamma: float = 0.99,
        target_update: int = 500,
        # [RAINBOW 4] Multi-step learning
        n_step: int = 3,
        # [RAINBOW 3] Distributional DQN (QR-DQN)
        n_quantiles: int = 200,
        kappa: float = 1.0,
        # [RAINBOW 6] Prioritized Experience Replay
        per_alpha: float = 0.5,
        per_beta_start: float = 0.4,
        per_beta_steps: int = 100_000,
        per_eps: float = 1e-6,
        hidden_dim: int = 256,
        device: str | torch.device = "cpu",
    ) -> None:
        super().__init__(obs_space=obs_space, action_space=action_space, device=device)
        self.lr = lr
        self.gamma = gamma
        self.target_update = target_update
        # [RAINBOW 4]
        self.n_step = n_step
        # [RAINBOW 3]
        self.n_quantiles = n_quantiles
        self.kappa = kappa
        # [RAINBOW 6]
        self.per_alpha = per_alpha
        self.per_beta_start = per_beta_start
        self.per_beta_steps = per_beta_steps
        self.per_eps = per_eps
        self.hidden_dim = hidden_dim

        self._optimizer: Optional[torch.optim.Optimizer] = None
        self._target_network: Optional[BaseNetwork] = None
        self._steps_done: int = 0
        self._update_steps: int = 0
        self._last_priority_update_indices: Optional[np.ndarray] = None
        self._last_priority_update_values: Optional[np.ndarray] = None

    def build(self) -> "DQNBot":
        self._network = self.create_network().to(self.device)
        self._target_network = copy.deepcopy(self._network).to(self.device)
        self._target_network.eval()
        self._optimizer = torch.optim.Adam(self.network.parameters(), lr=self.lr)
        return self

    # ------------------------------------------------------------------
    # RLBot interface
    # ------------------------------------------------------------------

    def create_network(self) -> BaseNetwork:
        if self.obs_space is None or self.action_space is None:
            raise RuntimeError("obs_space and action_space must be provided.")
        return QRDuelingNoisyNetwork(
            obs_space=self.obs_space,
            action_space=self.action_space,
            n_quantiles=self.n_quantiles,
            hidden_dim=self.hidden_dim,
        )

    def select_action(
        self,
        obs: Dict[str, np.ndarray],
        deterministic: bool = False,
        action_mask: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        net = self.network
        assert isinstance(net, QRDuelingNoisyNetwork)

        prev_training = net.training
        if deterministic:
            net.eval()
        else:
            net.train()
            net.reset_noise()

        obs_t = {
            k: torch.as_tensor(v, dtype=torch.float32, device=self.device).unsqueeze(0)
            for k, v in obs.items()
        }
        with torch.no_grad():
            quantiles = net(obs_t)[0]
            q_values = quantiles.mean(dim=-1)

            if net.is_discrete:
                action = int(torch.argmax(q_values[0], dim=0).item())
                action_arr = np.array(action, dtype=np.int64)
            else:
                if action_mask is not None:
                    dyn_mask = torch.as_tensor(
                        action_mask, dtype=torch.bool, device=self.device
                    ).unsqueeze(0)
                else:
                    dyn_mask = net.valid_action_mask.unsqueeze(0)
                masked_q = q_values.masked_fill(~dyn_mask, -1e9)
                action_arr = torch.argmax(masked_q[0], dim=-1).cpu().numpy().astype(np.int64)

        if prev_training:
            net.train()
        else:
            net.eval()

        self._steps_done += 1
        return action_arr, {}

    def update(self, batch: RolloutBatch) -> Dict[str, float]:
        """One Rainbow gradient step (QR-DQN + Double DQN + PER)."""
        if self._optimizer is None or self._target_network is None:
            raise RuntimeError("DQNBot must be built before calling update().")
        if batch.indices is None or batch.weights is None:
            raise ValueError("RolloutBatch for DQN update must include indices and weights.")

        net = self.network
        target = self._target_network
        assert isinstance(net, QRDuelingNoisyNetwork)
        assert isinstance(target, QRDuelingNoisyNetwork)

        obs_t = {
            k: torch.as_tensor(v, dtype=torch.float32, device=self.device)
            for k, v in batch.obs.items()
        }
        next_obs_t = {
            k: torch.as_tensor(v, dtype=torch.float32, device=self.device)
            for k, v in batch.next_obs.items()
        }
        actions_t = torch.as_tensor(batch.actions, dtype=torch.long, device=self.device)
        rewards_t = torch.as_tensor(batch.rewards, dtype=torch.float32, device=self.device)
        dones_t = torch.as_tensor(
            batch.dones.astype(np.float32), dtype=torch.float32, device=self.device
        )
        is_weights_t = torch.as_tensor(batch.weights, dtype=torch.float32, device=self.device)

        net.reset_noise()
        target.reset_noise()

        with torch.no_grad():
            online_next = net(next_obs_t)[0]
            q_online_next = online_next.mean(dim=-1)

            if net.is_discrete:
                best_next_actions = torch.argmax(q_online_next, dim=1)
            else:
                if batch.next_action_masks is not None:
                    next_mask = torch.as_tensor(
                        batch.next_action_masks, dtype=torch.bool, device=self.device
                    )
                else:
                    next_mask = net.valid_action_mask.unsqueeze(0).expand(
                        q_online_next.shape[0], -1, -1
                    )
                masked_q = q_online_next.masked_fill(~next_mask, -1e9)
                best_next_actions = torch.argmax(masked_q, dim=2)

            target_next = target(next_obs_t)[0]
            target_quantiles = self._gather_action_quantiles(target_next, best_next_actions)

            gamma_n = self.gamma ** self.n_step
            reward_term = rewards_t
            done_term = 1.0 - dones_t
            while reward_term.dim() < target_quantiles.dim():
                reward_term = reward_term.unsqueeze(-1)
                done_term = done_term.unsqueeze(-1)
            target_q = reward_term + gamma_n * done_term * target_quantiles

        pred_quantiles_all = net(obs_t)[0]
        pred_quantiles = self._gather_action_quantiles(pred_quantiles_all, actions_t)

        td = target_q.unsqueeze(-2) - pred_quantiles.unsqueeze(-1)
        abs_td = torch.abs(td)
        huber = torch.where(
            abs_td <= self.kappa,
            0.5 * td.pow(2),
            self.kappa * (abs_td - 0.5 * self.kappa),
        )

        tau = (
            2.0 * torch.arange(self.n_quantiles, device=self.device, dtype=torch.float32) + 1.0
        ) / (2.0 * float(self.n_quantiles))
        if pred_quantiles.dim() == 2:
            tau = tau.view(1, self.n_quantiles, 1)
        else:
            tau = tau.view(1, 1, self.n_quantiles, 1)

        quantile_weight = torch.abs(tau - (td.detach() < 0).float())
        quantile_huber = quantile_weight * huber

        loss_per_sample = quantile_huber.mean(dim=-1).sum(dim=-1) / float(self.n_quantiles)
        if loss_per_sample.dim() > 1:
            reduce_dims = tuple(range(1, loss_per_sample.dim()))
            loss_per_sample = loss_per_sample.mean(dim=reduce_dims)

        loss = (is_weights_t * loss_per_sample).mean()

        self._optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(net.parameters(), max_norm=10.0)
        self._optimizer.step()

        self._update_steps += 1
        if self._update_steps % self.target_update == 0:
            self._target_network.load_state_dict(self.network.state_dict())

        priority_reduce_dims = tuple(range(1, abs_td.dim()))
        priorities = (
            abs_td.detach().mean(dim=priority_reduce_dims).cpu().numpy() + self.per_eps
        )
        self._last_priority_update_indices = batch.indices
        self._last_priority_update_values = priorities

        beta = min(
            1.0,
            self.per_beta_start
            + self._steps_done * (1.0 - self.per_beta_start) / max(1, self.per_beta_steps),
        )
        return {
            "loss": float(loss.item()),
            "mean_priority": float(np.mean(priorities)),
            "beta": float(beta),
            "mean_q": float(pred_quantiles.detach().mean().item()),
        }

    @staticmethod
    def _gather_action_quantiles(
        quantiles: torch.Tensor,
        actions: torch.Tensor,
    ) -> torch.Tensor:
        """Gather quantiles for selected actions from Discrete/MultiDiscrete heads."""
        if quantiles.dim() == 3:
            b, _, n_q = quantiles.shape
            idx = actions.view(b, 1, 1).expand(b, 1, n_q)
            return quantiles.gather(dim=1, index=idx).squeeze(1)
        if quantiles.dim() == 4:
            b, d, _, n_q = quantiles.shape
            idx = actions.view(b, d, 1, 1).expand(b, d, 1, n_q)
            return quantiles.gather(dim=2, index=idx).squeeze(2)
        raise ValueError(f"Unexpected quantiles rank: {quantiles.dim()}")

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------

    def _populate_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        if self._optimizer is not None:
            checkpoint["optimizer_state_dict"] = self._optimizer.state_dict()
        if self._target_network is not None:
            checkpoint["target_network_state_dict"] = self._target_network.state_dict()
        checkpoint["steps_done"] = self._steps_done
        checkpoint["update_steps"] = self._update_steps
        checkpoint["hparams"] = {
            "lr": self.lr,
            "gamma": self.gamma,
            "target_update": self.target_update,
            "n_step": self.n_step,
            "n_quantiles": self.n_quantiles,
            "kappa": self.kappa,
            "per_alpha": self.per_alpha,
            "per_beta_start": self.per_beta_start,
            "per_beta_steps": self.per_beta_steps,
            "per_eps": self.per_eps,
            "hidden_dim": self.hidden_dim,
        }

    def _restore_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        if self._optimizer is not None and "optimizer_state_dict" in checkpoint:
            self._optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        if self._target_network is not None and "target_network_state_dict" in checkpoint:
            self._target_network.load_state_dict(checkpoint["target_network_state_dict"])
        self._steps_done = checkpoint.get("steps_done", 0)
        self._update_steps = checkpoint.get("update_steps", 0)
        hparams = checkpoint.get("hparams", {})
        self.n_step = hparams.get("n_step", self.n_step)
        self.n_quantiles = hparams.get("n_quantiles", self.n_quantiles)
        self.kappa = hparams.get("kappa", self.kappa)
        self.per_alpha = hparams.get("per_alpha", self.per_alpha)
        self.per_beta_start = hparams.get("per_beta_start", self.per_beta_start)
        self.per_beta_steps = hparams.get("per_beta_steps", self.per_beta_steps)
        self.per_eps = hparams.get("per_eps", self.per_eps)
        self.hidden_dim = hparams.get("hidden_dim", self.hidden_dim)
