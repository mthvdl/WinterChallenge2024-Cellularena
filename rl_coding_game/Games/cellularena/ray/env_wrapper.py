"""RLlib observation contract for the Cellularena action environment."""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
from gymnasium import spaces
from gymnasium.spaces.utils import flatten, flatten_space
from pettingzoo import ParallelEnv

from Games.cellularena.engine.action_env import CellularenaActionEnv
from Games.cellularena.factories import make_action_env


class CellularenaRayWrapper(ParallelEnv):
	"""Expose transformed observations and legal actions to RLlib."""

	def __init__(self, env: CellularenaActionEnv, continuous_actions: bool = False, observation_mapper: Any = None) -> None:
		self.env = env
		self.continuous_actions = continuous_actions
		self.observation_mapper = observation_mapper
		self.possible_agents = list(env.possible_agents)
		self.agents = []
		self.metadata = env.metadata

	def observation_space(self, agent: str) -> spaces.Space:
		if self.observation_mapper is not None:
			obs_dim = int(self.observation_mapper.output_dim(self._native_observation_space(agent)))
		else:
			native_space = self._native_observation_space(agent)
			obs_dim = int(np.prod(flatten_space(native_space).shape))
		mask_dim = self.env.action_space(agent).n
		return spaces.Box(
			low=np.concatenate((np.full(obs_dim, -np.inf, dtype=np.float32), np.zeros(mask_dim, dtype=np.float32))),
			high=np.concatenate((np.full(obs_dim, np.inf, dtype=np.float32), np.ones(mask_dim, dtype=np.float32))),
			dtype=np.float32,
		)

	def _native_observation_space(self, agent: str) -> spaces.Dict:
		obs_spaces = dict(self.env.observation_space(agent).spaces)
		obs_spaces["self_player_idx"] = spaces.Box(0, 1, shape=(1,), dtype=np.int32)
		return spaces.Dict(obs_spaces)

	def action_space(self, agent: str) -> spaces.Space:
		if self.continuous_actions:
			return spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
		return self.env.action_space(agent)

	def _native_action(self, action: Any) -> int:
		if not self.continuous_actions:
			return int(action)
		from Games.cellularena.engine.action_env import N_ACTIONS

		value = float(np.asarray(action, dtype=np.float32).reshape(-1)[0])
		position = np.clip((value + 1.0) * 0.5, 0.0, 1.0)
		return int(np.rint(position * (N_ACTIONS - 1)))

	def transform_observation(self, agent: str, observation: Any) -> Any:
		"""Transform the native observation before it reaches an RLlib module."""
		if self.observation_mapper is not None:
			import torch

			return self.observation_mapper.obs_to_tensor(observation, torch.device("cpu")).numpy()
		return observation

	def action_mask(self, agent: str) -> np.ndarray:
		"""Return a flat binary mask where one means that an action is legal."""
		return np.asarray(self.env.action_mask(agent), dtype=np.int8).reshape(-1)

	def _wrapped_observation(self, agent: str, observation: Any) -> Dict[str, Any]:
		transformed_observation = self.transform_observation(agent, observation)
		if self.observation_mapper is None:
			transformed_observation = flatten(self._native_observation_space(agent), transformed_observation)
		transformed = np.asarray(transformed_observation, dtype=np.float32).reshape(-1)
		return np.concatenate((transformed, self.action_mask(agent).astype(np.float32)))

	def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
		observations, infos = self.env.reset(seed=seed, options=options)
		self.agents = list(self.env.agents)
		return (
			{agent: self._wrapped_observation(agent, observations[agent]) for agent in self.agents},
			infos,
		)

	def step(self, actions: Dict[str, Any]):
		native_actions = {
			agent: self._native_action(action) for agent, action in actions.items()
		}
		observations, rewards, terminations, truncations, infos = self.env.step(native_actions)
		self.agents = list(self.env.agents)
		active_observations = {
			agent: self._wrapped_observation(agent, observations[agent])
			for agent in observations
		}
		return active_observations, rewards, terminations, truncations, infos

	def close(self) -> None:
		self.env.close()


def make_env_creator(continuous_actions: bool = False):
	"""Return an RLlib creator that builds a new wrapped env per worker."""

	def env_creator(env_config: Optional[Dict[str, Any]] = None):
		from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv

		config = env_config or {}
		base_env = make_action_env(
			seed=config.get("seed"),
			obs_history_steps=config.get("obs_history_steps", 1),
			map_height=config.get("map_height", 8),
		)
		return ParallelPettingZooEnv(
			CellularenaRayWrapper(base_env, continuous_actions=continuous_actions)
		)

	return env_creator


def register_cellularena_env(name: str = "cellularena_ray") -> None:
	"""Register the wrapped environment under an RLlib registry name."""
	from Core.ray_env import register_env

	register_env(name, make_env_creator())
