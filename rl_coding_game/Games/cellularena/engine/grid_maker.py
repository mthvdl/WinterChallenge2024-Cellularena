from __future__ import annotations
import random
from collections import deque
from typing import Set

from .coord import Coord
from .grid import Grid

_MAX_SPAWN_DIST = 3


def _mirror(coord: Coord, w: int) -> Coord:
	"""Vertical-axis mirror: reflect x across x = w/2."""
	return Coord(w - 1 - coord.x, coord.y)


def _bfs_reachable(grid: Grid, start: Coord) -> Set[Coord]:
	"""Return all non-obstacle coords reachable from *start*."""
	visited: Set[Coord] = {start}
	queue: deque[Coord] = deque([start])
	while queue:
		cur = queue.popleft()
		for nb in grid.get_neighbours(cur):
			tile = grid.cells.get(nb)
			if tile and not tile.obstacle and nb not in visited:
				visited.add(nb)
				queue.append(nb)
	return visited


def _carve_path(grid: Grid, src: Coord, dst: Coord, w: int) -> None:
	"""Clear the minimum set of obstacles to open a path from src to dst.

	BFS ignoring obstacles to find the shortest candidate route, then clears
	every obstacle along it together with its vertical-axis mirror.
	"""
	# BFS on full grid (obstacles treated as walkable) to find shortest route
	prev: dict[Coord, Coord | None] = {src: None}
	queue: deque[Coord] = deque([src])
	found = False
	while queue and not found:
		cur = queue.popleft()
		for nb in grid.get_neighbours(cur):
			if nb not in prev:
				prev[nb] = cur
				if nb == dst:
					found = True
					break
				queue.append(nb)

	if not found:
		return

	# Trace back the path and clear any obstacles encountered
	cur = dst
	while prev.get(cur) is not None:
		for c in (cur, _mirror(cur, w)):
			tile = grid.cells.get(c)
			if tile and tile.obstacle:
				tile.clear()
		cur = prev[cur]  # type: ignore[assignment]


def make_grid(rng: random.Random, map_height: int | None = None) -> Grid:
	"""Generate a random vertically-symmetric game grid.

	Guarantees:
	- Left-right (vertical-axis) symmetry.
	- At least one open path between the two spawn points.
	- All placed proteins are reachable from the nearest spawn.
	"""
	h = int(map_height) if map_height is not None else rng.randint(8, 12)
	w = h * 2
	grid = Grid(w, h)

	# Spawn positions: player 0 top-left area, player 1 its vertical mirror.
	sx = rng.randint(0, _MAX_SPAWN_DIST)
	sy = rng.randint(0, _MAX_SPAWN_DIST)
	spawn = Coord(sx, sy)
	spawn_opp = _mirror(spawn, w)

	# Work only on left half; right half is always the mirror.
	left_half = [c for c in grid.get_coords() if c.x < w // 2]
	rng.shuffle(left_half)

	# Place obstacles, skipping spawn cells and keeping ratio moderate.
	max_obstacle_ratio = 0.35
	obstacle_budget = int(rng.random() * max_obstacle_ratio * len(left_half))
	obstacle_coords: Set[Coord] = set()
	for coord in left_half:
		if len(obstacle_coords) >= obstacle_budget:
			break
		sym = _mirror(coord, w)
		if coord in (spawn, spawn_opp) or sym in (spawn, spawn_opp):
			continue
		obstacle_coords.add(coord)
		obstacle_coords.add(sym)

	for c in obstacle_coords:
		grid.cells[c].set_obstacle()

	# Guarantee a walkable path between the two spawn points.
	if spawn_opp not in _bfs_reachable(grid, spawn):
		_carve_path(grid, spawn, spawn_opp, w)

	# Recompute reachable set after any carving.
	reachable_from_spawn = _bfs_reachable(grid, spawn)

	# Place proteins on the left half only in cells reachable from spawn.
	max_protein_ratio = 0.15
	protein_budget = int(rng.random() * max_protein_ratio * len(left_half)) + 4
	candidates = [
		c for c in left_half
		if c not in obstacle_coords and c != spawn and c in reachable_from_spawn
	]
	rng.shuffle(candidates)

	protein_idx = 0
	placed = 0
	for coord in candidates:
		if placed >= protein_budget:
			break
		sym = _mirror(coord, w)
		sym_tile = grid.cells.get(sym)
		if sym_tile is None or sym_tile.obstacle:
			continue
		ptype = protein_idx % 4
		grid.cells[coord].set_protein(ptype)
		sym_tile.set_protein(ptype)
		protein_idx += 1
		placed += 1

	# Clear spawn tiles (may have picked up a protein above).
	for c in (spawn, spawn_opp):
		tile = grid.cells.get(c)
		if tile:
			tile.clear()

	grid.spawn = spawn
	return grid
