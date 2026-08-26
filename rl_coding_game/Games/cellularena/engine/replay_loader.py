"""
replay_loader.py - Parse CodingGame game-replay JSON for Cellularena.

Handles two formats produced by the CodingGame backend:

FORMAT A  - "standard" API (gameResult/findByGameId, synthetic replays)
-----------------------------------------------------------------------
{
  "agents": [{"index":0,"name":"..."}, ...],
  "frames": [
	{"key":"0", "data":"<global_data_string>"},
	{"key":"1", "data":"<frame_data_string>", "stdout":["CMD0\\n","CMD1\\n"]},
	...
  ]
}

FORMAT B  - TV-game (Challenge/findCurrentTvGameInformation)
-------------------------------------------------------------
{
  "frames": [
	{"agentId":-1, "keyframe":true,
	 "view":" 0\\n{\\"global\\":{\\"graphics\\":\\"<global_data_string>\\"}}"},
	{"agentId":0, "stdout":"CMD_P0\\n"},
	{"agentId":1, "stdout":"CMD_P1\\n", "keyframe":true,
	 "view":" N\\n{\\"graphics\\":\\"<frame_data_string>\\"}"},
	...
  ]
}

global_data_string (from Serializer.serializeGlobalData):
  line 0:       width height
  lines 1..W*H: obstacle(0|1) protein_char(A/B/C/D/X)
  For each player (0, 1):
	organ_count
	organ_count lines: id x y type direction parentId

frame_data_string (from Serializer.serializeFrameData):
  For each player (0, 1):
	A B C D          (storage)
	message_count
	message_count lines: organId text
  event_count
  event_count * 8 lines: type start end playerIdx id organType direction coords
"""
from __future__ import annotations

import json as _json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TileData:
	x: int
	y: int
	obstacle: bool
	protein: Optional[str]


@dataclass
class OrganData:
	organ_id: int
	x: int
	y: int
	organ_type: str
	direction: str
	parent_id: int
	player_idx: int


@dataclass
class GlobalData:
	width: int
	height: int
	tiles: List[TileData]
	organs: List[List[OrganData]]


@dataclass
class EventData:
	type: int
	start: float
	end: float
	player_idx: Optional[int]
	organ_id: Optional[int]
	organ_type: Optional[str]
	direction: Optional[str]
	coords: List[Tuple[int, int]]


@dataclass
class FrameData:
	storage: List[List[int]]
	messages: List[Dict[int, str]]
	events: List[EventData]


@dataclass
class ReplayTurn:
	turn: int
	frame_data: FrameData
	stdout: List[List[str]]
	summary: str


@dataclass
class Replay:
	agents: List[Dict[str, Any]]
	global_data: GlobalData
	turns: List[ReplayTurn]
	raw: Dict


def _parse_global_data(text: str) -> GlobalData:
	lines = text.strip().split("\n")
	idx = 0
	w, h = map(int, lines[idx].split())
	idx += 1

	tiles: List[TileData] = []
	for y in range(h):
		for x in range(w):
			parts = lines[idx].split()
			idx += 1
			obstacle = parts[0] == "1"
			protein = parts[1] if parts[1] != "X" else None
			if obstacle:
				protein = None
			tiles.append(TileData(x, y, obstacle, protein))

	organs: List[List[OrganData]] = [[], []]
	for player_idx in range(2):
		count = int(lines[idx])
		idx += 1
		for _ in range(count):
			parts = lines[idx].split()
			idx += 1
			organs[player_idx].append(
				OrganData(
					organ_id=int(parts[0]),
					x=int(parts[1]),
					y=int(parts[2]),
					organ_type=parts[3].upper(),
					direction=parts[4].upper(),
					parent_id=int(parts[5]),
					player_idx=player_idx,
				)
			)
	return GlobalData(width=w, height=h, tiles=tiles, organs=organs)


def _parse_frame_data(text: str, player_count: int = 2) -> FrameData:
	lines = text.strip().split("\n")
	idx = 0
	storage: List[List[int]] = []
	messages: List[Dict[int, str]] = []

	for _ in range(player_count):
		storage.append(list(map(int, lines[idx].split())))
		idx += 1
		n_msg = int(lines[idx])
		idx += 1
		msgs: Dict[int, str] = {}
		for _ in range(n_msg):
			parts = lines[idx].split(" ", 1)
			idx += 1
			msgs[int(parts[0])] = parts[1] if len(parts) > 1 else ""
		messages.append(msgs)

	events: List[EventData] = []
	n_ev = int(lines[idx])
	idx += 1
	for _ in range(n_ev):
		ev_type = int(lines[idx])
		idx += 1
		start = float(lines[idx])
		idx += 1
		end = float(lines[idx])
		idx += 1
		p_raw = lines[idx].strip()
		idx += 1
		id_raw = lines[idx].strip()
		idx += 1
		ot_raw = lines[idx].strip()
		idx += 1
		dr_raw = lines[idx].strip()
		idx += 1
		co_raw = lines[idx].strip()
		idx += 1
		coords = []
		if co_raw:
			for part in co_raw.split("_"):
				xy = part.strip().split()
				if len(xy) == 2:
					coords.append((int(xy[0]), int(xy[1])))
		events.append(
			EventData(
				type=ev_type,
				start=start,
				end=end,
				player_idx=int(p_raw) if p_raw else None,
				organ_id=int(id_raw) if id_raw else None,
				organ_type=ot_raw if ot_raw else None,
				direction=dr_raw if dr_raw else None,
				coords=coords,
			)
		)
	return FrameData(storage=storage, messages=messages, events=events)


