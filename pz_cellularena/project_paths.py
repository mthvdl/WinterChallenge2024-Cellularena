"""Project path conventions for shared game data and per-experiment artifacts.

Layout
------
- Shared, game-level data:
  data/games/<game>/replays

- Per-experiment data:
  experiments/<game>/<experiment>/runs
  experiments/<game>/<experiment>/replay_store
  experiments/<game>/<experiment>/league_pool
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parent


def shared_game_root(game: str) -> Path:
    return ROOT / "data" / "games" / game


def shared_replays_dir(game: str) -> Path:
    return shared_game_root(game) / "replays"


def experiment_root(game: str, experiment: str) -> Path:
    return ROOT / "experiments" / game / experiment


def experiment_run_dir(game: str, experiment: str) -> Path:
    return experiment_root(game, experiment) / "runs"


def experiment_replay_store_dir(game: str, experiment: str) -> Path:
    return experiment_root(game, experiment) / "replay_store"


def experiment_snapshot_dir(game: str, experiment: str) -> Path:
    return experiment_root(game, experiment) / "league_pool"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
