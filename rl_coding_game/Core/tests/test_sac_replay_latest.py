from pathlib import Path

import pytest

from Games.cellularena.ray.sac.replay_latest import latest_checkpoint_pair
from Games.cellularena.ray import evaluation


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


def test_evaluation_opponent_uses_immediately_previous_network(tmp_path: Path, monkeypatch) -> None:
	loaded = []
	monkeypatch.setattr(
		evaluation,
		"load_policy_from_checkpoint",
		lambda algorithm, checkpoint, target_policy_id: loaded.append(
			(checkpoint, target_policy_id)
		),
	)
	algorithm = object()

	assert evaluation.prepare_evaluation(
		algorithm, tmp_path, 10, "exp", None
	) == "initial_network"
	(tmp_path / "checkpoint_10").mkdir()
	assert evaluation.prepare_evaluation(
		algorithm, tmp_path, 20, "exp", None
	) == "checkpoint_10"
	(tmp_path / "checkpoint_20").mkdir()
	assert evaluation.prepare_evaluation(
		algorithm, tmp_path, 30, "exp", None
	) == "checkpoint_20"

	policy_id = evaluation.EVAL_OPPONENT_POLICY_ID
	assert loaded == [
		(str(tmp_path / "checkpoint_10"), policy_id),
		(str(tmp_path / "checkpoint_20"), policy_id),
	]


def test_evaluation_tags_eval_runners_for_replay(tmp_path: Path) -> None:
	class Runner:
		pass

	runner = Runner()

	class Group:
		def foreach_env_runner(self, func):
			func(runner)

	class Algorithm:
		eval_env_runner_group = Group()

	evaluation.prepare_evaluation(Algorithm(), tmp_path, 10, "exp", tmp_path)

	assert getattr(runner, evaluation._REPLAY_TAG_ATTR) == {
		"step": 10,
		"experiment_name": "exp",
		"opponent_name": "initial_network",
		"output_dir": str(tmp_path),
	}