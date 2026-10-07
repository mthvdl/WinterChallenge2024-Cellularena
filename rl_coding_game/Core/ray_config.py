"""Shared, editable configuration values for local RLlib training."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class RayRunSettings:
    iterations: int = 1
    checkpoint_interval: int = 0
    replay_capacity: int = 10_000
    replay_buffer_rotation: bool = True
    train_batch_size: int | None = None
    num_steps_sampled_before_learning_starts: int | None = None
    gamma: float | None = None
    replay_alpha: float | None = None
    replay_beta: float | None = None
    evaluation_interval: int = 0
    evaluation_num_env_runners: int = 0
    evaluation_duration: int = 10
    evaluation_duration_unit: str = "episodes"
    evaluation_explore: bool = False
    save_evaluation_play: bool = False
    num_env_runners: int = 0
    num_cpus_per_env_runner: int = 1
    num_cpus_for_main_process: int = 2
    num_gpus: int = 0


@dataclass(frozen=True)
class LeaguePoolSettings:
    enabled: bool = False
    max_size: int = 8


@dataclass(frozen=True)
class DQNSettings:
    num_atoms: int = 1
    noisy: bool = True
    dueling: bool = True
    double_q: bool = True
    training_intensity: float | None = None


def load_overrides(path: str | Path) -> dict[str, Any]:
    """Load JSON or YAML overrides, preserving algorithm-specific sections."""
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")
    if config_path.suffix.lower() == ".json":
        values = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("YAML config files require the PyYAML package.") from exc
        values = yaml.safe_load(text)
    if not isinstance(values, dict):
        raise ValueError(f"Configuration file must contain a mapping: {config_path}")
    return values


def settings_dict(settings: Any, overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return dataclass defaults merged with explicit overrides."""
    values = asdict(settings)
    if overrides:
        unknown = set(overrides) - set(values)
        if unknown:
            raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
        values.update(overrides)
    return values


def validate_sampled_episodes(*, samples: list[Any], **kwargs: Any) -> None:
    """RLlib `on_sample_end` hook: reject unfinished or non-finite episodes on the EnvRunner."""
    import numpy as np
    import tree

    for episode in samples:
        if not episode.is_done:
            raise RuntimeError(f"EnvRunner returned unfinished episode {episode.id_}.")
        for agent_id, agent_episode in episode.agent_episodes.items():
            for column, data in (
                ("actions", agent_episode.get_actions()),
                ("rewards", agent_episode.get_rewards()),
            ):
                for leaf in tree.flatten(data):
                    if not np.isfinite(np.asarray(leaf, dtype=np.float64)).all():
                        raise RuntimeError(
                            f"Non-finite {column} for agent {agent_id} in episode {episode.id_}."
                        )


def complete_episodes_only(config: Any) -> Any:
    """Only whole, validated games reach the replay buffer; any env error stops training."""
    return (
        config.env_runners(batch_mode="complete_episodes")
        .fault_tolerance(
            restart_failed_env_runners=False,
            restart_failed_sub_environments=False,
            ignore_env_runner_failures=False,
        )
        .callbacks(on_sample_end=validate_sampled_episodes)
    )