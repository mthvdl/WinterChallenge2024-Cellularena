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


def test_train_overwrites_replay_buffer_file_at_each_checkpoint(tmp_path, monkeypatch) -> None:
	algorithm = FakeAlgorithm()
	algorithm.local_replay_buffer = object()
	saves = []
	monkeypatch.setattr(
		"Core.ray_training.save_replay_buffer",
		lambda buffer, path: saves.append((buffer, path, algorithm.calls)),
	)
	buffer_path = tmp_path / "replay_buffer.pkl"

	train(
		algorithm,
		5,
		tmp_path / "checkpoint",
		checkpoint_interval=2,
		replay_buffer_path=buffer_path,
	)

	buffer = algorithm.local_replay_buffer
	assert saves == [(buffer, buffer_path, 2), (buffer, buffer_path, 4), (buffer, buffer_path, 5)]


def test_train_runs_iterations_and_saves_checkpoint(tmp_path) -> None:
	algorithm = FakeAlgorithm()
	seen = []

	results = train(algorithm, 2, tmp_path / "checkpoint", seen.append)

	assert results == [{"training_iteration": 1}, {"training_iteration": 2}]
	assert algorithm.calls == 2
	assert algorithm.saved_to == str(tmp_path / "checkpoint" / "checkpoint_2")
	assert len(seen) == 2
	assert list((tmp_path / "tensorboard").glob("events.out.tfevents.*"))


def test_train_prepares_evaluation_before_evaluated_iterations(tmp_path) -> None:
	algorithm = FakeAlgorithm()
	checkpoints = []
	evaluations = []

	train(
		algorithm,
		5,
		tmp_path / "checkpoint",
		checkpoint_callback=lambda path, step: checkpoints.append((path, step)),
		evaluation_callback=lambda step: evaluations.append((step, algorithm.calls)),
		checkpoint_interval=2,
		evaluation_interval=3,
	)

	assert algorithm.calls == 5
	assert checkpoints == [
		(tmp_path / "checkpoint" / "checkpoint_2", 2),
		(tmp_path / "checkpoint" / "checkpoint_4", 4),
		(tmp_path / "checkpoint" / "checkpoint_5", 5),
	]
	assert evaluations == [(3, 2)]


def test_resumed_train_saves_checkpoint_at_final_iteration(tmp_path) -> None:
	algorithm = FakeAlgorithm()

	train(
		algorithm,
		20,
		tmp_path / "checkpoint",
		checkpoint_interval=100,
		start_iteration=300,
	)

	assert algorithm.calls == 20
	assert algorithm.saved_to == str(tmp_path / "checkpoint" / "checkpoint_320")
