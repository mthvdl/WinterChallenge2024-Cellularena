import math

import pytest
from ray.rllib.algorithms.sac import SACConfig

from Games.cellularena.engine.action_adapter import N_ACTIONS
from Games.cellularena.ray.sac.config import build_config
from Games.cellularena.ray.sac.modules import (
	CellularenaSACCatalog,
	MaskedSACTorchRLModule,
	SACNetwork,
)
from Games.cellularena.ray.sac.replay_buffer import (
	TrainableOnlySamplePrioritizedReplayBuffer,
)


def test_sac_network_noop_preserves_config() -> None:
	config = SACConfig()

	assert SACNetwork().customize(config) is config


def test_sac_config_uses_native_cnn_catalog() -> None:
	config = build_config()

	assert config.rl_module_spec.catalog_class is CellularenaSACCatalog


def test_sac_config_uses_new_stack_and_masked_module() -> None:
	config = build_config()

	assert config.enable_rl_module_and_learner
	assert config.enable_env_runner_and_connector_v2
	assert config.rl_module_spec.module_class is MaskedSACTorchRLModule
	assert config.train_batch_size_per_learner == 256
	assert config.num_steps_sampled_before_learning_starts == 1500
	assert config.actor_lr == 3e-05
	# RLlib's "auto" resolves to -1 for any Discrete space regardless of size;
	# build_config uses a size-aware default instead (see config.py).
	assert config.target_entropy == pytest.approx(0.5 * math.log(N_ACTIONS))
	assert config.replay_buffer_config["type"] == "PrioritizedEpisodeReplayBuffer"
	assert config.replay_buffer_config["alpha"] == 0.6
	assert config.replay_buffer_config["beta"] == 0.4


def test_sac_config_uses_explicit_sac_overrides() -> None:
	config = build_config(
		overrides={
			"sac": {
				"train_batch_size": 64,
				"num_steps_sampled_before_learning_starts": 500,
				"target_entropy": 2.5,
				"replay_type": "MultiAgentPrioritizedEpisodeReplayBuffer",
				"replay_capacity": 10000,
			}
		}
	)

	assert config.train_batch_size_per_learner == 64
	assert config.num_steps_sampled_before_learning_starts == 500
	assert config.target_entropy == 2.5
	assert config.replay_buffer_config["type"] is TrainableOnlySamplePrioritizedReplayBuffer
	assert config.replay_buffer_config["capacity"] == 10000
	assert config.replay_buffer_config["alpha"] == 0.6
	assert config.replay_buffer_config["beta"] == 0.4
	# Only the trainable policy is sampled; frozen opponents stay stored but unsampled.
	assert config.replay_buffer_config["modules_to_sample"] == ["shared"]


def test_sac_config_league_pool_only_samples_learner_module() -> None:
	config = build_config(
		frozen_opponent=True,
		opponent_policy_ids=("opponent_000", "opponent_001"),
		overrides={
			"sac": {
				"replay_type": "MultiAgentPrioritizedEpisodeReplayBuffer",
				"replay_capacity": 10000,
			}
		},
	)

	assert config.replay_buffer_config["type"] is TrainableOnlySamplePrioritizedReplayBuffer
	assert config.replay_buffer_config["modules_to_sample"] == ["learner"]