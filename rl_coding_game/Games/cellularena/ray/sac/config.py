"""Stock SAC configuration boundary for Cellularena."""
from __future__ import annotations

import math
from typing import Callable

from ray.rllib.algorithms.sac import SACConfig
from ray.rllib.core.rl_module.rl_module import RLModuleSpec
from Core.ray_config import complete_episodes_only, settings_dict
from Core.fixed_replay import FixedReplaySAC
from Core.ray_connectors import env_to_module_connector
from Core.ray_policies import policy_setup
from Games.cellularena.engine.action_adapter import N_ACTIONS
from Games.cellularena.ray.config import resolve_run_and_env_settings
from Games.cellularena.ray.evaluation import EVAL_OPPONENT_POLICY_ID, configure_evaluation
from Games.cellularena.ray.sac.preprocessor import SACPreprocessor
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
    values = overrides or {}
    run, env_settings = resolve_run_and_env_settings(values, num_env_runners)
    if run["evaluation_interval"] and EVAL_OPPONENT_POLICY_ID not in auxiliary_policy_ids:
        auxiliary_policy_ids = (*auxiliary_policy_ids, EVAL_OPPONENT_POLICY_ID)
    policies, policy_mapping_fn, policies_to_train = policy_setup(
        frozen_opponent, opponent_policy_ids, auxiliary_policy_ids
    )
    if not isinstance(run["replay_buffer_rotation"], bool):
        raise ValueError("replay_buffer_rotation must be true or false")
    if not run["replay_buffer_rotation"] and run["replay_capacity"] < 1:
        raise ValueError("replay_capacity must be positive for fixed replay")
    sac_values = values.get("sac") or {}
    if not isinstance(sac_values, dict):
        raise ValueError("The 'sac' configuration section must be a mapping.")

    supported_sac_keys = {
        "training_intensity",
        "actor_lr",
        "critic_lr",
        "target_entropy",
        "initial_alpha",
        "alpha_lr",
        "replay_type",
    }
    unknown_sac_keys = set(sac_values) - supported_sac_keys
    if unknown_sac_keys:
        raise ValueError(
            "Unknown SAC configuration keys: "
            + ", ".join(sorted(unknown_sac_keys))
        )

    training_kwargs = {}
    if run["train_batch_size"] is not None:
        training_kwargs["train_batch_size_per_learner"] = run["train_batch_size"]
    for key in ("num_steps_sampled_before_learning_starts", "gamma"):
        if run[key] is not None:
            training_kwargs[key] = run[key]
    for key in (
        "training_intensity",
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

    replay_config = dict(SACConfig().replay_buffer_config)
    replay_config["capacity"] = run["replay_capacity"]
    for key in ("replay_alpha", "replay_beta"):
        if run[key] is not None:
            replay_config[key.removeprefix("replay_")] = run[key]
    if "replay_type" in sac_values:
        replay_config["type"] = sac_values["replay_type"]
    # Capacity is shared across algorithms and applies even when the user leaves
    # SAC-specific replay type and priority settings at their defaults.
    buffer_type = REPLAY_BUFFER_TYPES.get(replay_config.get("type"))
    if buffer_type is not None:
        replay_config["type"] = buffer_type
        replay_config["modules_to_sample"] = list(policies_to_train)
    training_kwargs["replay_buffer_config"] = replay_config
    config = (
        SACConfig(algo_class=FixedReplaySAC if not run["replay_buffer_rotation"] else None)
        .rl_module(rl_module_spec=RLModuleSpec(module_class=MaskedSACTorchRLModule))
        .environment(env=env_name, env_config=env_settings)
        .framework("torch")
        .env_runners(
            num_env_runners=run["num_env_runners"],
            num_cpus_per_env_runner=run["num_cpus_per_env_runner"],
            env_to_module_connector=env_to_module_connector(
                SACPreprocessor, history_steps=env_settings["obs_history_steps"]
            ),
        )
        .training(**training_kwargs)
        .resources(
            num_gpus=run["num_gpus"],
            num_cpus_for_main_process=run["num_cpus_for_main_process"],
        )
        .multi_agent(
            policies=policies,
            policy_mapping_fn=policy_mapping_fn,
            policies_to_train=policies_to_train,
        )
    )
    configure_evaluation(
        config, run, env_settings, "learner" if frozen_opponent else "shared"
    )
    if not run["replay_buffer_rotation"]:
        # RLlib normally waits for more sampled steps before ending each train()
        # iteration, which would hang forever after sampling has stopped.
        config.reporting(min_sample_timesteps_per_iteration=0)
    return network_factory().customize(complete_episodes_only(config))
