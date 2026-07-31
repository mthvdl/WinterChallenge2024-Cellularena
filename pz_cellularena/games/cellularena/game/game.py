"""
Core game logic for Cellularena, ported from the Java referee.

replay_* methods allow initialising the engine directly from a CodingGame
replay and executing raw GROW/SPORE/WAIT command strings, enabling exact
validation against reference games.

Turn flow (mirrors Java):
  1. Decode & validate each organism's action -> queue GrowthCommands
  2. Pay protein cost immediately for each valid command
  3. Resolve collisions: two growths to same cell -> both pay, cell -> wall
  4. Place new organs for non-colliding growths
  5. Harvest proteins (HARVESTERs +1/turn from faced protein tile)
  6. Attack (TENTACLEs kill faced enemy organ + cascade-remove children)
  7. Increment turn; check termination
"""
from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from .coord import Coord, Direction
from .grid import Grid, Protein
from .grid_maker import make_grid
from .organ import Organ, OrganType

MAX_TURNS = 100
PROTEIN_PER_ABSORB = 3
MAX_H = 12
MAX_W = 24
N_CHANNELS = 17
MAX_ROOTS = 5
ACTIONS_PER_ORG = 69

_GROW_TYPES = [OrganType.BASIC, OrganType.TENTACLE, OrganType.HARVESTER, OrganType.SPORER]


@dataclass
class GrowthCommand:
	player_idx: int
	from_organ_id: int
	target: Coord
	organ_type: OrganType
	direction: Direction
	is_spore: bool = False


@dataclass
class PlayerState:
	idx: int
	storage: Dict[Protein, int] = field(default_factory=lambda: {p: 0 for p in Protein})
	organs: List[Organ] = field(default_factory=list)
	roots: List[Organ] = field(default_factory=list)

	def add_organ(self, organ: Organ) -> None:
		self.organs.append(organ)
		if organ.type == OrganType.ROOT:
			self.roots.append(organ)

	def remove_organ(self, organ: Organ) -> None:
		if organ in self.organs:
			self.organs.remove(organ)
		if organ.type == OrganType.ROOT and organ in self.roots:
			self.roots.remove(organ)

	def can_afford(self, organ_type: OrganType) -> bool:
		prots = [Protein.A, Protein.B, Protein.C, Protein.D]
		return all(self.storage[p] >= c for p, c in zip(prots, organ_type.cost))

	def pay_for(self, organ_type: OrganType) -> None:
		prots = [Protein.A, Protein.B, Protein.C, Protein.D]
		for p, c in zip(prots, organ_type.cost):
			self.storage[p] -= c

	def absorb(self, protein: Optional[Protein]) -> None:
		if protein is not None:
			self.storage[protein] += PROTEIN_PER_ABSORB

	def harvest(self, protein: Protein) -> None:
		self.storage[protein] += 1

	@property
	def organ_count(self) -> int:
		return len(self.organs)

	@property
	def protein_total(self) -> int:
		return sum(self.storage.values())

	def is_alive(self) -> bool:
		return bool(self.organs)

	def can_progress(self, grid: Grid) -> bool:
		for o in self.organs:
			if o.is_harvester():
				tile = grid.get(o.get_faced_coord())
				if tile and tile.has_protein():
					return True
		return any(self.can_afford(t) for t in OrganType if t != OrganType.ROOT)


