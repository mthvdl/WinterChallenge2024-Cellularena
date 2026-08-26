"""Shared helpers for registering PettingZoo environments with RLlib."""
from __future__ import annotations

from abc import ABCMeta
from collections.abc import Callable
from typing import Any


def make_multi_agent_replay_buffer():
	"""Return RLlib's new-stack multi-agent episode replay buffer."""
	from ray.rllib.utils.replay_buffers import MultiAgentPrioritizedEpisodeReplayBuffer

	class ReplayBufferType(ABCMeta):
		def __contains__(cls, item: object) -> bool:
			return str(item) in cls.__name__

	class EpisodeCompatibleReplayBuffer(
		MultiAgentPrioritizedEpisodeReplayBuffer,
		metaclass=ReplayBufferType,
	):
		"""Work around RLlib checking a resolved class as though it were a string."""

	return EpisodeCompatibleReplayBuffer


def register_env(name: str, env_creator: Callable[[dict[str, Any]], Any]) -> None:
	"""Register an RLlib environment without importing Ray at module import time."""
	from ray.tune.registry import register_env as _register_env

	_register_env(name, env_creator)
