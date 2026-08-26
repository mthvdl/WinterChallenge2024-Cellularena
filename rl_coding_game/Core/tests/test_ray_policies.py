import pytest

from Core.ray_policies import league_policy_mapping, policy_setup


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