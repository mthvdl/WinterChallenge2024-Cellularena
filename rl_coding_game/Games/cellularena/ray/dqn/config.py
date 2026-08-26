"""Editable stock Rainbow DQN configuration for Cellularena."""
from __future__ import annotations

from ray.rllib.algorithms.dqn import DQNConfig
from Core.ray_env import make_multi_agent_replay_buffer
from Core.ray_config import DQNSettings, RayRunSettings, settings_dict
from Core.ray_policies import policy_setup


def build_config(
    env_name: str = "cellularena_ray",
    num_env_runners: int = 0,
    frozen_opponent: bool = False,
    opponent_policy_ids: tuple[str, ...] = ("opponent",),
    overrides: dict | None = None,
) -> DQNConfig:
    """Build a local, single-runner Rainbow DQN configuration."""
    policies, policy_mapping_fn, policies_to_train = policy_setup(
        frozen_opponent, opponent_policy_ids
    )
    values = overrides or {}
    run = settings_dict(RayRunSettings(num_env_runners=num_env_runners), values.get("run"))
    dqn = settings_dict(DQNSettings(), values.get("dqn"))
    return (
        DQNConfig()
        .environment(env=env_name, env_config={"map_height": run["map_height"], "obs_history_steps": run["obs_history_steps"]})
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
        .multi_agent(
            policies=policies,
            policy_mapping_fn=policy_mapping_fn,
            policies_to_train=policies_to_train,
        )
    )
