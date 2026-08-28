from ray.rllib.algorithms.dqn import DQNConfig

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


def test_masked_dqn_module_masks_invalid_actions() -> None:
	q_values = torch.tensor([[1.0, 2.0, 3.0]])
	mask = torch.tensor([[1.0, 0.0, 1.0]])

	masked = MaskedDQNTorchRLModule.apply_action_mask(q_values, mask)

	assert masked[0, 0] == 1.0
	assert masked[0, 2] == 3.0
	assert masked[0, 1] < -1e30