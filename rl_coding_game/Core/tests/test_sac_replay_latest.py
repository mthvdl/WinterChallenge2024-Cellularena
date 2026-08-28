from pathlib import Path

import pytest

from Games.cellularena.ray.sac.replay_latest import latest_checkpoint_pair


def test_latest_checkpoint_pair_uses_numeric_steps(tmp_path: Path) -> None:
	for name in ("checkpoint_9", "checkpoint_10", "checkpoint_100"):
		(tmp_path / name).mkdir()

	assert latest_checkpoint_pair(tmp_path) == (
		tmp_path / "checkpoint_100",
		tmp_path / "checkpoint_10",
	)


def test_latest_checkpoint_pair_requires_two_checkpoints(tmp_path: Path) -> None:
	(tmp_path / "checkpoint_10").mkdir()

	with pytest.raises(ValueError, match="At least two checkpoints"):
		latest_checkpoint_pair(tmp_path)