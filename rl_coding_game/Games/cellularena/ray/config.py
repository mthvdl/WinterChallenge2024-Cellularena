"""Resolve generic Ray and Cellularena-specific environment settings."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
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


def resolve_run_and_env_settings(
    overrides: Mapping[str, Any] | None = None,
    num_env_runners: int = 0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve the split config while accepting legacy env keys under ``run``."""
    values = overrides or {}
    run_overrides = values.get("run") or {}
    env_overrides = values.get("env") or {}
    if not isinstance(run_overrides, Mapping):
        raise ValueError("The 'run' configuration section must be a mapping.")
    if not isinstance(env_overrides, Mapping):
        raise ValueError("The 'env' configuration section must be a mapping.")

    env_keys = {field.name for field in fields(CellularenaEnvSettings)}
    legacy_env = {key: value for key, value in run_overrides.items() if key in env_keys}
    duplicate_keys = legacy_env.keys() & env_overrides.keys()
    if duplicate_keys:
        raise ValueError(
            "Environment settings cannot appear in both 'run' and 'env': "
            + ", ".join(sorted(duplicate_keys))
        )

    generic_run = {
        key: value for key, value in run_overrides.items() if key not in env_keys
    }
    return (
        settings_dict(RayRunSettings(num_env_runners=num_env_runners), generic_run),
        settings_dict(CellularenaEnvSettings(), {**legacy_env, **env_overrides}),
    )