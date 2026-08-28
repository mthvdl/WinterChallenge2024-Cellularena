"""RLlib adapter for Cellularena's discrete action environment."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import numpy as np
from gymnasium import spaces
from pettingzoo import ParallelEnv

from Games.cellularena.engine.action_env import CellularenaActionEnv
from Games.cellularena.factories import make_action_env
from Games.cellularena.policy.action_mask import ActionMaskBuilder


class FeatureBuilder:
    """Identity feature builder for an environment without custom encoding."""

    def build(self, raw_observation: Any) -> Any:
        return raw_observation


class CellularenaRayWrapper(ParallelEnv):
    """Expose structured features and legal-action masks to RLlib."""

    def __init__(
        self,
        env: CellularenaActionEnv,
        feature_builder: Any = None,
        action_mask_builder: Optional[ActionMaskBuilder] = None,
        flatten_action_mask: bool = False,
    ) -> None:
        self.env = env
        self.feature_builder = feature_builder or FeatureBuilder()
        self.action_mask_builder = action_mask_builder or ActionMaskBuilder()
        self.flatten_action_mask = flatten_action_mask
        self.possible_agents = list(env.possible_agents)
        self.agents = []
        self.metadata = env.metadata

    def observation_space(self, agent: str) -> spaces.Space:
        observation_space = getattr(self.feature_builder, "observation_space", None)
        if observation_space is None:
            observation_space = self.env.observation_space(agent)
        if self.flatten_action_mask:
            return spaces.Box(
                low=-np.inf,
                high=np.inf,
                shape=(int(np.prod(observation_space.shape)) + self.env.action_space(agent).n,),
                dtype=np.float32,
            )
        return spaces.Dict(
            {
                "observations": observation_space,
                "action_mask": spaces.Box(
                    low=0.0,
                    high=1.0,
                    shape=(self.env.action_space(agent).n,),
                    dtype=np.float32,
                ),
            }
        )

    def action_space(self, agent: str) -> spaces.Space:
        return self.env.action_space(agent)

    def _wrapped_observation(self, agent: str, observation: Any) -> Dict[str, np.ndarray]:
        player_idx = self.env._agent_to_idx[agent]
        features = self.feature_builder.build(observation)
        if not isinstance(features, dict):
            features = np.asarray(features, dtype=np.float32)
        wrapped = {
            "observations": features,
            "action_mask": self.action_mask_builder.build(
                self.env._game,
                player_idx,
                self.env.action_space(agent).n,
            ),
        }
        if self.flatten_action_mask:
            return np.concatenate(
                (np.asarray(features, dtype=np.float32).reshape(-1), wrapped["action_mask"])
            ).astype(np.float32)
        return wrapped

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        observations, infos = self.env.reset(seed=seed, options=options)
        self.agents = list(self.env.agents)
        return (
            {agent: self._wrapped_observation(agent, observations[agent]) for agent in self.agents},
            infos,
        )

    def step(self, actions: Dict[str, Any]):
        observations, rewards, terminations, truncations, infos = self.env.step(actions)
        self.agents = list(self.env.agents)
        active_observations = {
            agent: self._wrapped_observation(agent, observations[agent])
            for agent in observations
        }
        return active_observations, rewards, terminations, truncations, infos

    def close(self) -> None:
        self.env.close()


class CellularenaSACWrapper(CellularenaRayWrapper):
    """Expose SAC with the game's structured discrete observation."""


def make_env_creator(
    feature_builder_factory: Callable[[], Any] = FeatureBuilder,
    action_mask_builder_factory: Callable[[], ActionMaskBuilder] = ActionMaskBuilder,
    flatten_action_mask: bool = False,
):
    """Return an RLlib creator with algorithm-specific feature construction."""

    def env_creator(env_config: Optional[Dict[str, Any]] = None):
        from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv

        config = env_config or {}
        base_env = make_action_env(
            seed=config.get("seed"),
            obs_history_steps=config.get("obs_history_steps", 1),
            map_height=config.get("map_height", 8),
            map_width=config.get("map_width"),
            wall_ratio=config.get("wall_ratio"),
            protein_ratio=config.get("protein_ratio"),
            reward_shaping=config.get("reward_shaping", False),
        )
        return ParallelPettingZooEnv(
            CellularenaRayWrapper(
                base_env,
                feature_builder=feature_builder_factory(),
                action_mask_builder=action_mask_builder_factory(),
                flatten_action_mask=flatten_action_mask,
            )
        )

    return env_creator


def make_sac_env_creator(
    feature_builder_factory: Callable[[], Any],
    flatten_action_mask: bool = False,
):
    """Return an RLlib creator for SAC's discrete action interface."""

    def env_creator(env_config: Optional[Dict[str, Any]] = None):
        from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv

        config = env_config or {}
        base_env = make_action_env(
            seed=config.get("seed"),
            obs_history_steps=config.get("obs_history_steps", 1),
            map_height=config.get("map_height", 8),
            map_width=config.get("map_width"),
            wall_ratio=config.get("wall_ratio"),
            protein_ratio=config.get("protein_ratio"),
            reward_shaping=config.get("reward_shaping", False),
        )
        return ParallelPettingZooEnv(
            CellularenaSACWrapper(
                base_env,
                feature_builder=feature_builder_factory(),
                flatten_action_mask=flatten_action_mask,
            )
        )

    return env_creator


def register_cellularena_env(name: str = "cellularena_ray") -> None:
    from Core.ray_env import register_env

    register_env(name, make_env_creator())
