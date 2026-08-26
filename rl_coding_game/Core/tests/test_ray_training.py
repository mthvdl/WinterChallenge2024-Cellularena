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
	assert algorithm.saved_to == str(tmp_path / "checkpoint")
	assert len(seen) == 2
