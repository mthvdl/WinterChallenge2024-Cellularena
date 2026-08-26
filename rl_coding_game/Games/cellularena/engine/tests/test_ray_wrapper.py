from Games.cellularena.factories import make_action_env
from Games.cellularena.engine.obs_mapper import CellularenaObsMapper
from Games.cellularena.ray.env_wrapper import CellularenaRayWrapper


def test_ray_wrapper_observation_contract() -> None:
	env = CellularenaRayWrapper(make_action_env(seed=0, map_height=8))
	observations, _ = env.reset()

	for agent in env.agents:
		observation = observations[agent]
		assert env.observation_space(agent).contains(observation)
		assert observation.shape == (8939,)
		assert observation[-4033:].dtype == "float32"
		assert set(observation[-4033:]).issubset({0.0, 1.0})

	env.close()


def test_ray_wrapper_continuous_action_adapter() -> None:
	env = CellularenaRayWrapper(make_action_env(seed=0, map_height=8), continuous_actions=True)
	assert env.action_space("player_0").contains([0.0])
	assert env._native_action([-1.0]) == 0
	assert env._native_action([1.0]) == 4032
	assert env._native_action([4.0]) == 4032
	env.close()


def test_ray_wrapper_accepts_custom_observation_mapper() -> None:
	env = CellularenaRayWrapper(
		make_action_env(seed=0, map_height=8),
		observation_mapper=CellularenaObsMapper(),
	)
	observations, _ = env.reset()

	for agent in env.agents:
		observation = observations[agent]
		assert observation.shape == (CellularenaObsMapper().output_dim(None) + 4033,)
		assert env.observation_space(agent).contains(observation)

	env.close()