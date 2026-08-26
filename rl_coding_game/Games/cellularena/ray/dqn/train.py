"""Run stock Rainbow DQN on Cellularena."""
from __future__ import annotations

import argparse
from pathlib import Path

import ray

from Core.ray_env import register_env
from Core.ray_config import load_overrides
from Core.ray_policies import load_policy_from_checkpoint
from Core.ray_training import print_metrics, train
from Games.cellularena.ray.dqn.feature_builder import DQNFeatureBuilder
from Games.cellularena.ray.dqn.config import build_config
from Games.cellularena.ray.env_wrapper import make_env_creator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--num-env-runners", type=int, default=None)
    parser.add_argument("--config", type=Path, default=None, help="JSON/YAML Ray config overrides")
    parser.add_argument("--frozen-opponent", action="store_true")
    parser.add_argument("--opponent-checkpoint", type=Path, action="append", default=[])
    parser.add_argument("--opponent-policy", action="append", default=None)
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    args = parser.parse_args()
    overrides = load_overrides(args.config) if args.config else {}
    if args.num_env_runners is not None:
        overrides.setdefault("run", {})["num_env_runners"] = args.num_env_runners

    register_env("cellularena_ray", make_env_creator(feature_builder_factory=DQNFeatureBuilder))
    ray.init(ignore_reinit_error=True, include_dashboard=False)
    algorithm = build_config(
        overrides=overrides,
        frozen_opponent=args.frozen_opponent,
        opponent_policy_ids=tuple(args.opponent_policy or ["opponent"]),
    ).build_algo()
    try:
        if args.opponent_checkpoint:
            if not args.frozen_opponent:
                raise ValueError("--opponent-checkpoint requires --frozen-opponent")
            opponent_policy_ids = args.opponent_policy or ["opponent"]
            if len(args.opponent_checkpoint) != len(opponent_policy_ids):
                raise ValueError("Each opponent policy needs exactly one matching checkpoint.")
            for policy_id, checkpoint in zip(opponent_policy_ids, args.opponent_checkpoint):
                load_policy_from_checkpoint(algorithm, str(checkpoint), target_policy_id=policy_id)
        train(algorithm, args.iterations, args.checkpoint_dir, print_metrics)
    finally:
        algorithm.stop()
        ray.shutdown()


if __name__ == "__main__":
    main()
