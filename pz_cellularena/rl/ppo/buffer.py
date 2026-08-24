from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from rl.buffer import RolloutBuffer
from rl.experience import RolloutBatch, Transition


def _pack_obs(obs_list: List[Dict[str, np.ndarray]]) -> Dict[str, np.ndarray]:
    """Stack a list of single-sample obs dicts into a batched obs dict."""
    keys = obs_list[0].keys()
    return {k: np.stack([o[k] for o in obs_list]) for k in keys}


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
