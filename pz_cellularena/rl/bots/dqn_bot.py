"""Rainbow DQN bot – stub.

Algorithm overview
------------------
Rainbow (Hessel et al., 2017) combines six improvements over vanilla DQN into a
single agent.  This stub is structured to guide a full Rainbow implementation.
Each improvement is flagged with a [RAINBOW] tag in the relevant TODO.

The six Rainbow components
--------------------------
1. **Double DQN** (van Hasselt et al., 2015)
   Decouple action *selection* (online network) from action *evaluation*
   (target network) in the TD target to reduce overestimation bias:
   ``y = r + γ * Q(s', argmax_a Q(s', a; θ); θ⁻)``

2. **Dueling DQN** (Wang et al., 2016)
   Split the network head into two streams:
   - Value stream  V(s)       – scalar
   - Advantage stream A(s,a)  – one value per action
   Recombine as  Q(s,a) = V(s) + A(s,a) − mean_a A(s,a)  (mean-subtracted).

3. **Distributional DQN / QR-DQN** (Dabney et al., 2017 – arXiv:1710.10044)
   Predict the full return *distribution* as N quantile value estimates
   θ_1,...,θ_N(s,a) at fixed uniform quantile fractions
   τ̂_i = (2i − 1) / (2N)  for i = 1,...,N.
   Unlike C51 there is no bounded support [V_MIN, V_MAX] and no L2 projection.
   Loss = quantile Huber (pinball) loss between target quantiles and
   predicted quantiles.  Combine with Dueling: each stream outputs
   (N_QUANTILES,) values instead of logits.

4. **Multi-step Learning** (Sutton & Barto, ch. 7)
   Replace 1-step TD targets with n-step discounted returns:
   ``R_n = Σ_{k=0}^{n-1} γ^k r_{t+k}`` then bootstrap from s_{t+n}.
   Requires storing trajectories of length n in the replay buffer.
   In the distributional setting use the n-step distributional Bellman target.

5. **Noisy Nets** (Fortunato et al., 2017)
   Replace all linear layers (both value and advantage streams) with NoisyLinear
   layers whose weights/biases are perturbed by learned Gaussian noise.
   Use factorised Gaussian noise: generate noise vectors of size p and q,
   apply f(x)=sgn(x)√|x|, then take the outer product for the weight matrix.
   This replaces ε-greedy exploration – no epsilon annealing needed.
   Call ``reset_noise()`` on all NoisyLinear layers at the start of each step.

6. **Prioritized Experience Replay / PER** (Schaul et al., 2016)
   Store transitions in a sum-tree keyed by priority p_i = |δ_i| + ε_per.
   Sample with probability  P(i) = p_i^α / Σ p_j^α.
   Correct the resulting bias with importance-sampling weights:
   ``w_i = (1 / (N · P(i)))^β``  normalised by max w.
   Anneal β from β_start → 1.0 over training.  After each gradient step,
   update the priorities in the sum-tree with the fresh TD errors.

Key hyper-parameters
--------------------
lr              : Adam learning rate (default 6.25e-5, as in Rainbow paper).
gamma           : Discount factor (default 0.99).
buffer_size     : Replay buffer capacity (default 100_000).
batch_size      : Minibatch size for each gradient step (default 32).
target_update   : Hard target-network update frequency in gradient steps (default 500).
n_step          : [RAINBOW 4] Multi-step return length (default 3).
n_quantiles     : [RAINBOW 3] Number of quantile estimates N (default 200, as in QR-DQN paper).
kappa           : [RAINBOW 3] Huber loss threshold κ for quantile regression loss (default 1.0).
per_alpha       : [RAINBOW 6] PER priority exponent α (default 0.5).
per_beta_start  : [RAINBOW 6] Initial IS weight exponent β (default 0.4).
per_beta_steps  : [RAINBOW 6] Steps to anneal β to 1.0 (default 100_000).
per_eps         : [RAINBOW 6] Small constant added to priorities (default 1e-6).

Implementation checklist
------------------------
To implement RainbowBot you need to:
1. Implement :meth:`create_network` – return a network with:
   a. [RAINBOW 2] Dueling head: shared torso → separate V and A NoisyLinear streams.
      Derive input shape from ``self.obs_space``; derive number of actions and
      action dimensions from ``self.action_space``.
   b. [RAINBOW 3] Each stream outputs (N_QUANTILES,) values (not logits / no softmax).
   c. [RAINBOW 5] All linear layers are NoisyLinear (factorised Gaussian noise).
2. Create a target network (deep copy of the Q-network) in :meth:`build`.
3. Implement :meth:`select_action` –
   a. [RAINBOW 5] Call ``reset_noise()`` on the online network before each forward pass.
   b. [RAINBOW 3] Compute expected Q-values as the mean over quantiles:
      Q(s, a) = (1/N) Σ_i θ_i(s, a).
   c. Select argmax over expected Q-values (no ε-greedy needed).
      Return an action whose shape matches ``self.action_space``.
4. Implement :meth:`update` –
   a. [RAINBOW 6] Sample a weighted minibatch from the ``PrioritizedReplayBuffer``;
      retrieve importance-sampling weights w_i.
   b. [RAINBOW 5] Call ``reset_noise()`` on both online and target networks.
   c. [RAINBOW 3+4] Compute QR-DQN quantile Bellman targets (no gradient):
      target actions chosen by [RAINBOW 1] Double DQN;
      target quantile values T̂θ_j = R_n + γ^n · θ_j(s', a*) for each j.
   d. [RAINBOW 3] Compute quantile Huber loss per sample (see update() docstring).
   e. [RAINBOW 6] Weight each sample by IS weight; backprop + grad clip + step.
   f. [RAINBOW 6] Update priorities in the sum-tree with fresh |δ_i| + ε_per.
   g. Every :attr:`target_update` steps: hard-copy Q-net weights → target net.
5. Implement :meth:`_populate_checkpoint` / :meth:`_restore_checkpoint`.
6. Create a ``RainbowTrainer(BaseTrainer)`` that populates the
   ``PrioritizedReplayBuffer`` with n-step trajectories and calls
   ``bot.update()`` every step once the buffer has >= batch_size transitions.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from gymnasium import spaces
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from rl.base_bot import RLBot
from rl.base_network import BaseNetwork
from rl.base_trainer import BaseTrainer
from rl.buffer import AbstractBuffer
from rl.env_runner import EnvRunner, EnvFactory, EpisodeEndCallback, OpponentSelector
from rl.experience import RolloutBatch
from rl.logger import TrainingLogger
from rl.n_step import NStepBufferWrapper
from rl.prioritized_replay import PrioritizedReplayBuffer


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
        # [RAINBOW 4] Multi-step learning
        self.n_step = n_step
        # [RAINBOW 3] QR-DQN: N uniform quantile fractions, fixed at τ̂_i = (2i-1)/(2N)
        self.n_quantiles = n_quantiles
        self.kappa = kappa
        # [RAINBOW 6] PER hyper-parameters
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
        """Return the QR-DQN / Rainbow Q-network.

        TODO [RAINBOW 2+3+5]: implement a concrete network whose
        :meth:`~rl.base_network.BaseNetwork.forward` returns
        ``(quantiles,)`` where ``quantiles`` has shape
        ``(B, *flat_action_dims, N_QUANTILES)``.

        Use ``self.obs_space`` and ``self.action_space`` to derive all
        input/output dimensions – do **not** hard-code any game-specific
        constant here.  Examples:

        - ``gymnasium.spaces.Discrete(n)``:
          ``n`` actions, output shape ``(B, n, N_QUANTILES)``.
        - ``gymnasium.spaces.MultiDiscrete(nvec)``:
          ``len(nvec)`` action slots each with up to ``max(nvec)`` choices,
          output shape ``(B, len(nvec), max(nvec), N_QUANTILES)``;
          mask out invalid action indices at inference time.
        - ``gymnasium.spaces.Box``:
          continuous case – quantile regression over a continuous action
          distribution (requires a different head design).

        Architecture:
        1. Shared torso (MLP or CNN, derived from ``self.obs_space``) →
           embedding of shape ``(B, hidden_dim)``.
        2. [RAINBOW 2] Dueling split:
           - Value stream:     NoisyLinear(hidden_dim, hidden_dim)
                               → NoisyLinear(hidden_dim, N_QUANTILES)
             outputs N_QUANTILES scalar quantile values for the state value.
           - Advantage stream: NoisyLinear(hidden_dim, hidden_dim)
                               → NoisyLinear(hidden_dim, n_actions * N_QUANTILES)
             where ``n_actions`` is derived from ``self.action_space``.
        3. [RAINBOW 3] QR-DQN recombination (no softmax – these are raw values):
             Q_quantiles(s,a) = V_q(s) + A_q(s,a) − mean_a A_q(s,a)
           Values are *unconstrained* (no V_MIN/V_MAX).
        4. [RAINBOW 5] All linear layers (torso included) are NoisyLinear:
           - weights:  μ_w + σ_w ⊙ ε_w   where ε_w = f(ε_i) ⊗ f(ε_j)  (factorised)
           - biases:   μ_b + σ_b ⊙ ε_b   where ε_b = f(ε_j)
           - f(x) = sgn(x) * sqrt(|x|)
           - Expose a ``reset_noise()`` method that regenerates ε for all layers.
        """
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
        """Greedy action selection driven by noisy network exploration.

        TODO [RAINBOW 3+5]: implement
        - [RAINBOW 5] Call ``self.network.reset_noise()`` before the forward
          pass so the NoisyLinear layers sample fresh ε.  This replaces
          ε-greedy; no epsilon annealing is required.
        - Forward pass through the online network;
          output quantiles shape ``(B, *action_dims, N_QUANTILES)``
          where ``action_dims`` is derived from ``self.action_space``.
        - [RAINBOW 3] Compute expected Q-values as the mean over quantiles
          (no support vector needed – quantile values are directly averaged):
            Q(s, a) = (1 / N_QUANTILES) * Σ_i θ_i(s, a)
        - Select action = argmax_a Q(s, a) for each action dimension.
          The returned action array must match the shape of ``self.action_space``.
        - Increment :attr:`_steps_done`.
        - Return ``(action_array, {})``.
        """
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
              # Dynamic per-state mask provided by the env (preferred).
              dyn_mask = torch.as_tensor(action_mask, dtype=torch.bool, device=self.device).unsqueeze(0)
            else:
              # Fall back to the static structural mask (masks padding only).
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
        """One Rainbow gradient step.

        TODO: implement the full QR-DQN / Rainbow training step:

        Step 1 – Prepare batch
        - Convert (obs, action, reward, next_obs, done, weights, indices) to
          tensors on :attr:`device`.
        - [RAINBOW 4] ``reward`` is already the n-step discounted return
          R_n = Σ_{k=0}^{n-1} γ^k r_{t+k}; ``next_obs`` is s_{t+n}; ``done``
          is True if *any* of the n transitions is terminal.
        - Pre-compute fixed quantile fractions (shape: N):
            τ̂_i = (2i − 1) / (2 * N_QUANTILES)   for i = 1, ..., N_QUANTILES

        Step 2 – Noisy reset
        - [RAINBOW 5] Call ``reset_noise()`` on both the online and target
          networks before any forward pass.

        Step 3 – Build QR-DQN quantile targets (no gradient)
        - Online network forward on next_obs
          → online_next quantiles (B, *action_dims, N_QUANTILES).
        - [RAINBOW 1] Double DQN action selection:
            Q_online(s', a) = mean over quantiles of online_next
            best_a = argmax_a Q_online(s', a)   ← action from ONLINE net
        - Target network forward on next_obs
          → target_next quantiles (B, *action_dims, N_QUANTILES).
        - Gather target quantiles for best_a → shape (B, N_QUANTILES).
        - [RAINBOW 3+4] QR-DQN Bellman target (no projection needed):
            T̂θ_j = R_n + (γ^n) * (1 − done) * θ_j(s', best_a)
          shape: (B, N_QUANTILES)   (one target quantile value per j).

        Step 4 – Compute QR-DQN quantile Huber loss
        - Online network forward on obs
          → pred_quantiles (B, *action_dims, N_QUANTILES).
        - Gather quantiles for taken actions → θ_pred shape (B, N_QUANTILES).
        - Compute pairwise TD errors (expand dims for broadcasting):
            u = T̂θ_j.unsqueeze(1) − θ_pred.unsqueeze(2)
          shape: (B, N_QUANTILES_pred, N_QUANTILES_target)
        - [RAINBOW 3] Huber loss element-wise (threshold κ = :attr:`kappa`):
            L_κ(u) = 0.5 * u²              if |u| ≤ κ
                   = κ * (|u| − 0.5 * κ)  otherwise
        - Quantile regression (asymmetric) weighting:
            ρ_{τ̂_i}(u) = |τ̂_i − 1(u < 0)| * L_κ(u)
          where τ̂_i corresponds to θ_pred index i.
        - Mean over target quantile dim j, then sum over pred quantile dim i:
            loss_per_sample = (1 / N_QUANTILES) * Σ_i Σ_j ρ_{τ̂_i}(u_{i,j})
        - [RAINBOW 6] Weight each sample by IS weight w_i:
            loss = mean(w_i * loss_per_sample)

        Step 5 – Gradient step
        - ``optimizer.zero_grad(); loss.backward()``.
        - Clip gradients: ``clip_grad_norm_(network.parameters(), max_norm=10)``.
        - ``optimizer.step()``.

        Step 6 – Update PER priorities
        - [RAINBOW 6] Per-sample priority proxy = mean absolute pairwise TD
          error |u| averaged over all (i, j) pairs (before asymmetric weighting).
        - Update the sum-tree: priority_i = |δ_i| + :attr:`per_eps`,
          then raise to the power :attr:`per_alpha` before storing.
        - Anneal β: beta = min(1.0, per_beta_start + steps_done *
          (1.0 − per_beta_start) / per_beta_steps).

        Step 7 – Target network sync
        - Every :attr:`target_update` gradient steps: hard-copy online
          network weights to target network (``target.load_state_dict(...)``).

        Return metrics dict with keys:
          ``loss``, ``mean_priority``, ``beta``, ``mean_q``.
        """
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
        dones_t = torch.as_tensor(batch.dones.astype(np.float32), dtype=torch.float32, device=self.device)
        is_weights_t = torch.as_tensor(batch.weights, dtype=torch.float32, device=self.device)

        beta = min(
          1.0,
          self.per_beta_start
          + self._steps_done * (1.0 - self.per_beta_start) / max(1, self.per_beta_steps),
        )

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
              next_mask = net.valid_action_mask.unsqueeze(0).expand(q_online_next.shape[0], -1, -1)
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

        tau = (2.0 * torch.arange(self.n_quantiles, device=self.device, dtype=torch.float32) + 1.0) / (
          2.0 * float(self.n_quantiles)
        )
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
        priorities = abs_td.detach().mean(dim=priority_reduce_dims).cpu().numpy() + self.per_eps
        if hasattr(batch, "indices") and batch.indices is not None:
          # PrioritizedReplayBuffer applies alpha internally when storing priorities.
          self._last_priority_update_indices = batch.indices
          self._last_priority_update_values = priorities

        metrics = {
          "loss": float(loss.item()),
          "mean_priority": float(np.mean(priorities)),
          "beta": float(beta),
          "mean_q": float(pred_quantiles.detach().mean().item()),
        }
        return metrics

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
            # [RAINBOW 4]
            "n_step": self.n_step,
            # [RAINBOW 3] QR-DQN
            "n_quantiles": self.n_quantiles,
            "kappa": self.kappa,
            # [RAINBOW 6]
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
        # [RAINBOW 4]
        self.n_step = hparams.get("n_step", self.n_step)
        # [RAINBOW 3] QR-DQN
        self.n_quantiles = hparams.get("n_quantiles", self.n_quantiles)
        self.kappa = hparams.get("kappa", self.kappa)
        # [RAINBOW 6]
        self.per_alpha = hparams.get("per_alpha", self.per_alpha)
        self.per_beta_start = hparams.get("per_beta_start", self.per_beta_start)
        self.per_beta_steps = hparams.get("per_beta_steps", self.per_beta_steps)
        self.per_eps = hparams.get("per_eps", self.per_eps)
        self.hidden_dim = hparams.get("hidden_dim", self.hidden_dim)


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------


class RainbowTrainer(BaseTrainer):
    """Off-policy Rainbow trainer with PER and n-step replay."""

    def __init__(
        self,
        bot: RLBot,
        opponent: RLBot,
        env_factory: EnvFactory,
        n_envs: int = 4,
        learning_agent: str = "player_0",
        logger: Optional[TrainingLogger] = None,
        eval_env_factory: Optional[EnvFactory] = None,
        checkpoint_dir: Optional[str | Path] = None,
        eval_interval: Optional[int] = 10_000,
        self_play_manager: Optional[object] = None,
        opponent_selector: Optional[OpponentSelector] = None,
        on_episode_end: Optional[EpisodeEndCallback] = None,
        buffer_size: int = 100_000,
        replay_min_size: int = 2_000,
        batch_size: int = 32,
        collect_steps_per_env: int = 1,
        updates_per_iteration: int = 1,
        replay_dir: str | Path = "replay_store",
        reset_replay: bool = False,
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
        self.buffer_size = int(buffer_size)
        self.replay_min_size = int(replay_min_size)
        self.batch_size = int(batch_size)
        self.collect_steps_per_env = int(collect_steps_per_env)
        self.updates_per_iteration = int(updates_per_iteration)
        self.replay_dir = Path(replay_dir)
        self.reset_replay = bool(reset_replay)

        self._replay: Optional[PrioritizedReplayBuffer] = None
        self._collector_buffer: Optional[NStepBufferWrapper] = None

    def create_buffer(self) -> AbstractBuffer:
        if not hasattr(self.bot, "per_alpha") or not hasattr(self.bot, "per_eps"):
            raise TypeError("RainbowTrainer expects a DQN/Rainbow-style bot with PER hyper-parameters.")

        self._replay = PrioritizedReplayBuffer(
            capacity=self.buffer_size,
            min_size=self.replay_min_size,
            storage_dir=self.replay_dir,
            per_alpha=float(getattr(self.bot, "per_alpha")),
            per_eps=float(getattr(self.bot, "per_eps")),
        )
        if self.reset_replay:
            self._replay.clear()

        n_step = int(getattr(self.bot, "n_step", 1))
        gamma = float(getattr(self.bot, "gamma", 0.99))
        self._collector_buffer = NStepBufferWrapper(self._replay, n_step=n_step, gamma=gamma)
        return self._collector_buffer

    def collect_experience(self, runner: EnvRunner, buffer: AbstractBuffer) -> int:
        runner.collect(buffer=buffer, n_steps=self.collect_steps_per_env)
        return self.n_envs * self.collect_steps_per_env

    def train_step(self, buffer: AbstractBuffer) -> Dict[str, float]:
        del buffer
        if self._replay is None:
            raise RuntimeError("Replay buffer is not initialized.")
        if not self._replay.is_ready:
            return {}

        metric_list = []
        for _ in range(self.updates_per_iteration):
            beta = self._replay.beta_by_step(
                step=int(getattr(self.bot, "_steps_done", 0)),
                beta_start=float(getattr(self.bot, "per_beta_start", 0.4)),
                beta_steps=int(getattr(self.bot, "per_beta_steps", 100_000)),
            )
            batch = self._replay.sample(batch_size=self.batch_size, beta=beta)
            metrics = self.bot.update(batch)

            indices = getattr(self.bot, "_last_priority_update_indices", None)
            priorities = getattr(self.bot, "_last_priority_update_values", None)
            if indices is not None and priorities is not None:
                self._replay.update_priorities(indices=indices, priorities=priorities)
                setattr(self.bot, "_last_priority_update_indices", None)
                setattr(self.bot, "_last_priority_update_values", None)

            metric_list.append(metrics)

        out: Dict[str, float] = {}
        if not metric_list:
            return out

        keys = metric_list[0].keys()
        for key in keys:
            out[key] = float(np.mean([m[key] for m in metric_list]))
        return out

    def train(self, total_steps: int) -> None:
        try:
            super().train(total_steps)
        finally:
            if self._replay is not None:
                self._replay.close()
