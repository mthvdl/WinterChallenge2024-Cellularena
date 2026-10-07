"""Resolve generic Ray and Cellularena-specific environment settings."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from Core.ray_config import RayRunSettings, settings_dict


@dataclass(frozen=True)
class CellularenaEnvSettings:
    map_height: int = 8
    map_width: int | None = None
    wall_ratio: float | None = None
    protein_ratio: float | None = None
    obs_history_steps: int = 1
    reward_shaping: bool = False


TOP_LEVEL_SECTIONS = {"env", "experiment", "league_pool", "sac", "dqn"}
EXPERIMENT_KEYS = {
    "iterations",
    "checkpoint_interval",
    "replay_capacity",
    "replay_buffer_rotation",
    "train_batch_size",
    "num_steps_sampled_before_learning_starts",
    "gamma",
    "replay_alpha",
    "replay_beta",
}
EXPERIMENT_SUBSECTION_KEYS = {
    "runner": {"num_env_runners", "num_cpus_per_env_runner"},
    "learner": {"num_cpus_for_main_process", "num_gpus"},
    "evaluator": {
        "evaluation_interval",
        "evaluation_num_env_runners",
        "evaluation_duration",
        "evaluation_duration_unit",
        "evaluation_explore",
        "save_evaluation_play",
    },
}


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    value = value or {}
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{name}' configuration section must be a mapping.")
    return value


def _reject_unknown(values: Mapping[str, Any], allowed: set[str], name: str) -> None:
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(
            f"Unknown '{name}' configuration keys: " + ", ".join(sorted(unknown))
        )


def resolve_run_and_env_settings(
    overrides: Mapping[str, Any] | None = None,
    num_env_runners: int = 0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve the `experiment` (with runner/learner/evaluator) and `env` sections."""
    values = _mapping(overrides, "root")
    _reject_unknown(values, TOP_LEVEL_SECTIONS, "root")
    experiment = _mapping(values.get("experiment"), "experiment")
    _reject_unknown(
        experiment, EXPERIMENT_KEYS | EXPERIMENT_SUBSECTION_KEYS.keys(), "experiment"
    )
    run = {key: experiment[key] for key in EXPERIMENT_KEYS & experiment.keys()}
    for section, keys in EXPERIMENT_SUBSECTION_KEYS.items():
        section_values = _mapping(experiment.get(section), f"experiment.{section}")
        _reject_unknown(section_values, keys, f"experiment.{section}")
        run.update(section_values)
    env = _mapping(values.get("env"), "env")
    return (
        settings_dict(RayRunSettings(num_env_runners=num_env_runners), run),
        settings_dict(CellularenaEnvSettings(), env),
    )