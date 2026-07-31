"""Experience data-structures shared by all RL algorithms."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class Transition:
    """A single (s, a, r, s', done) transition for one agent.

    All array-valued fields use numpy; dtype and shape depend on the
    environment and are validated by the concrete buffer implementation.
    """

    # Observation at time t (dict matching the PettingZoo env's observation_space)
    obs: Dict[str, np.ndarray]

    # Action taken at time t; shape and dtype match the env's action_space
    action: np.ndarray

    # Scalar reward received after the action
    reward: float

    # Observation at time t+1 (same structure as obs)
    next_obs: Dict[str, np.ndarray]

    # True when the episode ended (terminal or truncated)
    done: bool

    # Optional log-probability of the action under the behaviour policy.
    # Required by on-policy algorithms (PPO). Off-policy algorithms may
    # leave this as None.
    log_prob: Optional[float] = None

    # Optional value-function estimate V(s_t). Required by actor-critic
    # algorithms (PPO, A2C). Left as None for value-free methods.
    value: Optional[float] = None

    # Boolean action mask for the current state, shape matching action_space.
    # None when the env does not implement action masking.
    action_mask: Optional[np.ndarray] = None

    # Boolean action mask for the next state (used for masked Double-DQN
    # target action selection). None when unavailable or at episode end.
    next_action_mask: Optional[np.ndarray] = None

    # Any extra algorithm-specific data (e.g. hidden state for recurrent nets)
    info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RolloutBatch:
    """A batch of transitions packed into contiguous numpy arrays.

    Created by :class:`~rl.buffer.AbstractBuffer` and consumed by
    ``RLBot.update()``.  Each array's first dimension is the batch size.

    Dict observations are stored as flat dicts of arrays rather than lists of
    dicts, which is more efficient for vectorised network forward-passes.
    """

    # Each key maps to a batched array whose shape matches the env's observation_space.
    obs: Dict[str, np.ndarray]

    # shape: (B, *action_shape); matches the env's action_space
    actions: np.ndarray

    # shape: (B,)
    rewards: np.ndarray

    # Same structure as obs
    next_obs: Dict[str, np.ndarray]

    # shape: (B,) dtype bool
    dones: np.ndarray

    # shape: (B,)  — may be all-NaN for off-policy algorithms
    log_probs: np.ndarray

    # shape: (B,)  — may be all-NaN for value-free algorithms
    values: np.ndarray

    # shape: (B,) - replay buffer indices (used by PER).
    indices: Optional[np.ndarray] = None

    # shape: (B,) - importance-sampling weights (used by PER).
    weights: Optional[np.ndarray] = None

    # shape: (B, *action_shape) bool — current-state action masks.
    # None when the env does not implement action masking.
    action_masks: Optional[np.ndarray] = None

    # shape: (B, *action_shape) bool — next-state action masks (for Double DQN).
    # None when unavailable.
    next_action_masks: Optional[np.ndarray] = None
