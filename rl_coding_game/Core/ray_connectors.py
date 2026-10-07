"""Env-to-module ConnectorV2 pieces shared by all games."""
from __future__ import annotations

import abc
from functools import partial
from typing import Any

import gymnasium as gym
import numpy as np
from ray.rllib.connectors.env_to_module.observation_preprocessor import (
    MultiAgentObservationPreprocessor,
)

from Core.action_mask import ACTION_MASK_KEY, OBSERVATIONS_KEY


class FeaturePreprocessor(MultiAgentObservationPreprocessor, abc.ABC):
    """Turn raw `{..., action_mask}` env observations into `{observations, action_mask}` module inputs.

    Subclasses implement `feature_space()` and `build_features()`. The result is
    written back into the episode, so the replay buffer and learner see what the module saw.
    """

    flatten: bool = False

    @abc.abstractmethod
    def feature_space(self, raw_space: gym.spaces.Dict) -> gym.spaces.Box:
        """Space of the array returned by `build_features()`, given one agent's raw env space."""

    @abc.abstractmethod
    def build_features(self, raw_observation: dict[str, Any]) -> np.ndarray:
        """Encode one agent's raw observation."""

    def _agent_space(self, raw_space: gym.spaces.Dict) -> gym.Space:
        features = self.feature_space(raw_space)
        mask = raw_space[ACTION_MASK_KEY]
        if self.flatten:
            size = int(np.prod(features.shape)) + int(np.prod(mask.shape))
            return gym.spaces.Box(-np.inf, np.inf, shape=(size,), dtype=np.float32)
        return gym.spaces.Dict({OBSERVATIONS_KEY: features, ACTION_MASK_KEY: mask})

    def recompute_output_observation_space(
        self, input_observation_space: gym.Space, input_action_space: gym.Space
    ) -> gym.Space:
        return gym.spaces.Dict(
            {
                agent_id: self._agent_space(space)
                for agent_id, space in input_observation_space.spaces.items()
            }
        )

    def preprocess(self, observations: dict[Any, Any], episode: Any) -> dict[Any, Any]:
        return {agent_id: self.transform(obs) for agent_id, obs in observations.items()}

    def transform(self, raw_observation: dict[str, Any]) -> Any:
        features = np.asarray(self.build_features(raw_observation), dtype=np.float32)
        if not np.isfinite(features).all():
            raise RuntimeError(f"{type(self).__name__} produced non-finite features.")
        mask = np.asarray(raw_observation[ACTION_MASK_KEY], dtype=np.float32)
        if self.flatten:
            return np.concatenate((features.reshape(-1), mask))
        return {OBSERVATIONS_KEY: features, ACTION_MASK_KEY: mask}


def _build_env_to_module(env: Any = None, spaces: Any = None, device: Any = None, *, preprocessor_class: type, kwargs: dict[str, Any]):
    return preprocessor_class(**kwargs)


def env_to_module_connector(preprocessor_class: type[FeaturePreprocessor], **kwargs: Any):
    """Picklable value for `config.env_runners(env_to_module_connector=...)`."""
    return partial(_build_env_to_module, preprocessor_class=preprocessor_class, kwargs=kwargs)
