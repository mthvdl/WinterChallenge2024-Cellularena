from __future__ import annotations
import random
from typing import Set

from .coord import Coord
from .grid import Grid

_MAX_SPAWN_DIST = 3


def make_grid(rng: random.Random) -> Grid:
	"""Generate a random symmetric game grid, mirroring the Java GridMaker logic."""
	h = rng.randint(8, 12)
	w = h * 2
	grid = Grid(w, h)

	all_coords = grid.get_coords()
	rng.shuffle(all_coords)

	max_obstacle_ratio = 0.5
	obstacle_budget = int(rng.random() * max_obstacle_ratio * h * w)
	obstacle_coords: Set[Coord] = set()
	for coord in all_coords:
		if len(obstacle_coords) // 2 >= obstacle_budget:
			break
		sym = grid.opposite(coord)
		if coord != sym and coord not in obstacle_coords:
			obstacle_coords.add(coord)
			obstacle_coords.add(sym)

	for c in obstacle_coords:
		grid.cells[c].set_obstacle()

	max_protein_ratio = 0.25
	protein_budget = int(rng.random() * max_protein_ratio * h * w)
	remaining = [c for c in all_coords if c not in obstacle_coords]

	protein_idx = 0
	placed = 0
	for coord in remaining:
		if placed // 2 >= protein_budget and protein_idx >= 8:
			break
		sym = grid.opposite(coord)
		sym_tile = grid.cells.get(sym)
		if sym_tile is None or sym_tile.obstacle or coord == sym:
			continue
		if grid.cells[coord].has_protein() or sym_tile.has_protein():
			continue
		ptype = protein_idx % 4
		grid.cells[coord].set_protein(ptype)
		sym_tile.set_protein(ptype)
		protein_idx += 1
		placed += 2

	sx = rng.randint(0, _MAX_SPAWN_DIST)
	sy = rng.randint(0, _MAX_SPAWN_DIST)
	spawn = Coord(sx, sy)

	t = grid.cells.get(spawn)
	t_opp = grid.cells.get(grid.opposite(spawn))
	if t:
		t.clear()
	if t_opp:
		t_opp.clear()

	grid.spawn = spawn
	return grid
