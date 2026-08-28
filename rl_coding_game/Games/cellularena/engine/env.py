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
The underlying game reward is sparse and non-zero only on the terminal step.
By default, the environment adds policy-invariant potential-based shaping on
non-terminal steps.
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

from .obs import TemporalObservationBuilder
from .grid import Protein
from .game import (
	ACTIONS_PER_ORG,
	MAX_H,
	MAX_ROOTS,
	MAX_TURNS,
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
		obs_history_steps: int = 1,
		map_height: Optional[int] = None,
		map_width: Optional[int] = None,
		wall_ratio: Optional[float] = None,
		protein_ratio: Optional[float] = None,
		reward_shaping: bool = True,
		shaping_gamma: float = 0.99,
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
		self._map_height = map_height
		self._map_width = map_width
		self._wall_ratio = wall_ratio
		self._protein_ratio = protein_ratio
		self._reward_shaping = reward_shaping
		self._shaping_gamma = float(shaping_gamma)
		if not 0.0 < self._shaping_gamma <= 1.0:
			raise ValueError("shaping_gamma must be in (0, 1].")
		self._game = self._make_game(seed)
		self._potentials = [0.0, 0.0]
		self._obs_builder = TemporalObservationBuilder(
			history_steps=obs_history_steps,
		)

	# ------------------------------------------------------------------
	# Spaces
	# ------------------------------------------------------------------

	@functools.lru_cache(maxsize=None)
	def observation_space(self, agent: str) -> spaces.Space:
		del agent
		return self._obs_builder.observation_space()

	@functools.lru_cache(maxsize=None)
	def action_space(self, agent: str) -> spaces.Space:
		return spaces.MultiDiscrete([ACTIONS_PER_ORG] * MAX_ROOTS)

	@property
	def max_episode_steps(self) -> int:
		return MAX_TURNS

	def _make_game(self, seed: Optional[int]) -> Game:
		return Game(
			seed,
			map_height=self._map_height,
			map_width=self._map_width,
			wall_ratio=self._wall_ratio,
			protein_ratio=self._protein_ratio,
		)

	# ------------------------------------------------------------------
	# PettingZoo API
	# ------------------------------------------------------------------

	def reset(
		self,
		seed: Optional[int] = None,
		options: Optional[Dict] = None,
	):
		self._game = self._make_game(seed if seed is not None else self._seed)

		self._game.reset()
		self._obs_builder.reset()
		self._potentials = self._state_potentials()
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
		if self._reward_shaping and not done:
			next_potentials = self._state_potentials()
			rewards_by_idx = {
				player_idx: float(rewards_by_idx.get(player_idx, 0.0))
				+ self._shaping_gamma * next_potentials[player_idx]
				- self._potentials[player_idx]
				for player_idx in range(len(self._game.players))
			}
			self._potentials = next_potentials
		elif done:
			self._potentials = [0.0, 0.0]

		reward_map = {
			a: float(rewards_by_idx.get(self._agent_to_idx[a], 0.0))
			for a in self.possible_agents
		}

		terminations: Dict[str, bool] = {a: done for a in self.possible_agents}
		truncations: Dict[str, bool] = {a: False for a in self.possible_agents}
		infos: Dict[str, Any] = {a: {} for a in self.possible_agents}
		if done:
			infos = self._episode_infos()

		if done:
			self.agents = []
			observations = {a: self._get_obs(self._agent_to_idx[a]) for a in self.possible_agents}
		else:
			observations = {a: self._get_obs(self._agent_to_idx[a]) for a in self.agents}

		return observations, reward_map, terminations, truncations, infos

	def _episode_infos(self) -> Dict[str, Dict[str, Any]]:
		"""Expose terminal game outcomes as RLlib episode metrics."""
		infos: Dict[str, Dict[str, Any]] = {}
		for agent, player_idx in self._agent_to_idx.items():
			player = self._game.players[player_idx]
			infos[agent] = {
				"harvest_count": self._game.harvested_by_player[player_idx],
				"final_storage_total": player.protein_total,
				**{
					f"final_storage_{protein.name.lower()}": player.storage[protein]
					for protein in Protein
				},
				"final_organ_count": player.organ_count,
				"terminal_reason": self._game.terminal_reason,
			}
		return infos

	def _state_potentials(self) -> List[float]:
		"""Return a bounded, zero-sum potential for the current game state."""
		organ_delta = self._game.players[0].organ_count - self._game.players[1].organ_count
		protein_delta = (
			self._game.players[0].protein_total
			- self._game.players[1].protein_total
		)
		potential = 0.25 * float(
			np.tanh(organ_delta / 8.0 + 0.25 * protein_delta / 20.0)
		)
		return [potential, -potential]

	# ------------------------------------------------------------------
	# Internal helpers
	# ------------------------------------------------------------------

	def _get_obs(self, player_idx: int) -> Dict:
		raw_obs = self._game.get_observation(player_idx)
		return self._obs_builder.transform(player_idx, raw_obs)

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
