"""Project path conventions for shared game data and per-experiment artifacts.

Layout
------
- Preferred (game-first):
    Games/<game>/experiments/shared/replays
    Games/<game>/experiments/<experiment>/runs
    Games/<game>/experiments/<experiment>/replay_store
    Games/<game>/experiments/<experiment>/league_pool
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def game_root(game: str) -> Path:
    return ROOT / "Games" / game


def shared_game_root(game: str) -> Path:
    return game_root(game) / "experiments" / "shared"


def shared_replays_dir(game: str) -> Path:
    return shared_game_root(game) / "replays"


def experiment_root(game: str, experiment: str) -> Path:
    return game_root(game) / "experiments" / experiment


def experiment_run_dir(game: str, experiment: str) -> Path:
    return experiment_root(game, experiment) / "runs"


def experiment_replay_store_dir(game: str, experiment: str) -> Path:
    return experiment_root(game, experiment) / "replay_store"


def experiment_snapshot_dir(game: str, experiment: str) -> Path:
    return experiment_root(game, experiment) / "league_pool"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
