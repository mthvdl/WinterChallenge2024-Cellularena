"""RLlib adapter for Cellularena's discrete action environment."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import numpy as np
from gymnasium import spaces
from pettingzoo import ParallelEnv

from Games.cellularena.engine.action_env import CellularenaActionEnv
from Games.cellularena.factories import make_action_env
from Games.cellularena.policy.action_mask import ActionMaskBuilder
from Games.cellularena.ray.sac.feature_builder import FEATURE_DIM, SACFeatureBuilder


class CellularenaRayWrapper(ParallelEnv):
    """Expose structured features and legal-action masks to RLlib."""

    def __init__(
        self,
        env: CellularenaActionEnv,
        feature_builder: Any = None,
        action_mask_builder: Optional[ActionMaskBuilder] = None,
    ) -> None:
        self.env = env
        self.feature_builder = feature_builder or SACFeatureBuilder()
        self.action_mask_builder = action_mask_builder or ActionMaskBuilder()
        self.possible_agents = list(env.possible_agents)
        self.agents = []
        self.metadata = env.metadata

    def observation_space(self, agent: str) -> spaces.Space:
        del agent
        return spaces.Dict(
            {
                "observations": spaces.Box(
                    low=-np.inf,
                    high=np.inf,
                    shape=(FEATURE_DIM,),
                    dtype=np.float32,
                ),
                "action_mask": spaces.Box(
                    low=0.0,
                    high=1.0,
                    shape=(self.env.action_space(self.possible_agents[0]).n,),
                    dtype=np.float32,
                ),
            }
        )

    def action_space(self, agent: str) -> spaces.Space:
        return self.env.action_space(agent)

    def _wrapped_observation(self, agent: str, observation: Any) -> Dict[str, np.ndarray]:
        player_idx = self.env._agent_to_idx[agent]
        return {
            "observations": np.asarray(self.feature_builder.build(observation), dtype=np.float32),
            "action_mask": self.action_mask_builder.build(self.env._game, player_idx),
        }

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


def make_env_creator(
    feature_builder_factory: Callable[[], Any] = SACFeatureBuilder,
    action_mask_builder_factory: Callable[[], ActionMaskBuilder] = ActionMaskBuilder,
):
    """Return an RLlib creator with algorithm-specific feature construction."""

    def env_creator(env_config: Optional[Dict[str, Any]] = None):
        from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv

        config = env_config or {}
        base_env = make_action_env(
            seed=config.get("seed"),
            obs_history_steps=config.get("obs_history_steps", 1),
            map_height=config.get("map_height", 8),
        )
        return ParallelPettingZooEnv(
            CellularenaRayWrapper(
                base_env,
                feature_builder=feature_builder_factory(),
                action_mask_builder=action_mask_builder_factory(),
            )
        )

    return env_creator


def register_cellularena_env(name: str = "cellularena_ray") -> None:
    from Core.ray_env import register_env

    register_env(name, make_env_creator())