class Game:
	def __init__(self, seed: Optional[int] = None) -> None:
		self._seed = seed
		self.rng: random.Random = random.Random(seed)
		self.grid: Optional[Grid] = None
		self.players: List[PlayerState] = []
		self.organ_by_id: Dict[int, Organ] = {}
		self.organ_by_coord: Dict[Coord, Organ] = {}
		self.turn: int = 0
		self.done: bool = False
		self.terminal_reason: str = ""
		self._next_organ_id: int = 1

	def reset(self) -> None:
		self.rng = random.Random(self._seed)
		self._next_organ_id = 1
		self.grid = make_grid(self.rng)
		self.players = [PlayerState(idx=0), PlayerState(idx=1)]
		self.organ_by_id = {}
		self.organ_by_coord = {}
		self.turn = 0
		self.done = False
		self.terminal_reason = ""

		for protein in Protein:
			amount = self.rng.randint(3, 10)
			for player in self.players:
				player.storage[protein] = amount

		spawn = self.grid.spawn
		for player in self.players:
			pos = spawn if player.idx == 0 else self.grid.opposite(spawn)
			root = self._make_organ(player.idx, OrganType.ROOT, Direction.NORTH)
			self._place_organ(root, pos)

	def step(self, actions: Dict[int, List[int]]) -> Tuple[bool, Dict[int, float]]:
		if self.done:
			return True, {0: 0.0, 1: 0.0}

		pending: List[GrowthCommand] = self._collect_commands(actions)
		self._resolve_growth(pending)
		self._do_harvests()
		self._do_attacks()
		self.turn += 1

		if self._is_game_over():
			self.done = True
			return True, self._final_rewards()

		return False, {0: 0.0, 1: 0.0}

	def get_observation(self, player_idx: int) -> Dict:
		grid_obs = np.zeros((MAX_H, MAX_W, N_CHANNELS), dtype=np.float32)

		for coord, tile in self.grid.cells.items():
			x, y = coord.x, coord.y
			if y >= MAX_H or x >= MAX_W:
				continue
			if tile.obstacle:
				grid_obs[y, x, 0] = 1.0
			elif tile.protein is not None:
				grid_obs[y, x, 1 + tile.protein.value] = 1.0
			elif tile.organ is not None:
				o = tile.organ
				base = 5 + o.owner_idx * 5
				grid_obs[y, x, base + o.type.value] = 1.0
				dir_ch = 15 + o.owner_idx
				grid_obs[y, x, dir_ch] = o.direction.to_index() / 3.0

		storage_obs = np.zeros((2, 4), dtype=np.float32)
		for p_idx, player in enumerate(self.players):
			for prot in Protein:
				storage_obs[p_idx, prot.value] = min(player.storage[prot] / 50.0, 1.0)

		turn_obs = np.array([self.turn / MAX_TURNS], dtype=np.float32)
		return {"grid": grid_obs, "storage": storage_obs, "turn": turn_obs}

	def compute_action_mask(self, player_idx: int) -> np.ndarray:
		"""Return a boolean mask of shape ``(MAX_ROOTS, ACTIONS_PER_ORG)``.

		``True``  means the action is legal in the current game state.
		``False`` means the engine would treat it as WAIT anyway; masking it
		out here lets the network focus its capacity on reachable actions.

		Per-slot logic:
		  - Unused slot (player has fewer organisms): only WAIT (index 0) is valid.
		  - Used slot i:
		    - WAIT (0)        : always valid.
		    - GROW (1-64)     : valid iff the player can afford the organ type
		                        AND organism i has at least one free neighbour
		                        in the requested growth direction.
		    - SPORE (65-68)   : valid iff the player can afford ROOT AND
		                        organism i contains a SPORER facing that
		                        direction with a reachable landing cell.
		"""
		player = self.players[player_idx]
		mask = np.zeros((MAX_ROOTS, ACTIONS_PER_ORG), dtype=bool)

		# Pre-compute affordability for each grow type (shared across slots).
		can_afford_grow = [player.can_afford(t) for t in _GROW_TYPES]
		can_afford_root = player.can_afford(OrganType.ROOT)

		for slot in range(MAX_ROOTS):
			# WAIT is always valid.
			mask[slot, 0] = True

			if slot >= len(player.roots):
				# Unused slot – only WAIT is meaningful.
				continue

			root = player.roots[slot]
			root_id = self._get_root_id(root)
			organs = self._organism_organs(root_id, player_idx)

			# GROW actions: check once per (growth_dir, organ_type) pair.
			# Facing direction does not affect legality, only placement aesthetics.
			has_free_in_dir: List[bool] = [False] * 4
			for d_idx in range(4):
				gdir = Direction.from_index(d_idx)
				for organ in organs:
					if self._valid_growth_target(player, organ.pos.add(gdir.coord)):
						has_free_in_dir[d_idx] = True
						break

			for action in range(1, 65):
				raw = action - 1
				growth_dir = raw // 16   # 0-N 1-E 2-S 3-W
				type_idx = raw % 4       # 0-BASIC 1-TENT 2-HARV 3-SPORER
				if can_afford_grow[type_idx] and has_free_in_dir[growth_dir]:
					mask[slot, action] = True

			# SPORE actions: need a SPORER facing that direction with a valid target.
			if can_afford_root:
				for organ in organs:
					if organ.is_sporer():
						target = self._spore_target(organ)
						if target is not None and self._valid_growth_target(player, target):
							mask[slot, 65 + organ.direction.to_index()] = True

		return mask

	def _make_organ(self, owner_idx: int, organ_type: OrganType, direction: Direction) -> Organ:
		organ = Organ(self._next_organ_id, owner_idx, organ_type, direction)
		self._next_organ_id += 1
		return organ

	def _place_organ(self, organ: Organ, coord: Coord) -> None:
		tile = self.grid.get(coord)
		if tile is None:
			return
		player = self.players[organ.owner_idx]
		protein = tile.protein

		organ.set_pos(coord)
		tile.place_organ(organ)
		player.add_organ(organ)
		player.absorb(protein)

		self.organ_by_id[organ.id] = organ
		self.organ_by_coord[coord] = organ

	def _remove_organ(self, organ: Organ) -> None:
		tile = self.grid.get(organ.pos)
		if tile:
			tile.clear()
		self.players[organ.owner_idx].remove_organ(organ)
		self.organ_by_id.pop(organ.id, None)
		self.organ_by_coord.pop(organ.pos, None)

		children_snapshot = list(organ.children)
		organ.children.clear()
		for child in children_snapshot:
			child.parent = None
			self._remove_organ(child)

		if organ.parent is not None:
			try:
				organ.parent.children.remove(organ)
			except ValueError:
				pass
			organ.parent = None

	def _connect(self, parent: Organ, child: Organ) -> None:
		parent.children.append(child)
		child.set_parent(parent)

	def _collect_commands(self, actions: Dict[int, List[int]]) -> List[GrowthCommand]:
		commands: List[GrowthCommand] = []
		for player_idx, player_actions in actions.items():
			player = self.players[player_idx]
			acted_roots: Set[int] = set()
			for slot, action_int in enumerate(player_actions):
				if slot >= len(player.roots):
					break
				root = player.roots[slot]
				root_id = self._get_root_id(root)
				if root_id in acted_roots:
					continue
				acted_roots.add(root_id)
				if action_int == 0:
					continue
				cmd = self._decode_action(player, root_id, action_int)
				if cmd is not None:
					player.pay_for(cmd.organ_type)
					commands.append(cmd)
		return commands

	def _decode_action(self, player: PlayerState, root_id: int, action_int: int) -> Optional[GrowthCommand]:
		if 1 <= action_int <= 64:
			raw = action_int - 1
			growth_dir = Direction.from_index(raw // 16)
			face_dir = Direction.from_index((raw // 4) % 4)
			type_idx = raw % 4
			organ_type = _GROW_TYPES[type_idx]
			return self._find_grow_cmd(player, root_id, growth_dir, face_dir, organ_type)

		if 65 <= action_int <= 68:
			spore_dir = Direction.from_index(action_int - 65)
			return self._find_spore_cmd(player, root_id, spore_dir)

		return None

	def _find_grow_cmd(
		self,
		player: PlayerState,
		root_id: int,
		growth_dir: Direction,
		face_dir: Direction,
		organ_type: OrganType,
	) -> Optional[GrowthCommand]:
		if not player.can_afford(organ_type):
			return None
		for organ in self._organism_organs(root_id, player.idx):
			target = organ.pos.add(growth_dir.coord)
			if self._valid_growth_target(player, target):
				return GrowthCommand(
					player_idx=player.idx,
					from_organ_id=organ.id,
					target=target,
					organ_type=organ_type,
					direction=face_dir,
					is_spore=False,
				)
		return None

	def _find_spore_cmd(self, player: PlayerState, root_id: int, spore_dir: Direction) -> Optional[GrowthCommand]:
		if not player.can_afford(OrganType.ROOT):
			return None
		sporer: Optional[Organ] = None
		for organ in self._organism_organs(root_id, player.idx):
			if organ.is_sporer() and organ.direction == spore_dir:
				sporer = organ
				break
		if sporer is None:
			return None

		target = self._spore_target(sporer)
		if target is None:
			return None

		return GrowthCommand(
			player_idx=player.idx,
			from_organ_id=sporer.id,
			target=target,
			organ_type=OrganType.ROOT,
			direction=Direction.NORTH,
			is_spore=True,
		)

	def _spore_target(self, sporer: Organ) -> Optional[Coord]:
		step = sporer.direction.coord
		cur = sporer.pos.add(step)
		last_valid: Optional[Coord] = None
		while True:
			tile = self.grid.get(cur)
			if tile is None:
				break
			if tile.obstacle or tile.has_organ():
				break
			foe_idx = 1 - sporer.owner_idx
			blocked = any(
				self.grid.get(n) is not None and self.grid.get(n).has_tentacle_targeting(foe_idx, cur)
				for n in self.grid.get_neighbours(cur)
			)
			if not blocked:
				last_valid = cur
			cur = cur.add(step)
		return last_valid

	def _resolve_growth(self, commands: List[GrowthCommand], event_id_map: Optional[Dict[Coord, int]] = None) -> None:
		by_coord: Dict[Coord, List[GrowthCommand]] = defaultdict(list)
		for cmd in commands:
			by_coord[cmd.target].append(cmd)

		for coord, cmds in by_coord.items():
			if len(cmds) > 1:
				tile = self.grid.get(coord)
				if tile:
					tile.set_obstacle()
			else:
				cmd = cmds[0]
				if event_id_map and coord in event_id_map:
					ref_id = event_id_map[coord]
					organ = Organ(ref_id, cmd.player_idx, cmd.organ_type, cmd.direction)
					if ref_id >= self._next_organ_id:
						self._next_organ_id = ref_id + 1
				else:
					organ = self._make_organ(cmd.player_idx, cmd.organ_type, cmd.direction)

				self._place_organ(organ, coord)
				if not organ.is_nucleus():
					parent = self.organ_by_id.get(cmd.from_organ_id)
					if parent is not None:
						self._connect(parent, organ)

	def _do_harvests(self) -> None:
		for player in self.players:
			harvested: Set[Coord] = set()
			for organ in player.organs:
				if organ.is_harvester():
					target = organ.get_faced_coord()
					if target not in harvested:
						tile = self.grid.get(target)
						if tile and tile.has_protein():
							player.harvest(tile.protein)
							harvested.add(target)

	def _do_attacks(self) -> None:
		dying: Set[int] = set()
		for organ in self.organ_by_id.values():
			if organ.is_tentacle():
				target_tile = self.grid.get(organ.get_faced_coord())
				if target_tile and target_tile.organ is not None:
					victim = target_tile.organ
					if victim.owner_idx != organ.owner_idx:
						dying.add(victim.id)

		for organ_id in dying:
			organ = self.organ_by_id.get(organ_id)
			if organ is not None:
				self._remove_organ(organ)

	def _is_game_over(self) -> bool:
		for player in self.players:
			if not player.is_alive():
				self.terminal_reason = "player_eliminated"
				return True
		if self.turn >= MAX_TURNS:
			self.terminal_reason = "max_turns"
			return True
		all_occupied = all(t.has_organ() or t.obstacle for t in self.grid.cells.values())
		if all_occupied:
			self.terminal_reason = "grid_full"
			return True
		if not any(p.can_progress(self.grid) for p in self.players):
			self.terminal_reason = "no_progress"
			return True
		return False

	def _final_rewards(self) -> Dict[int, float]:
		scores = [p.organ_count for p in self.players]
		if scores[0] > scores[1]:
			return {0: 1.0, 1: -1.0}
		if scores[1] > scores[0]:
			return {0: -1.0, 1: 1.0}
		proteins = [p.protein_total for p in self.players]
		if proteins[0] > proteins[1]:
			return {0: 0.5, 1: -0.5}
		if proteins[1] > proteins[0]:
			return {0: -0.5, 1: 0.5}
		return {0: 0.0, 1: 0.0}

	def _organism_organs(self, root_id: int, owner_idx: int) -> List[Organ]:
		return [o for o in self.organ_by_id.values() if o.owner_idx == owner_idx and self._get_root_id(o) == root_id]

	def _get_root_id(self, organ: Organ) -> int:
		cur = organ
		while cur.parent is not None:
			cur = cur.parent
		return cur.id

	def _valid_growth_target(self, player: PlayerState, target: Coord) -> bool:
		tile = self.grid.get(target)
		if tile is None:
			return False
		if tile.obstacle or tile.has_organ():
			return False
		foe_idx = 1 - player.idx
		for neigh in self.grid.get_neighbours(target):
			n_tile = self.grid.get(neigh)
			if n_tile and n_tile.has_tentacle_targeting(foe_idx, target):
				return False
		return True

	_RE_GROW = re.compile(
		r"^GROW(?:TH)?\\s+(-?\\d+)\\s+(-?\\d+)\\s+(-?\\d+)\\s+(\\w+)(?:\\s+([NESWnesw]))?(?:\\s+.*)?$",
		re.IGNORECASE,
	)
	_RE_SPORE = re.compile(r"^SPORE\\s+(-?\\d+)\\s+(-?\\d+)\\s+(-?\\d+)(?:\\s+.*)?$", re.IGNORECASE)
	_RE_WAIT = re.compile(r"^WAIT(?:\\s+.*)?$", re.IGNORECASE)

	def init_from_global_data(self, global_data_str: str) -> None:
		self._next_organ_id = 1
		self.organ_by_id = {}
		self.organ_by_coord = {}
		self.turn = 0
		self.done = False
		self.terminal_reason = ""

		lines = global_data_str.strip().split("\n")
		idx = 0

		w, h = map(int, lines[idx].split())
		idx += 1
		self.grid = Grid(w, h)
		self.players = [PlayerState(idx=0), PlayerState(idx=1)]

		for y in range(h):
			for x in range(w):
				parts = lines[idx].split()
				idx += 1
				coord = Coord(x, y)
				tile = self.grid.cells[coord]
				if parts[0] == "1":
					tile.set_obstacle()
				elif parts[1] != "X":
					tile.set_protein({"A": 0, "B": 1, "C": 2, "D": 3}[parts[1]])

		parent_ids: Dict[int, int] = {}
		for player_idx in range(2):
			count = int(lines[idx])
			idx += 1
			for _ in range(count):
				parts = lines[idx].split()
				idx += 1
				oid = int(parts[0])
				ox, oy = int(parts[1]), int(parts[2])
				otype = OrganType[parts[3].upper()]
				odir = Direction.from_str(parts[4]) if parts[4] != "X" else Direction.NORTH
				opid = int(parts[5])
				parent_ids[oid] = opid

				organ = Organ(oid, player_idx, otype, odir)
				pos = Coord(ox, oy)
				organ.set_pos(pos)
				self.grid.cells[pos].place_organ(organ)
				self.players[player_idx].add_organ(organ)
				self.organ_by_id[oid] = organ
				self.organ_by_coord[pos] = organ

				if oid >= self._next_organ_id:
					self._next_organ_id = oid + 1

		for oid, pid in parent_ids.items():
			if pid != 0:
				organ = self.organ_by_id[oid]
				parent = self.organ_by_id.get(pid)
				if parent:
					parent.children.append(organ)
					organ.set_parent(parent)

	def set_storage(self, storage_p0: List[int], storage_p1: List[int]) -> None:
		prots = [Protein.A, Protein.B, Protein.C, Protein.D]
		for p, v in zip(prots, storage_p0):
			self.players[0].storage[p] = v
		for p, v in zip(prots, storage_p1):
			self.players[1].storage[p] = v

	def parse_raw_command(self, cmd: str, player_idx: int) -> Optional[GrowthCommand]:
		cmd = cmd.strip()
		if not cmd:
			return None

		m = self._RE_GROW.match(cmd)
		if m:
			from_id = int(m.group(1))
			tx, ty = int(m.group(2)), int(m.group(3))
			type_str = m.group(4).upper()
			if type_str == "NUCLEUS":
				type_str = "ROOT"
			dir_str = (m.group(5) or "N").upper()
			target = Coord(tx, ty)
			try:
				organ_type = OrganType[type_str]
				direction = Direction.from_str(dir_str)
			except (KeyError, ValueError):
				return None

			player = self.players[player_idx]
			from_organ = self.organ_by_id.get(from_id)
			if from_organ is None or from_organ.owner_idx != player_idx:
				return None
			if organ_type == OrganType.ROOT:
				return None
			if not player.can_afford(organ_type):
				return None

			actual_target, actual_from_id = self._pathfind_grow(from_id, target, player_idx)
			if actual_target is None:
				return None
			if not self._valid_growth_target(player, actual_target):
				return None

			return GrowthCommand(
				player_idx=player_idx,
				from_organ_id=actual_from_id,
				target=actual_target,
				organ_type=organ_type,
				direction=direction,
				is_spore=False,
			)

		m = self._RE_SPORE.match(cmd)
		if m:
			from_id = int(m.group(1))
			tx, ty = int(m.group(2)), int(m.group(3))
			target = Coord(tx, ty)
			player = self.players[player_idx]
			sporer = self.organ_by_id.get(from_id)

			if sporer is None or sporer.owner_idx != player_idx:
				return None
			if not sporer.is_sporer():
				return None
			if not player.can_afford(OrganType.ROOT):
				return None

			if not self._valid_spore_target(sporer, target):
				return None
			if not self._valid_growth_target(player, target):
				return None

			return GrowthCommand(
				player_idx=player_idx,
				from_organ_id=from_id,
				target=target,
				organ_type=OrganType.ROOT,
				direction=Direction.NORTH,
				is_spore=True,
			)

		if self._RE_WAIT.match(cmd):
			return None

		return None

	def step_replay(
		self,
		commands: Dict[int, List[str]],
		reference_events: Optional[List] = None,
	) -> Tuple[bool, Dict[int, float]]:
		if self.done:
			return True, {0: 0.0, 1: 0.0}

		pending: List[GrowthCommand] = []
		for player_idx, player_cmds in commands.items():
			player = self.players[player_idx]
			acted_roots: Set[int] = set()

			for slot, cmd_str in enumerate(player_cmds):
				if slot >= len(player.roots):
					break
				root = player.roots[slot]
				root_id = self._get_root_id(root)
				if root_id in acted_roots:
					continue
				acted_roots.add(root_id)

				cmd = self.parse_raw_command(cmd_str, player_idx)
				if cmd is not None:
					player.pay_for(cmd.organ_type)
					pending.append(cmd)

		_EV_GROW = 0
		_EV_SPAWN = 8
		event_id_map: Dict[Coord, int] = {}
		if reference_events:
			for ev in reference_events:
				if ev.type == _EV_GROW and ev.coords and len(ev.coords) >= 2:
					cx, cy = ev.coords[1]
					event_id_map[Coord(cx, cy)] = ev.organ_id
				elif ev.type == _EV_SPAWN and ev.coords:
					cx, cy = ev.coords[0]
					event_id_map[Coord(cx, cy)] = ev.organ_id

		self._resolve_growth(pending, event_id_map)
		self._do_harvests()
		self._do_attacks()
		self.turn += 1

		if self._is_game_over():
			self.done = True
			return True, self._final_rewards()

		return False, {0: 0.0, 1: 0.0}

	def get_state_snapshot(self) -> Dict:
		organ_map = {}
		for coord, tile in self.grid.cells.items():
			if tile.obstacle:
				organ_map[f"{coord.x},{coord.y}"] = {"type": "WALL"}
			elif tile.protein is not None:
				organ_map[f"{coord.x},{coord.y}"] = {"type": tile.protein.name}
			elif tile.organ is not None:
				o = tile.organ
				organ_map[f"{coord.x},{coord.y}"] = {
					"type": o.type.name,
					"owner": o.owner_idx,
					"dir": o.direction.name[0],
					"id": o.id,
				}

		return {
			"turn": self.turn,
			"storage": [[self.players[i].storage[p] for p in Protein] for i in range(2)],
			"organs": [self.players[i].organ_count for i in range(2)],
			"grid": organ_map,
		}

	def _pathfind_grow(self, from_id: int, target: Coord, player_idx: int) -> Tuple[Optional[Coord], int]:
		from_organ = self.organ_by_id.get(from_id)
		if from_organ is None:
			return None, -1

		root_id = self._get_root_id(from_organ)

		if from_organ.pos.manhattan_to(target) == 1:
			return target, from_id

		from collections import deque

		visited: Set[Coord] = {target}
		queue: deque = deque([(target, [target])])

		while queue:
			cur, path = queue.popleft()
			for nc in self.grid.get_neighbours(cur):
				if nc in visited:
					continue
				visited.add(nc)
				tile = self.grid.get(nc)
				if tile is None:
					continue
				if tile.organ is not None:
					o = tile.organ
					if o.owner_idx == player_idx and self._get_root_id(o) == root_id:
						step = path[0] if path else cur
						return step, o.id
					continue
				if tile.obstacle:
					continue
				queue.append((nc, [nc] + path))

		return None, -1

	def _valid_spore_target(self, sporer: Organ, target: Coord) -> bool:
		direction = sporer.direction
		step = direction.coord
		cur = sporer.pos.add(step)
		while True:
			if cur == target:
				return True
			tile = self.grid.get(cur)
			if tile is None or tile.obstacle or tile.has_organ():
				return False
			cur = cur.add(step)
			if cur.manhattan_to(sporer.pos) > self.grid.width + self.grid.height:
				return False
		return False
