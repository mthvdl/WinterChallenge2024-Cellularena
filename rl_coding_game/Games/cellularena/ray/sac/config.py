"""Stock SAC configuration boundary for Cellularena."""
from __future__ import annotations

from ray.rllib.algorithms.sac import SACConfig
from Core.ray_config import RayRunSettings, SACSettings, settings_dict
from Core.ray_policies import policy_setup


def build_config(
    env_name: str = "cellularena_ray",
    num_env_runners: int = 0,
    frozen_opponent: bool = False,
    opponent_policy_ids: tuple[str, ...] = ("opponent",),
    overrides: dict | None = None,
) -> SACConfig:
    """Build stock SAC settings using the explicit scalar action adapter."""
    policies, policy_mapping_fn, policies_to_train = policy_setup(
        frozen_opponent, opponent_policy_ids
    )
    values = overrides or {}
    run = settings_dict(RayRunSettings(num_env_runners=num_env_runners), values.get("run"))
    sac = settings_dict(SACSettings(), values.get("sac"))
    return (
        SACConfig()
        .environment(env=env_name, env_config={"map_height": run["map_height"], "obs_history_steps": run["obs_history_steps"]})
        .framework("torch")
        .env_runners(num_env_runners=run["num_env_runners"])
        .training(
            train_batch_size=sac["train_batch_size"],
            gamma=sac["gamma"],
            actor_lr=sac["actor_lr"],
            critic_lr=sac["critic_lr"],
        )
        .resources(num_gpus=run["num_gpus"])
        .multi_agent(
            policies=policies,
            policy_mapping_fn=policy_mapping_fn,
            policies_to_train=policies_to_train,
        )
    )
