from Games.cellularena.factories import make_action_env
from Games.cellularena.ray.dqn.feature_builder import DQNFeatureBuilder
from Games.cellularena.ray.env_wrapper import CellularenaRayWrapper
from Games.cellularena.policy.action_mask import mask_logits
from Games.cellularena.policy.rl_module import mask_action_dist_inputs
import torch


def test_ray_wrapper_observation_contract() -> None:
	env = CellularenaRayWrapper(make_action_env(seed=0, map_height=8))
	observations, _ = env.reset()

	for agent in env.agents:
		observation = observations[agent]
		assert env.observation_space(agent).contains(observation)
		assert observation["observations"].shape == (26784,)
		assert observation["action_mask"].shape == (4033,)
		assert set(observation["action_mask"]).issubset({0.0, 1.0})

	env.close()


def test_ray_wrapper_uses_discrete_action_space() -> None:
	env = CellularenaRayWrapper(make_action_env(seed=0, map_height=8))
	assert env.action_space("player_0").n == 4033
	env.close()


def test_ray_wrapper_uses_encoded_observation() -> None:
	env = CellularenaRayWrapper(make_action_env(seed=0, map_height=8))
	observations, _ = env.reset()

	for agent in env.agents:
		observation = observations[agent]
		assert observation["observations"].shape == (26784,)
		assert env.observation_space(agent).contains(observation)

	env.close()


def test_ray_wrapper_accepts_algorithm_feature_builder() -> None:
	env = CellularenaRayWrapper(
		make_action_env(seed=0, map_height=8),
		feature_builder=DQNFeatureBuilder(),
	)
	observations, _ = env.reset()
	assert observations["player_0"]["observations"].shape == (26784,)
	env.close()


def test_mask_logits_disables_illegal_actions() -> None:
	logits = torch.zeros((1, 3))
	masked = mask_logits(logits, torch.tensor([[1, 0, 1]]))
	assert torch.isfinite(masked[0, 0])
	assert not torch.isfinite(masked[0, 1])


def test_mask_action_dist_inputs_uses_structured_observation() -> None:
	from ray.rllib.core.columns import Columns

	outputs = {Columns.ACTION_DIST_INPUTS: torch.zeros((1, 3))}
	batch = {
		Columns.OBS: {
			"observations": torch.zeros((1, 2)),
			"action_mask": torch.tensor([[1, 0, 1]]),
		}
	}

	masked = mask_action_dist_inputs(batch, outputs)

	assert not torch.isfinite(masked[Columns.ACTION_DIST_INPUTS][0, 1])