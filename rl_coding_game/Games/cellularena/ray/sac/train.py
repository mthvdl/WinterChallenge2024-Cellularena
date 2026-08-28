"""Run discrete SAC on Cellularena with masked categorical actions."""
from __future__ import annotations

import argparse
import signal
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch

import ray
from ray.rllib.core.columns import Columns

from Core.ray_env import register_env
from Core.ray_config import LeaguePoolSettings, load_overrides, settings_dict
from Core.ray_policies import load_policy_from_checkpoint
from Core.ray_training import print_metrics, train
from Core.league import discover_checkpoints, promote_checkpoint
from Core.project_paths import (
	algorithm_config_example,
	experiment_checkpoints_dir,
	experiment_replays_dir,
	experiment_root,
	experiment_snapshot_dir,
)
from Games.cellularena.engine.tools.game_recorder import save_checkpoint_replay
from Games.cellularena.factories import make_action_env
from Games.cellularena.ray.sac.feature_builder import SACFeatureBuilder
from Games.cellularena.ray.env_wrapper import make_sac_env_creator
from Games.cellularena.ray.sac.config import build_config
from Games.cellularena.ray.sac.modules import CNNSACNetwork


class _AlgorithmBot:
	def __init__(self, algorithm: Any, policy_id: str) -> None:
		self.algorithm = algorithm
		self.policy_id = policy_id

	def select_action(self, observation: Any, deterministic: bool = True, action_mask: Any = None):
		features = SACFeatureBuilder().build(observation)
		if action_mask is None:
			action_mask = np.ones(4033, dtype=np.float32)
		module = self.algorithm.get_module(self.policy_id)
		with torch.no_grad():
			outputs = module.forward_inference({Columns.OBS: {
				"observations": torch.from_numpy(features[None, ...]),
				"action_mask": torch.from_numpy(np.asarray(action_mask, dtype=np.float32)[None, :]),
			}})
		logits = outputs[Columns.ACTION_DIST_INPUTS]
		if deterministic:
			action = torch.argmax(logits, dim=-1)
		else:
			action = torch.distributions.Categorical(logits=logits).sample()
		return int(action.item()), None


def main() -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument("--iterations", type=int, default=None)
	parser.add_argument("--num-env-runners", type=int, default=None)
	parser.add_argument("--config", type=Path, default=None, help="JSON/YAML Ray config overrides")
	parser.add_argument("--resume-checkpoint", type=Path, default=None)
	parser.add_argument("--frozen-opponent", action="store_true")
	parser.add_argument("--opponent-checkpoint", type=Path, action="append", default=[])
	parser.add_argument("--opponent-policy", action="append", default=None)
	parser.add_argument("--experiment-name", default=f"sac_{datetime.now():%Y%m%d_%H%M%S}")
	args = parser.parse_args()
	root = experiment_root("cellularena", "sac", args.experiment_name)
	config_source = args.config or algorithm_config_example("cellularena", "sac")
	overrides = load_overrides(config_source) if config_source.exists() else {}
	root.mkdir(parents=True, exist_ok=True)
	shutil.copy2(config_source, root / "config.yaml") if config_source.exists() else None
	for directory in (experiment_checkpoints_dir("cellularena", "sac", args.experiment_name), experiment_replays_dir("cellularena", "sac", args.experiment_name)):
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
			experiment_snapshot_dir("cellularena", "sac", args.experiment_name)
		)[:league_pool_size]
	if league_enabled and not opponent_checkpoints:
		# Bootstrap case: no prior league checkpoint exists yet. Start with
		# randomly-initialized opponent policies instead of failing; the pool
		# fills in as checkpoints get promoted during this run (see below).
		print("No league checkpoints found; starting with randomly initialized opponent policies.")
	opponent_policy_ids = args.opponent_policy or [
		f"opponent_{i:03d}" for i in range(max(len(opponent_checkpoints), 1 if league_enabled else 0))
	]
	checkpoints_dir = experiment_checkpoints_dir("cellularena", "sac", args.experiment_name)

	register_env("cellularena_ray_sac", make_sac_env_creator(feature_builder_factory=SACFeatureBuilder))
	ray.init(ignore_reinit_error=True, include_dashboard=True)
	algorithm = build_config(
		"cellularena_ray_sac",
		frozen_opponent=frozen_opponent,
		opponent_policy_ids=tuple(opponent_policy_ids),
		overrides=overrides,
		network_factory=CNNSACNetwork,
	).build_algo()
	try:
		if args.resume_checkpoint:
			algorithm.restore(str(args.resume_checkpoint.resolve()))
		if opponent_checkpoints:
			if not league_enabled:
				raise ValueError("--opponent-checkpoint requires --frozen-opponent")
			if len(opponent_checkpoints) != len(opponent_policy_ids):
				raise ValueError("Each opponent policy needs exactly one matching checkpoint.")
			for policy_id, checkpoint in zip(opponent_policy_ids, opponent_checkpoints):
				load_policy_from_checkpoint(algorithm, str(checkpoint), target_policy_id=policy_id)
		main_policy_id = "learner" if frozen_opponent else "shared"
		opponent_policy_id = opponent_policy_ids[0] if frozen_opponent else "shared"
		main_bot = _AlgorithmBot(algorithm, main_policy_id)
		opponent_bot = _AlgorithmBot(algorithm, opponent_policy_id)
		start_iteration = 0
		if args.resume_checkpoint:
			start_iteration = int(args.resume_checkpoint.name.removeprefix("checkpoint_"))

		opponent_rotation = {"index": 0}

		def _refresh_league(checkpoint_path: Path, step: int) -> None:
			promote_checkpoint(
				checkpoint_path,
				experiment_snapshot_dir("cellularena", "sac", args.experiment_name),
				league_pool_size,
				main_policy_id,
			)
			# Also refresh one frozen opponent slot (round-robin) with the
			# learner's current in-memory weights, so this run's own league
			# pool keeps improving instead of staying fixed at startup.
			target_policy_id = opponent_policy_ids[opponent_rotation["index"] % len(opponent_policy_ids)]
			opponent_rotation["index"] += 1
			algorithm.set_weights({target_policy_id: algorithm.get_weights([main_policy_id])[main_policy_id]})

		train(
			algorithm,
			run_iterations,
			checkpoints_dir,
			print_metrics,
			checkpoint_interval=checkpoint_interval,
			replay_interval=replay_interval,
			checkpoint_callback=_refresh_league if league_enabled else None,
			replay_callback=lambda step: save_checkpoint_replay(
				Path(f"iteration_{step}"),
				lambda: make_action_env(map_height=8),
				main_bot,
				"player_0",
				opponent_bot,
				"cellularena-sac",
				step,
				opponent_policy_id,
				experiment_replays_dir("cellularena", "sac", args.experiment_name),
			),
			start_iteration=start_iteration,
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