"""Reusable RLlib policy layouts for two-player self-play."""
from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from ray.rllib.policy.policy import PolicySpec


def resolve_opponent_modes(
	league_config_enabled: bool,
	frozen_opponent_requested: bool,
	has_opponent_checkpoints: bool,
) -> tuple[bool, bool]:
	league_enabled = bool(league_config_enabled)
	frozen_opponent = bool(
		league_enabled or frozen_opponent_requested or has_opponent_checkpoints
	)
	return frozen_opponent, league_enabled


def resolve_opponent_policy_ids(
	frozen_opponent: bool,
	league_enabled: bool,
	league_pool_size: int,
	checkpoint_count: int,
	requested_policy_ids: list[str] | None = None,
) -> list[str]:
	if requested_policy_ids is not None:
		return list(requested_policy_ids)
	if league_enabled:
		if league_pool_size < 1:
			raise ValueError("League pool size must be at least 1.")
		count = league_pool_size
	else:
		count = max(checkpoint_count, 1 if frozen_opponent else 0)
	return [f"opponent_{index:03d}" for index in range(count)]


def seed_opponents_from_policy(
	algorithm: Any,
	source_policy_id: str,
	opponent_policy_ids: list[str],
) -> None:
	if not opponent_policy_ids:
		return
	source_weights = algorithm.get_weights([source_policy_id])[source_policy_id]
	algorithm.set_weights({policy_id: source_weights for policy_id in opponent_policy_ids})


def shared_policy_mapping(agent_id: str, *args: Any, **kwargs: Any) -> str:
	"""Map every player to one shared policy."""
	del agent_id, args, kwargs
	return "shared"


def learner_opponent_mapping(agent_id: str, *args: Any, **kwargs: Any) -> str:
	"""Train player 0 and use a separate policy for player 1."""
	del args, kwargs
	return "learner" if agent_id.endswith("0") else "opponent"


def league_policy_mapping(
	opponent_policy_ids: tuple[str, ...],
	learner_policy_id: str = "learner",
) -> Callable[..., str]:
	"""Choose one fixed league opponent per episode.

	The mapping is deterministic for an episode, which keeps both calls for a
	player-1 trajectory on the same opponent while distributing episodes across
	the configured pool.
	"""
	if not opponent_policy_ids:
		raise ValueError("At least one opponent policy is required.")

	def mapping(agent_id: str, episode: Any = None, *args: Any, **kwargs: Any) -> str:
		del args, kwargs
		if agent_id.endswith("0"):
			return learner_policy_id
		episode_id = getattr(episode, "id_", getattr(episode, "id", "0"))
		index = int.from_bytes(sha256(str(episode_id).encode("utf-8")).digest()[:8], "big")
		return opponent_policy_ids[index % len(opponent_policy_ids)]

	return mapping


def policy_setup(
	frozen_opponent: bool = False,
	opponent_policy_ids: tuple[str, ...] = ("opponent",),
	auxiliary_policy_ids: tuple[str, ...] = (),
) -> tuple[dict[str, PolicySpec], Callable[..., str], list[str]]:
	"""Return policy specs, mapping, and policy IDs eligible for training."""
	if not frozen_opponent:
		policies = {"shared": PolicySpec()}
		policies.update({policy_id: PolicySpec() for policy_id in auxiliary_policy_ids})
		return policies, shared_policy_mapping, ["shared"]
	if not opponent_policy_ids:
		raise ValueError("At least one opponent policy is required.")
	policies = {"learner": PolicySpec()}
	policies.update({policy_id: PolicySpec() for policy_id in opponent_policy_ids})
	policies.update({policy_id: PolicySpec() for policy_id in auxiliary_policy_ids})
	return (
		policies,
		league_policy_mapping(opponent_policy_ids),
		["learner"],
	)


def load_policy_from_checkpoint(
	algorithm: Any,
	checkpoint: str,
	source_policy_id: str | None = None,
	target_policy_id: str = "opponent",
) -> None:
	"""Copy one policy's weights from a checkpoint into a target algorithm.

	Loads only the requested policy's `RLModule` directly (no full `Algorithm`/
	env-runner rebuild), which is both faster and accepts relative paths.
	"""
	from ray.rllib.core.rl_module.rl_module import RLModule

	if target_policy_id not in algorithm.config.policies:
		raise ValueError(f"Unknown target policy: {target_policy_id}")
	checkpoint_path = Path(checkpoint).resolve()
	rl_module_root = checkpoint_path / "learner_group" / "learner" / "rl_module"
	if source_policy_id is None:
		manifest_path = checkpoint_path / "league_manifest.json"
		if manifest_path.is_file():
			manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
			source_policy_id = manifest.get("source_policy_id")
		if not source_policy_id:
			for candidate in ("shared", "learner"):
				if (rl_module_root / candidate).is_dir():
					source_policy_id = candidate
					break
	if not source_policy_id:
		raise ValueError("Checkpoint has no supported policy (expected 'shared' or 'learner').")
	source_path = rl_module_root / source_policy_id
	if not source_path.is_dir():
		raise ValueError(f"Checkpoint has no policy named {source_policy_id!r}.")
	module = RLModule.from_checkpoint(str(source_path))
	algorithm.set_weights({target_policy_id: module.get_state()})