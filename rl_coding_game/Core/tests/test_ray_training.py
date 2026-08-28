from Core.ray_training import train


class FakeAlgorithm:
	def __init__(self) -> None:
		self.calls = 0
		self.saved_to = None

	def train(self):
		self.calls += 1
		return {"training_iteration": self.calls}

	def save(self, path):
		self.saved_to = path
		return path


def test_train_runs_iterations_and_saves_checkpoint(tmp_path) -> None:
	algorithm = FakeAlgorithm()
	seen = []

	results = train(algorithm, 2, tmp_path / "checkpoint", seen.append)

	assert results == [{"training_iteration": 1}, {"training_iteration": 2}]
	assert algorithm.calls == 2
	assert algorithm.saved_to == str(tmp_path / "checkpoint" / "checkpoint_2")
	assert len(seen) == 2
	assert list((tmp_path / "tensorboard").glob("events.out.tfevents.*"))


def test_train_supports_independent_checkpoint_and_replay_intervals(tmp_path) -> None:
	algorithm = FakeAlgorithm()
	checkpoints = []
	replays = []

	train(
		algorithm,
		5,
		tmp_path / "checkpoint",
		checkpoint_callback=lambda path, step: checkpoints.append((path, step)),
		replay_callback=replays.append,
		checkpoint_interval=2,
		replay_interval=3,
	)

	assert algorithm.calls == 5
	assert checkpoints == [
		(tmp_path / "checkpoint" / "checkpoint_2", 2),
		(tmp_path / "checkpoint" / "checkpoint_4", 4),
		(tmp_path / "checkpoint" / "checkpoint_5", 5),
	]
	assert replays == [3]
