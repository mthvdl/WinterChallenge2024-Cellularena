import numpy as np

from Games.cellularena.factories import make_action_env
from Games.cellularena.ray.dqn.feature_builder import DQNFeatureBuilder
from Games.cellularena.ray.env_wrapper import CellularenaRayWrapper, CellularenaSACWrapper
from Games.cellularena.ray.sac.feature_builder import SACFeatureBuilder, encode_observation
from Games.cellularena.ray.sac.modules import _SpatialEncoder, _SpatialHead, _SpatialModelConfig
from Games.cellularena.engine.action_adapter import transform_action_index
from gymnasium import spaces
import torch


def test_ray_wrapper_observation_contract() -> None:
	env = CellularenaRayWrapper(
		make_action_env(seed=0, map_height=8),
		feature_builder=DQNFeatureBuilder(),
	)
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


def test_sac_wrapper_uses_discrete_action_space() -> None:
	env = CellularenaSACWrapper(
		make_action_env(seed=0, map_height=8), feature_builder=SACFeatureBuilder()
	)
	assert env.action_space("player_0").n == 4033
	observation, _ = env.reset()
	assert env.observation_space("player_0").contains(observation["player_0"])
	assert observation["player_0"]["observations"].shape == (12, 24, 93)
	assert observation["player_0"]["action_mask"].shape == (4033,)
	env.close()


def test_ray_wrapper_uses_player_relative_action_mask() -> None:
	env = CellularenaRayWrapper(
		make_action_env(seed=0, map_height=8),
		feature_builder=SACFeatureBuilder(),
	)
	env.reset()
	player_one_mask = env._wrapped_observation(
		"player_1", env.env._get_obs(env.env._agent_to_idx["player_1"])
	)["action_mask"]

	assert np.array_equal(
		player_one_mask,
		env.env.action_mask("player_1").astype(np.float32)
	)
	env.close()


def test_sac_observation_uses_left_right_mirror_and_direction_swap() -> None:
	raw_grid = np.zeros((12, 24, 17), dtype=np.float32)
	# Original player 0 HARVESTER at (x=2, y=3), facing north.
	raw_grid[3, 2, 7] = 1.0
	raw_observation = {
		"grid": raw_grid,
		"storage": np.zeros((2, 4), dtype=np.float32),
		"turn": np.zeros((1,), dtype=np.float32),
		"self_player_idx": np.ones((1,), dtype=np.int32),
	}

	encoded = encode_observation(raw_observation).reshape(12, 24, 93)

	# Original player 0 is the opponent. Only x is reflected, and north
	# remains north under a left-right mirror.
	assert encoded[3, 21, 22] == 1.0
	assert encoded[9, 21, 22] == 0.0
	assert encoded[3, 21, 24] == 0.0


def test_sac_observation_swaps_derived_income_with_player_perspective() -> None:
	raw_grid = np.zeros((12, 24, 17), dtype=np.float32)
	# Original player 0 harvester faces protein A; player 1 has no harvester.
	raw_grid[3, 2, 8] = 1.0
	raw_grid[2, 2, 1] = 1.0
	raw_observation = {
		"grid": raw_grid,
		"storage": np.zeros((2, 4), dtype=np.float32),
		"turn": np.zeros((1,), dtype=np.float32),
		"self_player_idx": np.ones((1,), dtype=np.int32),
	}

	encoded = encode_observation(raw_observation).reshape(12, 24, 93)

	# Player 0 is the opponent from player 1's local perspective.
	assert encoded[:, :, 85].max() == 1.0
	assert encoded[:, :, 56].max() == 0.0


def test_sac_observation_keeps_global_features_normalized() -> None:
	raw_grid = np.zeros((12, 24, 17), dtype=np.float32)
	encoded = encode_observation(
		{
			"grid": raw_grid,
			"storage": np.asarray(((0.2, 0.4, 0.6, 0.8), (1.0, 0.0, 0.5, 0.25)), dtype=np.float32),
			"turn": np.asarray([0.75], dtype=np.float32),
			"self_player_idx": np.asarray([0], dtype=np.int32),
		}
	).reshape(12, 24, 93)

	assert encoded[:, :, 52:56].max() <= 1.0
	assert encoded[:, :, 74:78].max() <= 1.0
	assert encoded[:, :, 92].max() == 0.75


def test_sac_network_uses_identity_residual_and_role_aware_output_init() -> None:
	encoder = _SpatialEncoder()
	residual_tails = [
		block.layers[2].weight
		for block in encoder.net
		if hasattr(block, "layers")
	]
	assert residual_tails
	assert all(torch.count_nonzero(weight) == 0 for weight in residual_tails)

	policy = _SpatialHead(_SpatialModelConfig(input_dims=(32, 12, 24)), output_gain=0.01)
	critic = _SpatialHead(_SpatialModelConfig(input_dims=(32, 12, 24)), output_gain=1.0)
	assert policy.grow.weight.norm() < critic.grow.weight.norm() * 0.02


def test_sac_observation_is_equivariant_under_player_swap() -> None:
	raw_grid = np.zeros((12, 24, 17), dtype=np.float32)
	raw_grid[1, 2, 1] = 1.0
	raw_grid[4, 5, 4] = 1.0
	raw_grid[3, 3, 5] = 1.0
	raw_grid[3, 4, 8] = 1.0
	raw_grid[7, 18, 10] = 1.0
	raw_grid[8, 19, 13] = 1.0
	raw_grid[3, 3, 15] = 0.0
	raw_grid[3, 4, 15] = 1.0 / 3.0
	raw_grid[7, 18, 16] = 2.0 / 3.0
	raw_grid[8, 19, 16] = 1.0
	storage = np.asarray(((0.2, 0.4, 0.6, 0.8), (0.8, 0.6, 0.4, 0.2)), dtype=np.float32)

	mirrored_grid = np.zeros_like(raw_grid)
	mirrored_grid[:, :, :5] = raw_grid[:, ::-1, :5]
	mirrored_grid[:, :, 5:10] = raw_grid[:, ::-1, 10:15]
	mirrored_grid[:, :, 10:15] = raw_grid[:, ::-1, 5:10]
	direction_mirror = np.asarray((0, 3, 2, 1))
	mirrored_grid[:, :, 15] = direction_mirror[
		np.rint(raw_grid[:, ::-1, 16] * 3.0).astype(np.int64)
	] / 3.0
	mirrored_grid[:, :, 16] = direction_mirror[
		np.rint(raw_grid[:, ::-1, 15] * 3.0).astype(np.int64)
	] / 3.0

	player_zero_view = encode_observation(
		{"grid": raw_grid, "storage": storage, "turn": np.asarray([0.4]), "self_player_idx": np.asarray([0])}
	)
	player_one_view = encode_observation(
		{"grid": mirrored_grid, "storage": storage[::-1], "turn": np.asarray([0.4]), "self_player_idx": np.asarray([1])}
	)

	assert np.array_equal(player_zero_view, player_one_view)


def test_player_one_actions_transform_back_to_raw_coordinates() -> None:
	per_cell = 12 * 24
	local_east_harvester = 7 * per_cell + 3 * 24 + 2
	transformed = transform_action_index(local_east_harvester, player_idx=1)

	assert transformed == 9 * per_cell + 3 * 24 + 21


def test_ray_wrapper_uses_encoded_observation() -> None:
	env = CellularenaRayWrapper(
		make_action_env(seed=0, map_height=8),
		feature_builder=DQNFeatureBuilder(),
	)
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