"""Cellularena-specific factory helpers for generic training scripts."""
from __future__ import annotations

from typing import Optional

from Games.cellularena.engine.env import CellularenaEnv
from Games.cellularena.engine.action_env import CellularenaActionEnv


def make_env(
	seed: Optional[int] = None,
	render_mode: Optional[str] = None,
	obs_history_steps: int = 1,
	map_height: Optional[int] = None,
	map_width: Optional[int] = None,
	wall_ratio: Optional[float] = None,
	protein_ratio: Optional[float] = None,
) -> CellularenaEnv:
	return CellularenaEnv(
		seed=seed,
		render_mode=render_mode,
		obs_history_steps=obs_history_steps,
		map_height=map_height,
		map_width=map_width,
		wall_ratio=wall_ratio,
		protein_ratio=protein_ratio,
	)


def make_action_env(
	seed: Optional[int] = None,
	render_mode: Optional[str] = None,
	obs_history_steps: int = 1,
	map_height: Optional[int] = None,
	map_width: Optional[int] = None,
	wall_ratio: Optional[float] = None,
	protein_ratio: Optional[float] = None,
	reward_shaping: bool = False,
) -> CellularenaActionEnv:
	return CellularenaActionEnv(
		seed=seed,
		render_mode=render_mode,
		obs_history_steps=obs_history_steps,
		map_height=map_height,
		map_width=map_width,
		wall_ratio=wall_ratio,
		protein_ratio=protein_ratio,
		reward_shaping=reward_shaping,
	)
