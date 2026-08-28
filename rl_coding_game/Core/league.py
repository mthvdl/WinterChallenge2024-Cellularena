"""League checkpoint promotion and discovery helpers."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path


MANIFEST_NAME = "league_manifest.json"


def promote_checkpoint(
	checkpoint_path: Path,
	pool_dir: Path,
	max_size: int,
	source_policy_id: str = "shared",
) -> Path:
	"""Copy a checkpoint into a bounded league pool and return its path."""
	if max_size < 1:
		raise ValueError("max_size must be at least 1")
	if not checkpoint_path.is_dir():
		raise ValueError(f"Checkpoint is not a directory: {checkpoint_path}")
	if not source_policy_id:
		raise ValueError("source_policy_id must not be empty")
	pool_dir.mkdir(parents=True, exist_ok=True)
	target = pool_dir / checkpoint_path.name
	with tempfile.TemporaryDirectory(dir=pool_dir) as temporary_dir:
		staged = Path(temporary_dir) / checkpoint_path.name
		shutil.copytree(checkpoint_path, staged)
		(staged / MANIFEST_NAME).write_text(
			json.dumps({"source_policy_id": source_policy_id}, indent=2) + "\n",
			encoding="utf-8",
		)
		if target.exists():
			shutil.rmtree(target)
		staged.rename(target)
	entries = sorted(
		(path for path in pool_dir.iterdir() if path.is_dir()),
		key=lambda path: (path.stat().st_mtime_ns, path.name),
		reverse=True,
	)
	for stale in entries[max_size:]:
		shutil.rmtree(stale)
	return target


def discover_checkpoints(pool_dir: Path) -> list[Path]:
	"""Find checkpoints in one experiment-owned league pool, newest first."""
	checkpoints = [
		path
		for path in (pool_dir.iterdir() if pool_dir.is_dir() else [])
		if path.is_dir()
	]
	return sorted(checkpoints, key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)


def latest_checkpoint_before(
	checkpoints_dir: Path,
	step: int,
	fallback: Path | None = None,
) -> Path | None:
	"""Return the highest numbered checkpoint strictly older than ``step``."""
	candidates: list[tuple[int, Path]] = []
	for path in checkpoints_dir.glob("checkpoint_*"):
		if not path.is_dir():
			continue
		try:
			checkpoint_step = int(path.name.removeprefix("checkpoint_"))
		except ValueError:
			continue
		if checkpoint_step < step:
			candidates.append((checkpoint_step, path))
	return max(candidates, default=(0, fallback), key=lambda item: item[0])[1]