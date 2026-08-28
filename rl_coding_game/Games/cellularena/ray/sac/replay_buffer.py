"""Replay buffers that avoid sampling non-trainable (frozen opponent) modules."""
from __future__ import annotations

from abc import ABCMeta
from typing import Any, List, Optional

from ray.rllib.utils.replay_buffers.multi_agent_episode_buffer import (
    MultiAgentEpisodeReplayBuffer,
)
from ray.rllib.utils.replay_buffers.multi_agent_prioritized_episode_buffer import (
    MultiAgentPrioritizedEpisodeReplayBuffer,
)


class _ModulesToSampleMixin:
    """Defaults every `sample()` call to `modules_to_sample`.

    Frozen league/opponent episodes still get added to the buffer, but RLlib's
    DQN/SAC training step calls `sample()` without restricting modules, drawing
    a full extra batch per opponent policy id that `Learner.should_module_be_updated`
    then discards before the forward pass. Defaulting `modules_to_sample` here
    skips that wasted sampling and connector work.
    """

    def __init__(self, *args: Any, modules_to_sample: Optional[List[str]] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._default_modules_to_sample = list(modules_to_sample) if modules_to_sample else None

    def sample(self, *args: Any, modules_to_sample: Optional[List[str]] = None, **kwargs: Any):
        if modules_to_sample is None:
            modules_to_sample = self._default_modules_to_sample
        return super().sample(*args, modules_to_sample=modules_to_sample, **kwargs)


class _MatchesBaseBufferNameMeta(ABCMeta):
    """Lets a subclass satisfy RLlib SAC's exact-string `replay_buffer_config`
    validation and its later `"...Buffer" in config["type"]` substring checks.

    `SACConfig.validate()` checks `replay_buffer_config["type"] not in
    [<hardcoded buffer name strings>]` with no `issubclass()` fallback (unlike
    DQN's equivalent check), and `Algorithm._create_local_replay_buffer_if_necessary`
    does `"EpisodeReplayBuffer" in config["replay_buffer_config"]["type"]` — both
    assume `type` is always a string, even though buffer construction itself
    (`from_config`) accepts a class directly.
    """

    def __eq__(cls, other: Any) -> bool:
        if isinstance(other, str):
            return any(other == base.__name__ for base in cls.__mro__)
        return NotImplemented

    def __hash__(cls) -> int:
        return type.__hash__(cls)

    def __contains__(cls, item: Any) -> bool:
        item = str(item)
        return any(item in base.__name__ for base in cls.__mro__)


class TrainableOnlySampleReplayBuffer(
    _ModulesToSampleMixin, MultiAgentEpisodeReplayBuffer, metaclass=_MatchesBaseBufferNameMeta
):
    pass


class TrainableOnlySamplePrioritizedReplayBuffer(
    _ModulesToSampleMixin,
    MultiAgentPrioritizedEpisodeReplayBuffer,
    metaclass=_MatchesBaseBufferNameMeta,
):
    pass


REPLAY_BUFFER_TYPES = {
    "MultiAgentEpisodeReplayBuffer": TrainableOnlySampleReplayBuffer,
    "MultiAgentPrioritizedEpisodeReplayBuffer": TrainableOnlySamplePrioritizedReplayBuffer,
}
