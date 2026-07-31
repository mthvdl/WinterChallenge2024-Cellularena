from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List


@dataclass(frozen=True)
class Coord:
	x: int
	y: int

	def add(self, other: "Coord") -> "Coord":
		return Coord(self.x + other.x, self.y + other.y)

	def manhattan_to(self, other: "Coord") -> int:
		return abs(self.x - other.x) + abs(self.y - other.y)

	def __repr__(self) -> str:
		return f"({self.x},{self.y})"


class Direction(Enum):
	NORTH = (0, -1)
	EAST = (1, 0)
	SOUTH = (0, 1)
	WEST = (-1, 0)

	@property
	def coord(self) -> Coord:
		return Coord(*self.value)

	@staticmethod
	def from_index(idx: int) -> "Direction":
		return _DIR_ORDER[idx]

	def to_index(self) -> int:
		return _DIR_ORDER.index(self)

	@staticmethod
	def from_str(s: str) -> "Direction":
		return {
			"N": Direction.NORTH,
			"E": Direction.EAST,
			"S": Direction.SOUTH,
			"W": Direction.WEST,
		}[s.upper()]


_DIR_ORDER: List[Direction] = [
	Direction.NORTH,
	Direction.EAST,
	Direction.SOUTH,
	Direction.WEST,
]

ADJACENCY: List[Coord] = [d.coord for d in _DIR_ORDER]
