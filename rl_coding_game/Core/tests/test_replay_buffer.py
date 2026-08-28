from Games.cellularena.ray.sac.replay_buffer import _ModulesToSampleMixin


class _FakeBuffer:
	def __init__(self, **kwargs) -> None:
		self.init_kwargs = kwargs

	def sample(self, *args, modules_to_sample=None, **kwargs):
		return modules_to_sample


class _TestBuffer(_ModulesToSampleMixin, _FakeBuffer):
	pass


def test_sample_defaults_to_configured_modules() -> None:
	buffer = _TestBuffer(capacity=10, modules_to_sample=["learner"])

	assert buffer.sample() == ["learner"]


def test_sample_explicit_modules_override_default() -> None:
	buffer = _TestBuffer(capacity=10, modules_to_sample=["learner"])

	assert buffer.sample(modules_to_sample=["opponent_000"]) == ["opponent_000"]


def test_sample_without_default_passes_none_through() -> None:
	buffer = _TestBuffer(capacity=10)

	assert buffer.sample() is None
