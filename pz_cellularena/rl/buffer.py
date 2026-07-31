"""Abstract and concrete experience buffers.

Hierarchy
---------
AbstractBuffer   (ABC)
  ├── RolloutBuffer   – fixed-size, overwritten each iteration (on-policy: PPO, A2C)
  └── ReplayBuffer    – circular ring-buffer with random sampling (off-policy: DQN, SAC)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from rl.experience import RolloutBatch, Transition


class AbstractBuffer(ABC):
    """Common interface for all experience storage types."""

    @abstractmethod
    def add(self, transition: Transition) -> None:
        """Store a single transition."""

    @abstractmethod
    def sample(self, batch_size: int) -> RolloutBatch:
        """Return a :class:`~rl.experience.RolloutBatch` of *batch_size* transitions.

        On-policy buffers typically ignore *batch_size* and return the full
        buffer; off-policy buffers sample uniformly at random.
        """

    @abstractmethod
    def clear(self) -> None:
        """Remove all stored transitions (called at the start of each iteration
        for on-policy algorithms)."""

    @abstractmethod
    def __len__(self) -> int:
        """Return the number of transitions currently stored."""

    @property
    def is_ready(self) -> bool:
        """Return True when the buffer holds enough data to sample from.

        Concrete classes may override to enforce a minimum fill level.
        """
        return len(self) > 0


class RolloutBuffer(AbstractBuffer):
    """Fixed-capacity buffer for **on-policy** algorithms (PPO, A2C, …).

    Transitions are collected by :class:`~rl.env_runner.EnvRunner` until the
    buffer is full, then consumed by :meth:`~rl.base_bot.RLBot.update`, and
    finally cleared before the next rollout.

    Parameters
    ----------
    capacity:
        Maximum number of transitions to store before the buffer is
        considered full.  Typically ``n_envs * n_steps_per_env``.
    """

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._storage: list[Transition] = []

    # ------------------------------------------------------------------
    # AbstractBuffer interface
    # ------------------------------------------------------------------

    def add(self, transition: Transition) -> None:
        if len(self._storage) < self.capacity:
            self._storage.append(transition)

    def sample(self, batch_size: int = -1) -> RolloutBatch:
        """Pack the entire buffer into a :class:`~rl.experience.RolloutBatch`.

        *batch_size* is ignored; all stored transitions are returned.
        Subclasses may add advantage estimation here.
        """
        raise NotImplementedError(
            "RolloutBuffer.sample() must be implemented by the algorithm-specific "
            "subclass (e.g. PPO needs to compute advantages before packing)."
        )

    def clear(self) -> None:
        self._storage.clear()

    def __len__(self) -> int:
        return len(self._storage)

    @property
    def is_full(self) -> bool:
        """True when the buffer has reached its capacity."""
        return len(self._storage) >= self.capacity


class ReplayBuffer(AbstractBuffer):
    """Circular ring-buffer for **off-policy** algorithms (DQN, SAC, …).

    New transitions overwrite the oldest ones once *capacity* is reached.
    :meth:`sample` returns a uniformly random batch (no replacement).

    Parameters
    ----------
    capacity:
        Maximum number of transitions to retain (e.g. 100_000–1_000_000).
    min_size:
        Minimum number of transitions required before :attr:`is_ready` returns
        True.  Prevents training from starting on an under-filled buffer.
    """

    def __init__(self, capacity: int, min_size: int = 1000) -> None:
        self.capacity = capacity
        self.min_size = min_size
        self._storage: list[Optional[Transition]] = [None] * capacity
        self._ptr: int = 0
        self._size: int = 0

    # ------------------------------------------------------------------
    # AbstractBuffer interface
    # ------------------------------------------------------------------

    def add(self, transition: Transition) -> None:
        self._storage[self._ptr] = transition
        self._ptr = (self._ptr + 1) % self.capacity
        self._size = min(self._size + 1, self.capacity)

    def sample(self, batch_size: int) -> RolloutBatch:
        """Uniformly sample *batch_size* transitions (without replacement).

        Must be implemented by a concrete subclass that knows how to pack
        :class:`~rl.experience.Transition` objects into numpy arrays.
        """
        raise NotImplementedError(
            "ReplayBuffer.sample() must be implemented by the algorithm-specific "
            "subclass (e.g. DQN may want to use prioritised sampling)."
        )

    def clear(self) -> None:
        self._storage = [None] * self.capacity
        self._ptr = 0
        self._size = 0

    def __len__(self) -> int:
        return self._size

    @property
    def is_ready(self) -> bool:
        return self._size >= self.min_size
