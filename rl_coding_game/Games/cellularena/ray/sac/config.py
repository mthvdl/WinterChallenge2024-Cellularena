"""Stock SAC configuration boundary for Cellularena."""
from __future__ import annotations

import math
from typing import Callable

from ray.rllib.algorithms.sac import SACConfig
from ray.rllib.core.rl_module.rl_module import RLModuleSpec
from Core.ray_config import settings_dict
from Core.ray_policies import policy_setup
from Games.cellularena.engine.action_adapter import N_ACTIONS
from Games.cellularena.ray.config import resolve_run_and_env_settings
from Games.cellularena.ray.sac.modules import CNNSACNetwork, MaskedSACTorchRLModule, SACNetwork
from Games.cellularena.ray.sac.replay_buffer import REPLAY_BUFFER_TYPES


def build_config(
    env_name: str = "cellularena_ray",
    num_env_runners: int = 0,
    frozen_opponent: bool = False,
    opponent_policy_ids: tuple[str, ...] = ("opponent",),
    auxiliary_policy_ids: tuple[str, ...] = (),
    overrides: dict | None = None,
    network_factory: Callable[[], SACNetwork] = CNNSACNetwork,
) -> SACConfig:
    """Build SAC settings for the discrete Cellularena action space."""
    policies, policy_mapping_fn, policies_to_train = policy_setup(
        frozen_opponent, opponent_policy_ids, auxiliary_policy_ids
    )
    values = overrides or {}
    run, env_settings = resolve_run_and_env_settings(values, num_env_runners)
    sac_values = values.get("sac") or {}
    if not isinstance(sac_values, dict):
        raise ValueError("The 'sac' configuration section must be a mapping.")

    supported_sac_keys = {
        "train_batch_size",
        "num_steps_sampled_before_learning_starts",
        "gamma",
        "actor_lr",
        "critic_lr",
        "target_entropy",
        "initial_alpha",
        "alpha_lr",
        "replay_type",
        "replay_capacity",
        "replay_alpha",
        "replay_beta",
    }
    unknown_sac_keys = set(sac_values) - supported_sac_keys
    if unknown_sac_keys:
        raise ValueError(
            "Unknown SAC configuration keys: "
            + ", ".join(sorted(unknown_sac_keys))
        )

    training_kwargs = {
        "train_batch_size_per_learner": sac_values["train_batch_size"]
    } if "train_batch_size" in sac_values else {}
    for key in (
        "num_steps_sampled_before_learning_starts",
        "gamma",
        "actor_lr",
        "critic_lr",
        "target_entropy",
        "initial_alpha",
        "alpha_lr",
    ):
        if key in sac_values:
            training_kwargs[key] = sac_values[key]
    if "target_entropy" not in training_kwargs:
        # RLlib's "auto" target entropy resolves to -np.prod(action_space.shape),
        # which is -1 for any Discrete space regardless of its size. Use a
        # size-aware default instead so entropy regularization isn't silently
        # broken for this large masked discrete action space; override via
        # sac.target_entropy if a different value is needed.
        training_kwargs["target_entropy"] = 0.5 * math.log(N_ACTIONS)

    replay_keys = {"replay_type", "replay_capacity", "replay_alpha", "replay_beta"}
    if replay_keys.intersection(sac_values):
        replay_config = {}
        if "replay_type" in sac_values:
            # Note: capacity/alpha/beta fall back to SACConfig()'s single-agent
            # defaults (capacity=1_000_000) unless also overridden below; pass
            # replay_capacity explicitly alongside replay_type to avoid this.
            replay_config.update(
                {
                    key: SACConfig().replay_buffer_config[key]
                    for key in ("capacity", "alpha", "beta")
                }
            )
        for source_key, target_key in (
            ("replay_type", "type"),
            ("replay_capacity", "capacity"),
            ("replay_alpha", "alpha"),
            ("replay_beta", "beta"),
        ):
            if source_key in sac_values:
                replay_config[target_key] = sac_values[source_key]
        # Frozen league/opponent episodes still get stored, but sampling is
        # restricted to trainable modules to avoid wasted per-iteration work.
        buffer_type = REPLAY_BUFFER_TYPES.get(replay_config.get("type"))
        if buffer_type is not None:
            replay_config["type"] = buffer_type
            replay_config["modules_to_sample"] = list(policies_to_train)
        training_kwargs["replay_buffer_config"] = replay_config
    config = (
        SACConfig()
        .rl_module(rl_module_spec=RLModuleSpec(module_class=MaskedSACTorchRLModule))
        .environment(env=env_name, env_config=env_settings)
        .framework("torch")
        .env_runners(
            num_env_runners=run["num_env_runners"],
            num_cpus_per_env_runner=run["num_cpus_per_env_runner"],
        )
        .training(**training_kwargs)
        .resources(
            num_gpus=run["num_gpus"],
            num_cpus_for_main_process=run["num_cpus_for_main_process"],
        )
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
