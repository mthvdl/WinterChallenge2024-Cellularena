"""Display effective SAC settings and refuse to overlap an existing Ray run."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from Core.ray_config import load_overrides
from Games.cellularena.ray.config import EXPERIMENT_SUBSECTION_KEYS, resolve_run_and_env_settings
from Games.cellularena.ray.sac.config import build_config


def main() -> int:
    path = Path("Games/cellularena/experiments/sac/config.yaml")
    overrides = load_overrides(path)
    run, env = resolve_run_and_env_settings(overrides)
    config = build_config(overrides=overrides)

    port = subprocess.run(
        ["ss", "-ltnp", "( sport = :8265 )"], capture_output=True, text=True, check=True
    )
    trainers = subprocess.run(
        ["pgrep", "-af", "python( -u)? -m Games[.]cellularena[.]ray[.]sac[.]train"],
        capture_output=True, text=True, check=False,
    )
    print("Ray dashboard on 127.0.0.1:8265:", port.stdout.strip() or "none")
    print("Existing SAC trainers:", trainers.stdout.strip() or "none")
    if len(port.stdout.splitlines()) > 1 or trainers.returncode == 0:
        print("ABORT: another Ray dashboard or SAC trainer is running.", file=sys.stderr)
        return 1

    print(f"game=cellularena algorithm=SAC config={path} experiment=sac_fixed_replay_20260929_v2")
    experiment = overrides.get("experiment") or {}
    yaml_run_keys = {key for key in experiment if key not in EXPERIMENT_SUBSECTION_KEYS}
    for section in EXPERIMENT_SUBSECTION_KEYS:
        yaml_run_keys |= set(experiment.get(section) or {})
    for section, values, yaml_keys in (
        ("experiment", run, yaml_run_keys),
        ("env", env, set(overrides.get("env") or {})),
    ):
        print(f"{section}:")
        for key, value in values.items():
            source = "YAML" if key in yaml_keys else "project default"
            print(f"  {key}: {value!r} ({source})")
    print("league_pool:", overrides.get("league_pool", {}))
    print("SAC settings:")
    for key in (
        "training_intensity", "actor_lr", "critic_lr", "target_entropy",
        "initial_alpha", "alpha_lr", "tau", "n_step", "gamma",
        "num_steps_sampled_before_learning_starts", "train_batch_size_per_learner",
        "min_sample_timesteps_per_iteration",
        "min_time_s_per_iteration",
    ):
        from_yaml = key in overrides.get("sac", {}) or (
            key == "train_batch_size_per_learner" and "train_batch_size" in yaml_run_keys
        )
        source = "YAML" if from_yaml else "RLlib/project default"
        print(f"  {key}: {getattr(config, key)!r} ({source})")
    print("  replay_buffer_config:", config.replay_buffer_config)
    print("  resolved num_env_runners:", config.num_env_runners)
    print("  resolved num_gpus:", config.num_gpus)
    print("  evaluation:", config.evaluation_interval, config.evaluation_num_env_runners,
          config.evaluation_duration, config.evaluation_duration_unit, config.evaluation_config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())