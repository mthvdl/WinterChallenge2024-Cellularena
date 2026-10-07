import math

import pytest
from ray.rllib.algorithms.sac import SACConfig

from Core.fixed_replay import FixedReplaySAC
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
	assert config.replay_buffer_config["capacity"] == 10_000
	assert config.replay_buffer_config["alpha"] == 0.6
	assert config.replay_buffer_config["beta"] == 0.4
	assert config.algo_class is not FixedReplaySAC


def test_sac_config_uses_explicit_sac_overrides() -> None:
	config = build_config(
		overrides={
			"experiment": {
				"train_batch_size": 64,
				"num_steps_sampled_before_learning_starts": 500,
			},
			"sac": {
				"target_entropy": 2.5,
				"replay_type": "MultiAgentPrioritizedEpisodeReplayBuffer",
			},
		}
	)

	assert config.train_batch_size_per_learner == 64
	assert config.num_steps_sampled_before_learning_starts == 500
	assert config.target_entropy == 2.5
	assert config.replay_buffer_config["type"] is TrainableOnlySamplePrioritizedReplayBuffer
	assert config.replay_buffer_config["capacity"] == 10_000
	assert config.replay_buffer_config["alpha"] == 0.6
	assert config.replay_buffer_config["beta"] == 0.4
	# Only the trainable policy is sampled; frozen opponents stay stored but unsampled.
	assert config.replay_buffer_config["modules_to_sample"] == ["shared"]


def test_sac_config_uses_shared_replay_capacity() -> None:
	config = build_config(
		overrides={
			"experiment": {
				"replay_capacity": 1234,
				"train_batch_size": 64,
				"num_steps_sampled_before_learning_starts": 50,
				"gamma": 0.95,
				"replay_alpha": 0.7,
				"replay_beta": 0.8,
			}
		}
	)

	assert config.replay_buffer_config["capacity"] == 1234
	assert config.train_batch_size_per_learner == 64
	assert config.num_steps_sampled_before_learning_starts == 50
	assert config.gamma == 0.95
	assert config.replay_buffer_config["alpha"] == 0.7
	assert config.replay_buffer_config["beta"] == 0.8


def test_sac_fixed_replay_config() -> None:
	config = build_config(overrides={"experiment": {
		"replay_capacity": 1234, "replay_buffer_rotation": False,
	}})

	assert config.algo_class is FixedReplaySAC
	assert config.replay_buffer_config["capacity"] == 1234
	assert config.min_sample_timesteps_per_iteration == 0


@pytest.mark.parametrize("value", [0, "false", None])
def test_sac_fixed_replay_requires_boolean(value) -> None:
	with pytest.raises(ValueError, match="replay_buffer_rotation"):
		build_config(overrides={"experiment": {"replay_buffer_rotation": value}})


def test_sac_fixed_replay_requires_positive_capacity() -> None:
	with pytest.raises(ValueError, match="replay_capacity"):
		build_config(overrides={"experiment": {
			"replay_buffer_rotation": False, "replay_capacity": 0,
		}})


def test_sac_config_rejects_shared_settings_in_sac_section() -> None:
	with pytest.raises(ValueError, match="Unknown SAC configuration keys: replay_capacity"):
		build_config(overrides={"sac": {"replay_capacity": 2345}})


def test_sac_config_league_pool_only_samples_learner_module() -> None:
	config = build_config(
		frozen_opponent=True,
		opponent_policy_ids=("opponent_000", "opponent_001"),
		auxiliary_policy_ids=("replay_previous",),
		overrides={
			"sac": {
				"replay_type": "MultiAgentPrioritizedEpisodeReplayBuffer",
			}
		},
	)

	assert config.replay_buffer_config["type"] is TrainableOnlySamplePrioritizedReplayBuffer
	assert config.replay_buffer_config["modules_to_sample"] == ["learner"]
	assert set(config.policies) == {
		"learner",
		"opponent_000",
		"opponent_001",
		"replay_previous",
	}