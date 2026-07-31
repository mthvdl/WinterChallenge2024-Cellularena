"""Game-agnostic n-step transition wrapper.

This module converts 1-step transitions into n-step returns while preserving
the underlying buffer interface (e.g., PrioritizedReplayBuffer).
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List

from rl.buffer import AbstractBuffer
from rl.experience import RolloutBatch, Transition


class NStepBufferWrapper(AbstractBuffer):
    """Wrap an existing buffer and push n-step transitions into it.

    The wrapper is environment-agnostic: episodes are separated using
    ``transition.info['env_idx']`` when present, and default to ``0``.
    """

    def __init__(self, base_buffer: AbstractBuffer, n_step: int, gamma: float) -> None:
        self.base_buffer = base_buffer
        self.n_step = max(1, int(n_step))
        self.gamma = float(gamma)
        self._queues: Dict[int, Deque[Transition]] = {}

    def add(self, transition: Transition) -> None:
        env_idx = int(transition.info.get("env_idx", 0))
        if env_idx not in self._queues:
            self._queues[env_idx] = deque()

        q = self._queues[env_idx]
        q.append(transition)

        if transition.done:
            while q:
                seq = list(q)[: self.n_step]
                self.base_buffer.add(self._aggregate(seq))
                q.popleft()
            q.clear()
            return

        if len(q) >= self.n_step:
            seq = list(q)[: self.n_step]
            self.base_buffer.add(self._aggregate(seq))
            q.popleft()

    def sample(self, batch_size: int) -> RolloutBatch:
        return self.base_buffer.sample(batch_size)

    def clear(self) -> None:
        self._queues.clear()
        self.base_buffer.clear()

    def __len__(self) -> int:
        return len(self.base_buffer)

    @property
    def is_ready(self) -> bool:
        return self.base_buffer.is_ready

    def __getattr__(self, name: str):
        return getattr(self.base_buffer, name)

    def _aggregate(self, seq: List[Transition]) -> Transition:
        first = seq[0]
        last = seq[-1]

        reward = 0.0
        for k, tr in enumerate(seq):
            reward += (self.gamma ** k) * float(tr.reward)

        info = dict(first.info)
        info["n_step_len"] = len(seq)

        return Transition(
            obs=first.obs,
            action=first.action,
            reward=reward,
            next_obs=last.next_obs,
            done=bool(any(t.done for t in seq)),
            log_prob=first.log_prob,
            value=first.value,
            info=info,
        )