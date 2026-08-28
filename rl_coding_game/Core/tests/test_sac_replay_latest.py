from pathlib import Path

import pytest

from Games.cellularena.ray.sac.replay_latest import latest_checkpoint_pair
from Games.cellularena.ray.sac import train as sac_train


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


def test_replay_policy_uses_immediately_previous_network(tmp_path: Path, monkeypatch) -> None:
	loaded = []
	monkeypatch.setattr(
		sac_train,
		"load_policy_from_checkpoint",
		lambda algorithm, checkpoint, target_policy_id: loaded.append(
			(checkpoint, target_policy_id)
		),
	)
	algorithm = object()

	assert sac_train._load_previous_replay_policy(
		algorithm, tmp_path, 10, "replay_previous"
	) == "initial_network"
	(tmp_path / "checkpoint_10").mkdir()
	assert sac_train._load_previous_replay_policy(
		algorithm, tmp_path, 20, "replay_previous"
	) == "checkpoint_10"
	(tmp_path / "checkpoint_20").mkdir()
	assert sac_train._load_previous_replay_policy(
		algorithm, tmp_path, 30, "replay_previous"
	) == "checkpoint_20"

	assert loaded == [
		(str(tmp_path / "checkpoint_10"), "replay_previous"),
		(str(tmp_path / "checkpoint_20"), "replay_previous"),
	]