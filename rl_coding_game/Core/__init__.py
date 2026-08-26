"""RL training infrastructure package.

Exports are loaded lazily to keep lightweight utilities usable even when
optional heavy dependencies (for example torch) are not installed.
"""

from __future__ import annotations

import importlib


_EXPORTS = {
    "RLBot": "rl.base_bot",
    "BaseNetwork": "rl.base_network",
    "BaseTrainer": "rl.base_trainer",
    "AbstractBuffer": "rl.buffer",
    "RolloutBuffer": "rl.buffer",
    "ReplayBuffer": "rl.buffer",
    "PrioritizedReplayBuffer": "rl.prioritized_replay",
    "NStepBufferWrapper": "rl.n_step",
    "EnvRunner": "rl.env_runner",
    "RolloutBatch": "rl.experience",
    "Transition": "rl.experience",
    "TrainingLogger": "rl.logger",
    "RainbowTrainer": "rl.rainbow_trainer",
    "LeagueSelfPlayManager": "rl.self_play",
    "OpponentRole": "rl.self_play",
    "MatchBucket": "rl.self_play",
}

__all__ = [
    "RLBot",
    "BaseNetwork",
    "BaseTrainer",
    "AbstractBuffer",
    "RolloutBuffer",
    "ReplayBuffer",
    "PrioritizedReplayBuffer",
    "NStepBufferWrapper",
    "EnvRunner",
    "RolloutBatch",
    "Transition",
    "TrainingLogger",
    "RainbowTrainer",
    "LeagueSelfPlayManager",
    "OpponentRole",
    "MatchBucket",
]


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module 'rl' has no attribute '{name}'")
    module = importlib.import_module(module_name)
    return getattr(module, name)
