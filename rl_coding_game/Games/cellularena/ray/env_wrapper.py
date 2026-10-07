"""RLlib adapter for Cellularena's discrete action environment."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import numpy as np
from gymnasium import spaces
from pettingzoo import ParallelEnv

from Core.action_mask import ACTION_MASK_KEY
from Games.cellularena.engine.action_env import CellularenaActionEnv
from Games.cellularena.engine.tools.game_recorder import EpisodeRecorder
from Games.cellularena.factories import make_action_env
from Games.cellularena.policy.action_mask import ActionMaskBuilder


class CellularenaRayWrapper(ParallelEnv):
    """Expose raw observations plus the legal-action mask (which needs live game state)."""

    def __init__(
        self,
        env: CellularenaActionEnv,
        action_mask_builder: Optional[ActionMaskBuilder] = None,
        record_replay: bool = False,
    ) -> None:
        self.env = env
        self.action_mask_builder = action_mask_builder or ActionMaskBuilder()
        self.possible_agents = list(env.possible_agents)
        self.agents = []
        self.metadata = env.metadata
        self.recorder = EpisodeRecorder() if record_replay else None
        # Kept separately because vector envs may auto-reset before callbacks read it.
        self.completed_replay_frames: list[dict[str, Any]] | None = None

    def observation_space(self, agent: str) -> spaces.Space:
        return spaces.Dict(
            {
                **self.env.observation_space(agent).spaces,
                ACTION_MASK_KEY: spaces.Box(
                    low=0.0,
                    high=1.0,
                    shape=(self.env.action_space(agent).n,),
                    dtype=np.float32,
                ),
            }
        )

    def action_space(self, agent: str) -> spaces.Space:
        return self.env.action_space(agent)

    def _wrapped_observation(self, agent: str, observation: Dict[str, Any]) -> Dict[str, Any]:
        mask = self.action_mask_builder.build(
            self.env._game,
            self.env._agent_to_idx[agent],
            self.env.action_space(agent).n,
        )
        return {**observation, ACTION_MASK_KEY: mask}

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        observations, infos = self.env.reset(seed=seed, options=options)
        self.agents = list(self.env.agents)
        if self.recorder is not None:
            self.recorder.start(self.env._game)
        return (
            {agent: self._wrapped_observation(agent, observations[agent]) for agent in self.agents},
            infos,
        )

    def step(self, actions: Dict[str, Any]):
        observations, rewards, terminations, truncations, infos = self.env.step(actions)
        self.agents = list(self.env.agents)
        if self.recorder is not None:
            self.recorder.record_step(self.env._game)
            if not self.agents or all(terminations.values()) or all(truncations.values()):
                self.completed_replay_frames = self.recorder.frames
        active_observations = {
            agent: self._wrapped_observation(agent, observations[agent])
            for agent in observations
        }
        return active_observations, rewards, terminations, truncations, infos

    def close(self) -> None:
        self.env.close()


def make_env_creator(
    action_mask_builder_factory: Callable[[], ActionMaskBuilder] = ActionMaskBuilder,
):
    """Return an RLlib creator; features are built by the env-to-module connector."""

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
                action_mask_builder=action_mask_builder_factory(),
                record_replay=config.get("record_replay", False),
            )
        )

    return env_creator


def register_cellularena_env(name: str = "cellularena_ray") -> None:
    from Core.ray_env import register_env

    register_env(name, make_env_creator())
