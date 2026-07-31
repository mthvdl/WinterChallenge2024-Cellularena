from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

from .coord import Coord, ADJACENCY

if TYPE_CHECKING:
	from .organ import Organ


class Protein(Enum):
	A = 0
	B = 1
	C = 2
	D = 3

	@staticmethod
	def from_index(idx: int) -> "Protein":
		return _PROTEIN_ORDER[idx]


_PROTEIN_ORDER = [Protein.A, Protein.B, Protein.C, Protein.D]


class Tile:
	"""A single cell of the grid."""

	def __init__(self, coord: Coord) -> None:
		self.coord = coord
		self.protein: Optional[Protein] = None
		self.obstacle: bool = False
		self.organ: Optional["Organ"] = None

	def set_obstacle(self) -> None:
		self.obstacle = True
		self.protein = None
		self.organ = None

	def set_protein(self, idx: int) -> None:
		self.obstacle = False
		self.protein = Protein.from_index(idx)

	def place_organ(self, organ: "Organ") -> None:
		self.organ = organ
		self.obstacle = False
		self.protein = None

	def clear(self) -> None:
		self.organ = None
		self.obstacle = False
		self.protein = None

	def has_organ(self) -> bool:
		return self.organ is not None

	def has_protein(self) -> bool:
		return self.protein is not None

	def has_tentacle_targeting(self, owner_idx: int, target: Coord) -> bool:
		if self.organ is None:
			return False
		o = self.organ
		from .organ import OrganType

		return (
			o.owner_idx == owner_idx
			and o.type == OrganType.TENTACLE
			and o.get_faced_coord() == target
		)


class Grid:
	"""Rectangular game grid."""

	def __init__(self, width: int, height: int) -> None:
		self.width = width
		self.height = height
		self.cells: Dict[Coord, Tile] = {}
		self.spawn = Coord(0, 0)

		for y in range(height):
			for x in range(width):
				c = Coord(x, y)
				self.cells[c] = Tile(c)

	def get(self, coord: Coord) -> Optional[Tile]:
		return self.cells.get(coord)

	def get_neighbours(self, pos: Coord) -> List[Coord]:
		return [pos.add(d) for d in ADJACENCY if pos.add(d) in self.cells]

	def opposite(self, coord: Coord) -> Coord:
		return Coord(self.width - 1 - coord.x, self.height - 1 - coord.y)

	def get_coords(self) -> List[Coord]:
		return list(self.cells.keys())