def _stdout_to_lines(raw) -> List[str]:
	if isinstance(raw, list):
		lines = raw
	else:
		lines = str(raw).split("\n")
	return [l.strip() for l in lines if l.strip()]


def _extract_graphics_from_view(view: str) -> Optional[str]:
	nl = view.find("\n")
	if nl < 0:
		return None
	payload = view[nl + 1 :].strip()
	if not payload:
		return None
	try:
		obj = _json.loads(payload)
	except Exception:
		return None
	g = obj.get("global") or {}
	graphics = g.get("graphics") or obj.get("graphics")
	return graphics


def _is_format_b(raw: Dict) -> bool:
	frames = raw.get("frames", [])
	if not frames:
		return False
	f0 = frames[0]
	return "view" in f0 or "agentId" in f0


def _load_format_a(raw: Dict) -> Replay:
	agents = raw.get("agents", [])
	raw_frames = raw.get("frames", [])

	global_data = _parse_global_data(raw_frames[0].get("data", ""))

	turns: List[ReplayTurn] = []
	for i, rf in enumerate(raw_frames[1:], start=1):
		fd_text = rf.get("data", "")
		try:
			frame_data = _parse_frame_data(fd_text)
		except Exception:
			frame_data = FrameData(storage=[[0, 0, 0, 0], [0, 0, 0, 0]], messages=[{}, {}], events=[])

		raw_stdout = rf.get("stdout", ["", ""])
		if isinstance(raw_stdout, str):
			raw_stdout = raw_stdout.split("\n\n")
		stdout = [_stdout_to_lines(raw_stdout[p]) if p < len(raw_stdout) else [] for p in range(2)]

		turns.append(
			ReplayTurn(
				turn=i,
				frame_data=frame_data,
				stdout=stdout,
				summary=rf.get("summary", "") or "",
			)
		)
	return Replay(agents=agents, global_data=global_data, turns=turns, raw=raw)


def _load_format_b(raw: Dict) -> Replay:
	agents = raw.get("agents", [])
	raw_frames = raw.get("frames", [])

	view0 = raw_frames[0].get("view", "")
	gfx0 = _extract_graphics_from_view(view0) or ""
	global_data = _parse_global_data(gfx0)

	turns: List[ReplayTurn] = []
	turn_num = 1
	i = 1
	while i < len(raw_frames):
		f0 = raw_frames[i]
		f1 = raw_frames[i + 1] if i + 1 < len(raw_frames) else {}

		cmd0 = _stdout_to_lines(f0.get("stdout", "WAIT"))
		cmd1 = _stdout_to_lines(f1.get("stdout", "WAIT"))
		stdout = [cmd0, cmd1]

		frame_data = FrameData(storage=[[0, 0, 0, 0], [0, 0, 0, 0]], messages=[{}, {}], events=[])
		for f in (f1, f0):
			view = f.get("view", "")
			gfx = _extract_graphics_from_view(view)
			if gfx:
				try:
					frame_data = _parse_frame_data(gfx)
					break
				except Exception:
					pass

		turns.append(
			ReplayTurn(
				turn=turn_num,
				frame_data=frame_data,
				stdout=stdout,
				summary=f1.get("summary", "") or "",
			)
		)
		turn_num += 1
		i += 2

	return Replay(agents=agents, global_data=global_data, turns=turns, raw=raw)


def _is_format_core_v1(raw: Dict) -> bool:
	return raw.get("format") == "cellularena-core-raw-v1"


def _load_format_core_v1(raw: Dict) -> Replay:
	"""Load the cellularena-core-raw-v1 format produced by download_games.py.

	This format stores only initial state + per-turn commands (no frame_data).
	"""
	agents = raw.get("agents", [])
	global_data = _parse_global_data(raw.get("globalData", ""))
	empty_frame_data = FrameData(storage=[[0, 0, 0, 0], [0, 0, 0, 0]], messages=[{}, {}], events=[])

	turns: List[ReplayTurn] = []
	for entry in raw.get("turns", []):
		raw_cmds = entry.get("commands", [[], []])
		stdout = [list(raw_cmds[p]) if p < len(raw_cmds) else [] for p in range(2)]
		turns.append(
			ReplayTurn(
				turn=entry["turn"],
				frame_data=empty_frame_data,
				stdout=stdout,
				summary="",
			)
		)
	return Replay(agents=agents, global_data=global_data, turns=turns, raw=raw)


def load_replay(path) -> Replay:
	data = _json.loads(Path(path).read_text(encoding="utf-8"))
	if "success" in data:
		data = data["success"]

	if _is_format_core_v1(data):
		return _load_format_core_v1(data)
	if _is_format_b(data):
		return _load_format_b(data)
	return _load_format_a(data)
