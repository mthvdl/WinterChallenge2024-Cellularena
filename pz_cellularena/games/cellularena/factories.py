"""Cellularena-specific factory helpers for generic training scripts."""
from __future__ import annotations

from games.cellularena.env import CellularenaEnv


def make_env() -> CellularenaEnv:
	return CellularenaEnv()
