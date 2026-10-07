from ray.rllib.algorithms.dqn import DQNConfig
import pytest

from Core.fixed_replay import FixedReplayDQN
from Games.cellularena.ray.dqn.config import build_config
from Games.cellularena.ray.dqn.modules import DQNNetwork, MaskedDQNTorchRLModule
import torch


def test_dqn_network_noop_preserves_config() -> None:
	config = DQNConfig()

	assert DQNNetwork().customize(config) is config


def test_dqn_config_wires_network_factory() -> None:
	class CustomNetwork(DQNNetwork):
		def customize(self, config: DQNConfig) -> DQNConfig:
			return config.training(
				model={
					"fcnet_hiddens": [128, 64],
					"post_fcnet_hiddens": [32],
				}
			)

	config = build_config(network_factory=CustomNetwork)

	assert config.model["fcnet_hiddens"] == [128, 64]
	assert config.model["post_fcnet_hiddens"] == [32]
	assert config.enable_rl_module_and_learner
	assert config.enable_env_runner_and_connector_v2


def test_dqn_config_uses_shared_replay_capacity() -> None:
	config = build_config(overrides={"experiment": {"replay_capacity": 1234}})

	assert config.replay_buffer_config["capacity"] == 1234


def test_dqn_fixed_replay_config() -> None:
	config = build_config(overrides={"experiment": {"replay_buffer_rotation": False}})

	assert config.algo_class is FixedReplayDQN
	assert config.min_sample_timesteps_per_iteration == 0


def test_dqn_config_rejects_shared_settings_in_dqn_section() -> None:
	with pytest.raises(ValueError, match="Unknown configuration keys: train_batch_size"):
		build_config(overrides={"dqn": {"train_batch_size": 64}})


def test_dqn_config_uses_shared_training_and_priority_settings() -> None:
	config = build_config(
		overrides={
			"experiment": {
				"train_batch_size": 64,
				"num_steps_sampled_before_learning_starts": 50,
				"gamma": 0.95,
				"replay_alpha": 0.7,
				"replay_beta": 0.8,
			}
		}
	)

	assert config.train_batch_size == 64
	assert config.num_steps_sampled_before_learning_starts == 50
	assert config.gamma == 0.95
	assert config.replay_buffer_config["alpha"] == 0.7
	assert config.replay_buffer_config["beta"] == 0.8


def test_masked_dqn_module_masks_invalid_actions() -> None:
	q_values = torch.tensor([[1.0, 2.0, 3.0]])
	mask = torch.tensor([[1.0, 0.0, 1.0]])

	masked = MaskedDQNTorchRLModule.apply_action_mask(q_values, mask)

	assert masked[0, 0] == 1.0
	assert masked[0, 2] == 3.0
	assert masked[0, 1] < -1e30