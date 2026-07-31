"""Cellularena replay adapter for offline transition extraction.

This module is intentionally game-specific and kept outside rl/ to preserve
the game-agnostic RL framework boundary.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np

from rl.experience import Transition
from rl.offline_adapter import ReplayTransitionAdapter

from games.cellularena.game.coord import Direction
from games.cellularena.game.game import ACTIONS_PER_ORG, MAX_ROOTS, Game, GrowthCommand


def create_adapter() -> ReplayTransitionAdapter:
	return CellularenaCoreReplayAdapter()


class CellularenaCoreReplayAdapter(ReplayTransitionAdapter):
	"""Convert cellularena-core-raw-v1 replay files into RL transitions."""

	def __init__(self, include_player1: bool = True) -> None:
		self.include_player1 = include_player1

	def iter_transitions(self, replay_path: Path) -> Iterable[Transition]:
		data = json.loads(replay_path.read_text(encoding="utf-8"))
		if data.get("format") != "cellularena-core-raw-v1":
			raise ValueError(
				f"Unsupported replay format in {replay_path}. "
				"Expected cellularena-core-raw-v1."
			)

		game = Game()
		game.init_from_global_data(data["globalData"])

		init_storage = self._resolve_initial_storage(data, replay_path)
		game.set_storage(init_storage[0], init_storage[1])

		for turn_entry in data.get("turns", []):
			raw_commands = turn_entry.get("commands", [[], []])
			cmds_p0 = list(raw_commands[0] if len(raw_commands) > 0 else [])
			cmds_p1 = list(raw_commands[1] if len(raw_commands) > 1 else [])

			obs_p0 = game.get_observation(0)
			obs_p1 = game.get_observation(1)

			actions_p0 = self._encode_player_actions(game, 0, cmds_p0)
			actions_p1 = self._encode_player_actions(game, 1, cmds_p1)

			done, rewards = game.step_replay({0: cmds_p0, 1: cmds_p1})

			next_obs_p0 = game.get_observation(0)
			next_obs_p1 = game.get_observation(1)

			yield Transition(
				obs=obs_p0,
				action=actions_p0,
				reward=float(rewards.get(0, 0.0)),
				next_obs=next_obs_p0,
				done=bool(done),
				info={"agent_idx": 0, "source": "offline_replay"},
			)

			if self.include_player1:
				yield Transition(
					obs=obs_p1,
					action=actions_p1,
					reward=float(rewards.get(1, 0.0)),
					next_obs=next_obs_p1,
					done=bool(done),
					info={"agent_idx": 1, "source": "offline_replay"},
				)

	def _encode_player_actions(self, game: Game, player_idx: int, cmds: List[str]) -> np.ndarray:
		action = np.zeros((MAX_ROOTS,), dtype=np.int64)
		player = game.players[player_idx]

		for slot in range(min(MAX_ROOTS, len(cmds))):
			cmd = cmds[slot]
			action[slot] = self._encode_slot_cmd(game, player_idx, player, slot, cmd)
		return action

	def _encode_slot_cmd(
		self,
		game: Game,
		player_idx: int,
		player,
		slot: int,
		cmd: str,
	) -> int:
		if slot >= len(player.roots):
			return 0
		if not cmd or cmd.strip().upper().startswith("WAIT"):
			return 0

		parsed = game.parse_raw_command(cmd, player_idx)
		if parsed is None:
			return 0

		root = player.roots[slot]
		root_id = game._get_root_id(root)

		for action_int in range(1, ACTIONS_PER_ORG):
			candidate = game._decode_action(player, root_id, action_int)
			if candidate is not None and self._same_command(candidate, parsed):
				return int(action_int)

		# Best-effort fallback for unusual command forms.
		direct = self._direct_command_encode(game, player_idx, parsed)
		if direct is not None:
			return direct
		return 0

	@staticmethod
	def _same_command(a: GrowthCommand, b: GrowthCommand) -> bool:
		return (
			a.target == b.target
			and a.organ_type == b.organ_type
			and a.direction == b.direction
			and a.is_spore == b.is_spore
		)

	def _direct_command_encode(
		self,
		game: Game,
		player_idx: int,
		parsed: GrowthCommand,
	) -> Optional[int]:
		# Direct inversion when command fully specifies a compatible action.
		if parsed.is_spore:
			from_organ = game.organ_by_id.get(parsed.from_organ_id)
			if from_organ is None:
				return None
			return 65 + from_organ.direction.to_index()

		from_organ = game.organ_by_id.get(parsed.from_organ_id)
		if from_organ is None:
			return None

		dx = parsed.target.x - from_organ.pos.x
		dy = parsed.target.y - from_organ.pos.y
		growth_dir = self._direction_from_delta(dx, dy)
		if growth_dir is None:
			return None

		type_map = {
			"BASIC": 0,
			"TENTACLE": 1,
			"HARVESTER": 2,
			"SPORER": 3,
		}
		type_idx = type_map.get(parsed.organ_type.name)
		if type_idx is None:
			return None

		raw = growth_dir.to_index() * 16 + parsed.direction.to_index() * 4 + type_idx
		return raw + 1

	@staticmethod
	def _direction_from_delta(dx: int, dy: int) -> Optional[Direction]:
		if dx == 0 and dy == -1:
			return Direction.NORTH
		if dx == 1 and dy == 0:
			return Direction.EAST
		if dx == 0 and dy == 1:
			return Direction.SOUTH
		if dx == -1 and dy == 0:
			return Direction.WEST
		return None

	def _resolve_initial_storage(self, data: dict, replay_path: Path) -> List[List[int]]:
		init_storage = data.get("initialStorage")
		if init_storage and len(init_storage) == 2:
			return [list(init_storage[0]), list(init_storage[1])]

		game_id = data.get("gameId")
		if game_id is not None:
			codingame_path = replay_path.parent / f"codingame_{int(game_id)}.json"
			if codingame_path.exists():
				try:
					from replay_transform import _infer_initial_storage, load_replay_from_dict

					raw = json.loads(codingame_path.read_text(encoding="utf-8"))
					replay = load_replay_from_dict(raw if "success" in raw else {"success": raw})
					inferred = _infer_initial_storage(data.get("globalData", ""), replay)
					if inferred and len(inferred) == 2:
						return [list(inferred[0]), list(inferred[1])]
				except Exception:
					pass

		# Safe fallback to keep prefill operational on imperfect archives.
		# High symmetric values keep command-affordability checks permissive.
		fallback = [10, 10, 10, 10]
		return [list(fallback), list(fallback)]
