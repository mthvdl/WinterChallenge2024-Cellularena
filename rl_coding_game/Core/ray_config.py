"""Shared, editable configuration values for local RLlib training."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class RayRunSettings:
    map_height: int = 8
    obs_history_steps: int = 1
    num_env_runners: int = 0
    num_gpus: int = 0


@dataclass(frozen=True)
class DQNSettings:
    num_atoms: int = 1
    noisy: bool = True
    dueling: bool = True
    double_q: bool = True
    train_batch_size: int = 32
    replay_capacity: int = 10_000
    replay_alpha: float = 0.6
    replay_beta: float = 0.4


@dataclass(frozen=True)
class SACSettings:
    train_batch_size: int = 32
    gamma: float = 0.99
    actor_lr: float = 3e-4
    critic_lr: float = 3e-4


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