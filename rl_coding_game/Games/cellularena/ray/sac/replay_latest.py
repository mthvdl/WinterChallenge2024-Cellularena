"""Record the newest SAC checkpoint against its predecessor."""
from __future__ import annotations

import argparse
from functools import partial
from pathlib import Path

import ray

from Core.project_paths import (
	algorithm_experiments_root,
	experiment_checkpoints_dir,
	experiment_replays_dir,
	experiment_root,
)
from Core.ray_config import load_overrides
from Core.ray_env import register_env
from Core.ray_policies import load_policy_from_checkpoint
from Games.cellularena.engine.tools.game_recorder import save_checkpoint_replay
from Games.cellularena.factories import make_action_env
from Games.cellularena.ray.config import resolve_run_and_env_settings
from Games.cellularena.ray.env_wrapper import make_sac_env_creator
from Games.cellularena.ray.sac.config import build_config
from Games.cellularena.ray.sac.feature_builder import SACFeatureBuilder
from Games.cellularena.ray.sac.modules import CNNSACNetwork
from Games.cellularena.ray.sac.train import _AlgorithmBot


def checkpoint_step(path: Path) -> int:
	try:
		return int(path.name.removeprefix("checkpoint_"))
	except ValueError as exc:
		raise ValueError(f"Invalid checkpoint directory name: {path.name}") from exc


def latest_checkpoint_pair(checkpoints_dir: Path) -> tuple[Path, Path]:
	checkpoints = sorted(
		(path for path in checkpoints_dir.glob("checkpoint_*") if path.is_dir()),
		key=checkpoint_step,
		reverse=True,
	)
	if len(checkpoints) < 2:
		raise ValueError(f"At least two checkpoints are required in {checkpoints_dir}")
	return checkpoints[0], checkpoints[1]


def latest_experiment_name() -> str:
	experiments_root = algorithm_experiments_root("cellularena", "sac")
	candidates = [
		path
		for path in experiments_root.iterdir()
		if path.is_dir() and len(list((path / "checkpoints").glob("checkpoint_*"))) >= 2
	]
	if not candidates:
		raise ValueError(f"No SAC experiment with at least two checkpoints found in {experiments_root}")
	return max(candidates, key=lambda path: path.stat().st_mtime_ns).name


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--experiment-name", default=None)
	parser.add_argument("--seed", type=int, default=1)
	args = parser.parse_args()
	experiment_name = args.experiment_name or latest_experiment_name()
	root = experiment_root("cellularena", "sac", experiment_name)
	config_path = root / "config.yaml"
	if not config_path.is_file():
		raise ValueError(f"Experiment config not found: {config_path}")
	latest, previous = latest_checkpoint_pair(
		experiment_checkpoints_dir("cellularena", "sac", experiment_name)
	)
	overrides = load_overrides(config_path)
	overrides.setdefault("run", {}).update({
		"evaluation_interval": 0,
		"evaluation_num_env_runners": 0,
		"num_env_runners": 0,
		"num_gpus": 0,
	})
	_, env_settings = resolve_run_and_env_settings(overrides)

	register_env(
		"cellularena_ray_sac_replay",
		make_sac_env_creator(
			feature_builder_factory=partial(
				SACFeatureBuilder,
				history_steps=env_settings["obs_history_steps"],
			)
		),
	)
	ray.init(ignore_reinit_error=True, include_dashboard=False)
	algorithm = build_config(
		"cellularena_ray_sac_replay",
		frozen_opponent=True,
		opponent_policy_ids=("previous",),
		overrides=overrides,
		network_factory=CNNSACNetwork,
	).build_algo()
	try:
		load_policy_from_checkpoint(algorithm, str(latest), target_policy_id="learner")
		load_policy_from_checkpoint(algorithm, str(previous), target_policy_id="previous")
		output = save_checkpoint_replay(
			latest,
			partial(
				make_action_env,
				seed=args.seed,
				**env_settings,
			),
			_AlgorithmBot(algorithm, "learner", env_settings["obs_history_steps"]),
			"player_0",
			_AlgorithmBot(algorithm, "previous", env_settings["obs_history_steps"]),
			experiment_name,
			checkpoint_step(latest),
			previous.name,
			experiment_replays_dir("cellularena", "sac", experiment_name),
		)
		print(f"Replay saved: {output}")
	finally:
		algorithm.stop()
		ray.shutdown()


if __name__ == "__main__":
	main()