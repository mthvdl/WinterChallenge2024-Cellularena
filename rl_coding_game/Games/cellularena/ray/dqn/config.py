"""Editable stock Rainbow DQN configuration for Cellularena."""
from __future__ import annotations

from typing import Callable

from ray.rllib.algorithms.dqn import DQNConfig
from ray.rllib.core.rl_module.rl_module import RLModuleSpec
from Core.ray_env import make_multi_agent_replay_buffer
from Core.ray_config import DQNSettings, settings_dict
from Core.ray_policies import policy_setup
from Games.cellularena.ray.config import resolve_run_and_env_settings
from Games.cellularena.ray.dqn.modules import DQNNetwork, MaskedDQNTorchRLModule


def build_config(
    env_name: str = "cellularena_ray",
    num_env_runners: int = 0,
    frozen_opponent: bool = False,
    opponent_policy_ids: tuple[str, ...] = ("opponent",),
    overrides: dict | None = None,
    network_factory: Callable[[], DQNNetwork] = DQNNetwork,
) -> DQNConfig:
    """Build a local, single-runner Rainbow DQN configuration."""
    policies, policy_mapping_fn, policies_to_train = policy_setup(
        frozen_opponent, opponent_policy_ids
    )
    values = overrides or {}
    run, env_settings = resolve_run_and_env_settings(values, num_env_runners)
    dqn = settings_dict(DQNSettings(), values.get("dqn"))
    config = (
        DQNConfig()
        .rl_module(rl_module_spec=RLModuleSpec(module_class=MaskedDQNTorchRLModule))
        .environment(env=env_name, env_config=env_settings)
        .framework("torch")
        .env_runners(num_env_runners=run["num_env_runners"])
        .training(
            num_atoms=dqn["num_atoms"],
            noisy=dqn["noisy"],
            dueling=dqn["dueling"],
            double_q=dqn["double_q"],
            train_batch_size=dqn["train_batch_size"],
            replay_buffer_config={
                "type": make_multi_agent_replay_buffer(),
                "capacity": dqn["replay_capacity"],
                "alpha": dqn["replay_alpha"],
                "beta": dqn["replay_beta"],
            },
        )
        .resources(num_gpus=run["num_gpus"])
        .evaluation(
            evaluation_interval=run["evaluation_interval"],
            evaluation_num_env_runners=run["evaluation_num_env_runners"],
            evaluation_duration=run["evaluation_duration"],
            evaluation_duration_unit=run["evaluation_duration_unit"],
            evaluation_parallel_to_training=False,
            evaluation_config={"explore": run["evaluation_explore"]},
        )
        .multi_agent(
            policies=policies,
            policy_mapping_fn=policy_mapping_fn,
            policies_to_train=policies_to_train,
        )
    )
    return network_factory().customize(config)
