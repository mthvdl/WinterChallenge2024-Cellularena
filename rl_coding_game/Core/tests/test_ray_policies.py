import pytest

from Core.ray_policies import league_policy_mapping, load_policy_from_checkpoint, policy_setup


def test_shared_policy_setup() -> None:
	policies, mapping, policies_to_train = policy_setup()
	assert set(policies) == {"shared"}
	assert mapping("player_0") == "shared"
	assert mapping("player_1") == "shared"
	assert policies_to_train == ["shared"]


def test_frozen_opponent_policy_setup() -> None:
	policies, mapping, policies_to_train = policy_setup(frozen_opponent=True)
	assert set(policies) == {"learner", "opponent"}
	assert mapping("player_0") == "learner"
	assert mapping("player_1") == "opponent"
	assert policies_to_train == ["learner"]


def test_league_mapping_keeps_one_opponent_for_an_episode() -> None:
	policies, mapping, policies_to_train = policy_setup(
		frozen_opponent=True,
		opponent_policy_ids=("opponent_a", "opponent_b"),
	)
	episode = type("Episode", (), {"id_": "episode-17"})()

	assert set(policies) == {"learner", "opponent_a", "opponent_b"}
	assert mapping("player_0", episode) == "learner"
	assert mapping("player_1", episode) == mapping("player_1", episode)
	assert mapping("player_1", episode) in {"opponent_a", "opponent_b"}
	assert policies_to_train == ["learner"]


def test_league_mapping_requires_an_opponent() -> None:
	with pytest.raises(ValueError, match="At least one opponent"):
		league_policy_mapping(())


def test_load_policy_detects_learner_policy_from_league_checkpoint(tmp_path, monkeypatch) -> None:
	(tmp_path / "league_manifest.json").write_text(
		'{"source_policy_id": "learner"}', encoding="utf-8"
	)
	rl_module_dir = tmp_path / "learner_group" / "learner" / "rl_module" / "learner"
	rl_module_dir.mkdir(parents=True)

	class FakeModule:
		def get_state(self):
			return {"weight": 1}

	from ray.rllib.core.rl_module.rl_module import RLModule

	def fake_from_checkpoint(path, *args, **kwargs):
		assert path == str(rl_module_dir)
		return FakeModule()

	monkeypatch.setattr(RLModule, "from_checkpoint", staticmethod(fake_from_checkpoint))

	class TargetAlgorithm:
		config = type("Config", (), {"policies": {"opponent": object()}})()

		def set_weights(self, weights):
			self.weights = weights

	target = TargetAlgorithm()
	load_policy_from_checkpoint(target, str(tmp_path))
	assert target.weights == {"opponent": {"weight": 1}}


def test_load_policy_auto_detects_shared_policy_without_manifest(tmp_path, monkeypatch) -> None:
	rl_module_dir = tmp_path / "learner_group" / "learner" / "rl_module" / "shared"
	rl_module_dir.mkdir(parents=True)

	class FakeModule:
		def get_state(self):
			return {"weight": 2}

	from ray.rllib.core.rl_module.rl_module import RLModule

	monkeypatch.setattr(RLModule, "from_checkpoint", staticmethod(lambda path, *a, **kw: FakeModule()))

	class TargetAlgorithm:
		config = type("Config", (), {"policies": {"opponent": object()}})()

		def set_weights(self, weights):
			self.weights = weights

	target = TargetAlgorithm()
	load_policy_from_checkpoint(target, str(tmp_path))
	assert target.weights == {"opponent": {"weight": 2}}