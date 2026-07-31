from __future__ import annotations
from enum import Enum
from typing import List, Optional

from .coord import Coord, Direction


class OrganType(Enum):
	ROOT = 0
	BASIC = 1
	TENTACLE = 2
	HARVESTER = 3
	SPORER = 4

	@property
	def cost(self) -> List[int]:
		return _ORGAN_COSTS[self]


_ORGAN_COSTS = {
	OrganType.ROOT: [1, 1, 1, 1],
	OrganType.BASIC: [1, 0, 0, 0],
	OrganType.TENTACLE: [0, 1, 1, 0],
	OrganType.HARVESTER: [0, 0, 1, 1],
	OrganType.SPORER: [0, 1, 0, 1],
}


class Organ:
	def __init__(
		self,
		organ_id: int,
		owner_idx: int,
		organ_type: OrganType,
		direction: Direction,
	) -> None:
		self.id = organ_id
		self.owner_idx = owner_idx
		self.type = organ_type
		self.direction = direction
		self.pos: Optional[Coord] = None
		self.parent: Optional["Organ"] = None
		self.children: List["Organ"] = []
		self.root_id: int = self.id

	def set_pos(self, pos: Coord) -> None:
		self.pos = pos

	def set_parent(self, parent: "Organ") -> None:
		self.parent = parent
		self.root_id = parent.root_id if parent.type != OrganType.ROOT else parent.id

	def get_faced_coord(self) -> Coord:
		return self.pos.add(self.direction.coord)

	def is_harvester(self) -> bool:
		return self.type == OrganType.HARVESTER

	def is_tentacle(self) -> bool:
		return self.type == OrganType.TENTACLE

	def is_nucleus(self) -> bool:
		return self.type == OrganType.ROOT

	def is_sporer(self) -> bool:
		return self.type == OrganType.SPORER
