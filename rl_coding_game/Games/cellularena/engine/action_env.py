"""Cellularena paper-action wrapper env.

Wraps the native Cellularena env (MultiDiscrete per root) with a
Discrete(4033) action space compatible with the paper policy head.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
from gymnasium import spaces

from Games.cellularena.engine.action_adapter import (
    N_ACTIONS,
    build_action_mask,
    discrete_action_to_slot_actions,
    transform_action_index,
    transform_action_mask,
)
from .env import CellularenaEnv


class CellularenaActionEnv(CellularenaEnv):
    """Cellularena env with Discrete(4033) actions.

    Notes
    -----
    A single discrete action maps to one executable organism action and leaves
    all other organism slots on WAIT for that turn.
    """

    @property
    def action_space_n(self) -> int:
        return N_ACTIONS

    def action_space(self, agent: str) -> spaces.Space:
        del agent
        return spaces.Discrete(N_ACTIONS)

    def observation_space(self, agent: str) -> spaces.Space:
        base_space = super().observation_space(agent)
        return spaces.Dict(
            {
                **base_space.spaces,
                "self_player_idx": spaces.Box(0, 1, shape=(1,), dtype=np.int32),
            }
        )

    def _get_obs(self, player_idx: int) -> Dict:
        obs = super()._get_obs(player_idx)
        out = dict(obs)
        out["self_player_idx"] = np.asarray([player_idx], dtype=np.int32)
        return out

    def step(self, actions: Dict[str, Any]):
        translated: Dict[str, np.ndarray] = {}
        for agent, act in actions.items():
            if agent not in self._agent_to_idx:
                continue
            player_idx = self._agent_to_idx[agent]
            translated[agent] = discrete_action_to_slot_actions(
                game=self._game,
                player_idx=player_idx,
                action_index=transform_action_index(int(act), player_idx),
            )
        return super().step(translated)

    def action_mask(self, agent: str) -> np.ndarray:
        player_idx = self._agent_to_idx[agent]
        return transform_action_mask(build_action_mask(self._game, player_idx), player_idx)


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
