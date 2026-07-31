"""
CellularenaEnv  -  PettingZoo ParallelEnv implementation of
Cellularena (CodinGame Winter Challenge 2024).

Agents act simultaneously; the game resolves after both have submitted.

Action space (per agent)
------------------------
``MultiDiscrete([ACTIONS_PER_ORG] * MAX_ROOTS)``

Each slot controls one organism (indexed by the order ROOTs were placed).
Unused slots (player has fewer organisms than MAX_ROOTS) are ignored.

Encoding per slot (ACTIONS_PER_ORG = 69):
  0        -> WAIT
  1..64    -> GROW  (raw = action-1)
			   growth_dir = raw // 16          (0=N, 1=E, 2=S, 3=W)
			   facing_dir = (raw // 4) % 4     (0=N, 1=E, 2=S, 3=W)
			   type_idx   = raw % 4            (0=BASIC 1=TENTACLE 2=HARVESTER 3=SPORER)
  65..68   -> SPORE (launch ROOT from SPORER facing direction action-65)

Observation space (per agent)
------------------------------
Dict:
  "grid"    Box(float32, shape=(MAX_H, MAX_W, N_CHANNELS))
			  ch 0    : obstacle
			  ch 1-4  : protein A/B/C/D
			  ch 5-9  : player-0 organ flags  (ROOT/BASIC/TENT/HARV/SPORER)
			  ch 10-14: player-1 organ flags
			  ch 15   : player-0 organ facing direction  (0..1 normalised)
			  ch 16   : player-1 organ facing direction
  "storage" Box(float32, shape=(2, 4))  - proteins A/B/C/D per player, /50
  "turn"    Box(float32, shape=(1,))    - current turn / MAX_TURNS

Rewards
-------
Sparse: non-zero only on the terminal step.
  +1.0 / -1.0 for clear win/loss
  +0.5 / -0.5 for tie-break by proteins
   0.0         for a true tie
"""
from __future__ import annotations

import functools
from typing import Any, Dict, List, Optional

import numpy as np
from gymnasium import spaces
from pettingzoo import ParallelEnv

from .game.game import (
	ACTIONS_PER_ORG,
	MAX_H,
	MAX_ROOTS,
	MAX_W,
	N_CHANNELS,
	Game,
)


class CellularenaEnv(ParallelEnv):
	"""PettingZoo ParallelEnv wrapping the Cellularena game."""

	metadata = {
		"render_modes": [],
		"name": "cellularena_v0",
	}

	def __init__(
		self,
		seed: Optional[int] = None,
		render_mode: Optional[str] = None,
	) -> None:
		super().__init__()
		self.possible_agents: List[str] = ["player_0", "player_1"]
		self._agent_to_idx: Dict[str, int] = {
			"player_0": 0,
			"player_1": 1,
		}
		# Kept for backward compatibility, but rendering is intentionally
		# handled by the standalone viewer package.
		self.render_mode = render_mode
		self._seed = seed
		self._game = Game(seed)

	# ------------------------------------------------------------------
	# Spaces
	# ------------------------------------------------------------------

	@functools.lru_cache(maxsize=None)
	def observation_space(self, agent: str) -> spaces.Space:
		return spaces.Dict(
			{
				"grid": spaces.Box(
					low=0.0,
					high=1.0,
					shape=(MAX_H, MAX_W, N_CHANNELS),
					dtype=np.float32,
				),
				"storage": spaces.Box(
					low=0.0,
					high=1.0,
					shape=(2, 4),
					dtype=np.float32,
				),
				"turn": spaces.Box(
					low=0.0,
					high=1.0,
					shape=(1,),
					dtype=np.float32,
				),
			}
		)

	@functools.lru_cache(maxsize=None)
	def action_space(self, agent: str) -> spaces.Space:
		return spaces.MultiDiscrete([ACTIONS_PER_ORG] * MAX_ROOTS)

	# ------------------------------------------------------------------
	# PettingZoo API
	# ------------------------------------------------------------------

	def reset(
		self,
		seed: Optional[int] = None,
		options: Optional[Dict] = None,
	):
		if seed is not None:
			self._game = Game(seed)
		else:
			self._game = Game(self._seed)

		self._game.reset()
		self.agents = self.possible_agents[:]

		observations = {a: self._get_obs(self._agent_to_idx[a]) for a in self.agents}
		infos: Dict[str, Any] = {a: {} for a in self.agents}
		return observations, infos

	def step(self, actions: Dict[str, Any]):
		# Map agent names -> integer actions per organism slot
		int_actions: Dict[int, List[int]] = {
			self._agent_to_idx[a]: list(act)
			for a, act in actions.items()
			if a in self._agent_to_idx
		}

		done, rewards_by_idx = self._game.step(int_actions)

		reward_map = {
			a: float(rewards_by_idx.get(self._agent_to_idx[a], 0.0))
			for a in self.possible_agents
		}

		terminations: Dict[str, bool] = {a: done for a in self.possible_agents}
		truncations: Dict[str, bool] = {a: False for a in self.possible_agents}
		infos: Dict[str, Any] = {a: {} for a in self.possible_agents}

		if done:
			self.agents = []
			observations = {a: self._get_obs(self._agent_to_idx[a]) for a in self.possible_agents}
		else:
			observations = {a: self._get_obs(self._agent_to_idx[a]) for a in self.agents}

		return observations, reward_map, terminations, truncations, infos

	# ------------------------------------------------------------------
	# Internal helpers
	# ------------------------------------------------------------------

	def _get_obs(self, player_idx: int) -> Dict:
		return self._game.get_observation(player_idx)

	# ------------------------------------------------------------------
	# Action masking
	# ------------------------------------------------------------------

	def action_mask(self, agent: str) -> np.ndarray:
		"""Return a boolean mask of shape ``(MAX_ROOTS, ACTIONS_PER_ORG)``.

		``True`` indicates a legal action for *agent* in the current state.
		Any env that wishes to support action masking must implement this
		method; :class:`~rl.env_runner.EnvRunner` detects it via
		``hasattr(env, "action_mask")`` and forwards the mask to
		:meth:`~rl.base_bot.RLBot.select_action`.
		"""
		player_idx = self._agent_to_idx[agent]
		return self._game.compute_action_mask(player_idx)

	def close(self) -> None:
		pass
