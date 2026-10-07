"""Editable stock Rainbow DQN configuration for Cellularena."""
from __future__ import annotations

from typing import Callable

from ray.rllib.algorithms.dqn import DQNConfig
from ray.rllib.core.rl_module.rl_module import RLModuleSpec
from Core.ray_env import make_multi_agent_replay_buffer
from Core.ray_config import DQNSettings, complete_episodes_only, settings_dict
from Core.fixed_replay import FixedReplayDQN
from Core.ray_connectors import env_to_module_connector
from Core.ray_policies import policy_setup
from Games.cellularena.ray.config import resolve_run_and_env_settings
from Games.cellularena.ray.evaluation import EVAL_OPPONENT_POLICY_ID, configure_evaluation
from Games.cellularena.ray.dqn.preprocessor import DQNPreprocessor
from Games.cellularena.ray.dqn.modules import DQNNetwork, MaskedDQNTorchRLModule

DEFAULT_TRAIN_BATCH_SIZE = 32
DEFAULT_REPLAY_ALPHA = 0.6
DEFAULT_REPLAY_BETA = 0.4


def build_config(
    env_name: str = "cellularena_ray",
    num_env_runners: int = 0,
    frozen_opponent: bool = False,
    opponent_policy_ids: tuple[str, ...] = ("opponent",),
    overrides: dict | None = None,
    network_factory: Callable[[], DQNNetwork] = DQNNetwork,
) -> DQNConfig:
    """Build a local, single-runner Rainbow DQN configuration."""
    values = overrides or {}
    run, env_settings = resolve_run_and_env_settings(values, num_env_runners)
    policies, policy_mapping_fn, policies_to_train = policy_setup(
        frozen_opponent,
        opponent_policy_ids,
        (EVAL_OPPONENT_POLICY_ID,) if run["evaluation_interval"] else (),
    )
    if not isinstance(run["replay_buffer_rotation"], bool):
        raise ValueError("replay_buffer_rotation must be true or false")
    if not run["replay_buffer_rotation"] and run["replay_capacity"] < 1:
        raise ValueError("replay_capacity must be positive for fixed replay")
    dqn = settings_dict(DQNSettings(), values.get("dqn"))
    config = (
        DQNConfig(algo_class=FixedReplayDQN if not run["replay_buffer_rotation"] else None)
        .rl_module(rl_module_spec=RLModuleSpec(module_class=MaskedDQNTorchRLModule))
        .environment(env=env_name, env_config=env_settings)
        .framework("torch")
        .env_runners(
            num_env_runners=run["num_env_runners"],
            env_to_module_connector=env_to_module_connector(
                DQNPreprocessor, history_steps=env_settings["obs_history_steps"]
            ),
        )
        .training(
            num_atoms=dqn["num_atoms"],
            noisy=dqn["noisy"],
            dueling=dqn["dueling"],
            double_q=dqn["double_q"],
            train_batch_size=(
                run["train_batch_size"]
                if run["train_batch_size"] is not None
                else DEFAULT_TRAIN_BATCH_SIZE
            ),
            training_intensity=dqn["training_intensity"],
            replay_buffer_config={
                "type": make_multi_agent_replay_buffer(),
                "capacity": run["replay_capacity"],
                "alpha": (
                    run["replay_alpha"]
                    if run["replay_alpha"] is not None
                    else DEFAULT_REPLAY_ALPHA
                ),
                "beta": (
                    run["replay_beta"]
                    if run["replay_beta"] is not None
                    else DEFAULT_REPLAY_BETA
                ),
            },
        )
        .resources(num_gpus=run["num_gpus"])
        .multi_agent(
            policies=policies,
            policy_mapping_fn=policy_mapping_fn,
            policies_to_train=policies_to_train,
        )
    )
    configure_evaluation(
        config, run, env_settings, "learner" if frozen_opponent else "shared"
    )
    shared_training = {
        key: run[key]
        for key in ("num_steps_sampled_before_learning_starts", "gamma")
        if run[key] is not None
    }
    if shared_training:
        config.training(**shared_training)
    if not run["replay_buffer_rotation"]:
        config.reporting(min_sample_timesteps_per_iteration=0)
    return network_factory().customize(complete_episodes_only(config))
