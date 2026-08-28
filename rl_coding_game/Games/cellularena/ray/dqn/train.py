"""Run stock Rainbow DQN on Cellularena."""
from __future__ import annotations

import argparse
import signal
import shutil
from datetime import datetime
from pathlib import Path

import ray

from Core.ray_env import register_env
from Core.ray_config import LeaguePoolSettings, load_overrides, settings_dict
from Core.ray_policies import load_policy_from_checkpoint
from Core.ray_training import print_metrics, train
from Core.league import discover_checkpoints, promote_checkpoint
from Core.project_paths import algorithm_config_example, experiment_checkpoints_dir, experiment_replays_dir, experiment_root, experiment_snapshot_dir
from Games.cellularena.ray.dqn.feature_builder import DQNFeatureBuilder
from Games.cellularena.ray.dqn.modules import DQNNetwork
from Games.cellularena.ray.dqn.config import build_config
from Games.cellularena.ray.env_wrapper import make_env_creator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--num-env-runners", type=int, default=None)
    parser.add_argument("--config", type=Path, default=None, help="JSON/YAML Ray config overrides")
    parser.add_argument("--frozen-opponent", action="store_true")
    parser.add_argument("--opponent-checkpoint", type=Path, action="append", default=[])
    parser.add_argument("--opponent-policy", action="append", default=None)
    parser.add_argument("--experiment-name", default=f"dqn_{datetime.now():%Y%m%d_%H%M%S}")
    args = parser.parse_args()
    root = experiment_root("cellularena", "dqn", args.experiment_name)
    config_source = args.config or algorithm_config_example("cellularena", "dqn")
    overrides = load_overrides(config_source) if config_source.exists() else {}
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_source, root / "config.yaml") if config_source.exists() else None
    for directory in (experiment_checkpoints_dir("cellularena", "dqn", args.experiment_name), experiment_replays_dir("cellularena", "dqn", args.experiment_name)):
        directory.mkdir(parents=True, exist_ok=True)
    if args.iterations is not None:
        overrides.setdefault("run", {})["iterations"] = args.iterations
    if args.num_env_runners is not None:
        overrides.setdefault("run", {})["num_env_runners"] = args.num_env_runners
    run_iterations = overrides.get("run", {}).get("iterations", 1)
    checkpoint_interval = overrides.get("run", {}).get("checkpoint_interval", 0)
    replay_interval = overrides.get("run", {}).get("replay_interval", 0)
    debug = overrides.get("run", {}).get("debug", False)
    league_pool = settings_dict(LeaguePoolSettings(), overrides.get("league_pool"))
    frozen_opponent = bool(league_pool["enabled"] or args.frozen_opponent or args.opponent_checkpoint)
    league_enabled = frozen_opponent
    league_pool_size = league_pool["max_size"]
    opponent_checkpoints = args.opponent_checkpoint
    if league_enabled and not opponent_checkpoints:
        opponent_checkpoints = discover_checkpoints(
            experiment_snapshot_dir("cellularena", "dqn", args.experiment_name)
        )[:league_pool_size]
    if league_enabled and not opponent_checkpoints:
        print("No league checkpoints found; starting with randomly initialized opponent policies.")
    opponent_policy_ids = args.opponent_policy or [
        f"opponent_{i:03d}" for i in range(max(len(opponent_checkpoints), 1 if league_enabled else 0))
    ]

    register_env("cellularena_ray", make_env_creator(feature_builder_factory=DQNFeatureBuilder, flatten_action_mask=True))
    ray.init(ignore_reinit_error=True, include_dashboard=debug)
    algorithm = build_config(
        overrides=overrides,
        frozen_opponent=frozen_opponent,
        opponent_policy_ids=tuple(opponent_policy_ids),
    ).build_algo()
    try:
        if opponent_checkpoints:
            if not league_enabled:
                raise ValueError("--opponent-checkpoint requires --frozen-opponent")
            if len(opponent_checkpoints) != len(opponent_policy_ids):
                raise ValueError("Each opponent policy needs exactly one matching checkpoint.")
            for policy_id, checkpoint in zip(opponent_policy_ids, opponent_checkpoints):
                load_policy_from_checkpoint(algorithm, str(checkpoint), target_policy_id=policy_id)
        main_policy_id = "learner" if frozen_opponent else "shared"
        opponent_rotation = {"index": 0}

        def _refresh_league(checkpoint_path: Path, step: int) -> None:
            promote_checkpoint(
                checkpoint_path,
                experiment_snapshot_dir("cellularena", "dqn", args.experiment_name),
                league_pool_size,
                main_policy_id,
            )
            target_policy_id = opponent_policy_ids[opponent_rotation["index"] % len(opponent_policy_ids)]
            opponent_rotation["index"] += 1
            algorithm.set_weights({target_policy_id: algorithm.get_weights([main_policy_id])[main_policy_id]})

        train(
            algorithm,
            run_iterations,
            experiment_checkpoints_dir("cellularena", "dqn", args.experiment_name),
            print_metrics,
            checkpoint_interval=checkpoint_interval,
            replay_interval=replay_interval,
            checkpoint_callback=_refresh_league if league_enabled else None,
        )
        if debug:
            print("Debug mode: Ray remains available until interrupted with Ctrl+C.")
            while True:
                signal.pause()
    finally:
        algorithm.stop()
        ray.shutdown()


if __name__ == "__main__":
    main()
