"""Cellularena-specific factory helpers for generic training scripts."""
from __future__ import annotations

from typing import Optional

from Games.cellularena.engine.env import CellularenaEnv
from Games.cellularena.engine.action_env import CellularenaActionEnv


def make_env(
	seed: Optional[int] = None,
	render_mode: Optional[str] = None,
	obs_history_steps: int = 1,
) -> CellularenaEnv:
	return CellularenaEnv(
		seed=seed,
		render_mode=render_mode,
		obs_history_steps=obs_history_steps,
	)


def make_action_env(
	seed: Optional[int] = None,
	render_mode: Optional[str] = None,
	obs_history_steps: int = 1,
	map_height: Optional[int] = None,
) -> CellularenaActionEnv:
	return CellularenaActionEnv(
		seed=seed,
		render_mode=render_mode,
		obs_history_steps=obs_history_steps,
		map_height=map_height,
	)
