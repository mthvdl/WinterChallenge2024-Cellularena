"""Run discrete SAC on Cellularena with masked categorical actions."""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import torch

import ray
from ray.rllib.core.columns import Columns

from Core.ray_env import register_env
from Core.ray_config import LeaguePoolSettings, load_overrides, settings_dict
from Core.ray_policies import (
	load_policy_from_checkpoint,
	resolve_opponent_modes,
	resolve_opponent_policy_ids,
	seed_opponents_from_policy,
)
from Core.ray_training import print_metrics, train
from Core.replay_buffer_store import load_replay_buffer
from Core.league import discover_checkpoints, promote_checkpoint
from Core.project_paths import (
	algorithm_config_example,
	experiment_checkpoints_dir,
	experiment_replay_buffer_path,
	experiment_replays_dir,
	experiment_root,
	experiment_snapshot_dir,
)
from Games.cellularena.engine.action_adapter import N_ACTIONS
from Games.cellularena.engine.obs.runtime_bridge import IterativeActionRuntime
from Games.cellularena.factories import make_action_env
from Games.cellularena.ray.config import resolve_run_and_env_settings
from Games.cellularena.ray.evaluation import EVAL_OPPONENT_POLICY_ID, prepare_evaluation
from Games.cellularena.ray.sac.preprocessor import SACPreprocessor
from Games.cellularena.ray.env_wrapper import make_env_creator
from Games.cellularena.ray.sac.config import build_config
from Games.cellularena.ray.sac.modules import CNNSACNetwork


class _AlgorithmBot:
	def __init__(self, algorithm: Any, policy_id: str, history_steps: int = 1) -> None:
		self.algorithm = algorithm
		self.policy_id = policy_id
		self.preprocessor = SACPreprocessor(history_steps=history_steps)

	def _action_logits(self, observation: Any, action_mask: Any = None) -> torch.Tensor:
		features = self.preprocessor.build_features(observation)
		if action_mask is None:
			action_mask = np.ones(N_ACTIONS, dtype=np.float32)
		module = self.algorithm.get_module(self.policy_id)
		with torch.no_grad():
			outputs = module.forward_inference({Columns.OBS: {
				"observations": torch.from_numpy(features[None, ...]),
				"action_mask": torch.from_numpy(np.asarray(action_mask, dtype=np.float32)[None, :]),
			}})
		return outputs[Columns.ACTION_DIST_INPUTS]

	def select_action(self, observation: Any, deterministic: bool = True, action_mask: Any = None):
		logits = self._action_logits(observation, action_mask)
		if deterministic:
			action = torch.argmax(logits, dim=-1)
		else:
			action = torch.distributions.Categorical(logits=logits).sample()
		return int(action.item()), None

	def select_joint_action(
		self,
		observation: Any,
		game: Any,
		player_idx: int,
		deterministic: bool = True,
		action_mask: Any = None,
	):
		if not deterministic:
			raise ValueError("Joint action decoding currently requires deterministic inference.")
		logits = self._action_logits(observation, action_mask).squeeze(0).cpu().numpy()
		return IterativeActionRuntime().build_joint_action(game, player_idx, logits), None


def _make_replay_env_factory(env_settings: dict[str, Any], seed: int):
	return partial(make_action_env, seed=seed, **env_settings)


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
		overrides.setdefault("experiment", {})["iterations"] = args.iterations
	if args.num_env_runners is not None:
		overrides.setdefault("experiment", {}).setdefault("runner", {})["num_env_runners"] = args.num_env_runners
	run, env_settings = resolve_run_and_env_settings(overrides)
	run_iterations = run["iterations"]
	checkpoint_interval = run["checkpoint_interval"]
	league_pool = settings_dict(LeaguePoolSettings(), overrides.get("league_pool"))
	frozen_opponent, league_enabled = resolve_opponent_modes(
		league_pool["enabled"], args.frozen_opponent, bool(args.opponent_checkpoint)
	)
	league_pool_size = league_pool["max_size"]
	opponent_checkpoints = args.opponent_checkpoint
	if league_enabled and not opponent_checkpoints:
		opponent_checkpoints = list(reversed(discover_checkpoints(
			experiment_snapshot_dir("cellularena", "sac", args.experiment_name)
		)[:league_pool_size]))
	if league_enabled and not opponent_checkpoints:
		print("No league checkpoints found; seeding opponents from the initial learner.")
	opponent_policy_ids = resolve_opponent_policy_ids(
		frozen_opponent,
		league_enabled,
		league_pool_size,
		len(opponent_checkpoints),
		args.opponent_policy,
	)
	checkpoints_dir = experiment_checkpoints_dir("cellularena", "sac", args.experiment_name)

	register_env("cellularena_ray_sac", make_env_creator())
	ray.init(ignore_reinit_error=True, include_dashboard=True)
	algorithm = build_config(
		"cellularena_ray_sac",
		frozen_opponent=frozen_opponent,
		opponent_policy_ids=tuple(opponent_policy_ids),
		overrides=overrides,
		network_factory=CNNSACNetwork,
	).build_algo()
	try:
		replay_buffer_path = experiment_replay_buffer_path("cellularena", "sac", args.experiment_name)
		if args.resume_checkpoint:
			algorithm.restore(str(args.resume_checkpoint.resolve()))
			if replay_buffer_path.is_file():
				load_replay_buffer(algorithm.local_replay_buffer, replay_buffer_path)
				print(f"Replay buffer restored from {replay_buffer_path}")
		main_policy_id = "learner" if frozen_opponent else "shared"
		if run["evaluation_interval"]:
			seed_opponents_from_policy(algorithm, main_policy_id, [EVAL_OPPONENT_POLICY_ID])
		if league_enabled and not args.resume_checkpoint:
			seed_opponents_from_policy(algorithm, main_policy_id, opponent_policy_ids)
		if opponent_checkpoints:
			if len(opponent_checkpoints) > len(opponent_policy_ids) or (
				not league_enabled and len(opponent_checkpoints) != len(opponent_policy_ids)
			):
				raise ValueError("Opponent checkpoints exceed the available policy slots.")
			for policy_id, checkpoint in zip(opponent_policy_ids, opponent_checkpoints):
				load_policy_from_checkpoint(algorithm, str(checkpoint), target_policy_id=policy_id)
		start_iteration = 0
		if args.resume_checkpoint:
			start_iteration = int(args.resume_checkpoint.name.removeprefix("checkpoint_"))

		opponent_rotation = {
			"index": len(opponent_checkpoints) % len(opponent_policy_ids)
			if league_enabled
			else 0
		}

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

		def _prepare_evaluation(step: int) -> None:
			prepare_evaluation(
				algorithm,
				checkpoints_dir,
				step,
				args.experiment_name,
				experiment_replays_dir("cellularena", "sac", args.experiment_name)
				if run["save_evaluation_play"]
				else None,
				args.resume_checkpoint,
			)

		train(
			algorithm,
			run_iterations,
			checkpoints_dir,
			print_metrics,
			checkpoint_interval=checkpoint_interval,
			evaluation_interval=run["evaluation_interval"],
			checkpoint_callback=_refresh_league if league_enabled else None,
			evaluation_callback=_prepare_evaluation,
			start_iteration=start_iteration,
			replay_buffer_path=replay_buffer_path,
		)
	finally:
		algorithm.stop()
		ray.shutdown()


if __name__ == "__main__":
	main()