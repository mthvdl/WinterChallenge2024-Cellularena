"""Reusable RLlib policy layouts for two-player self-play."""
from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
from typing import Any

from ray.rllib.policy.policy import PolicySpec


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
) -> tuple[dict[str, PolicySpec], Callable[..., str], list[str]]:
	"""Return policy specs, mapping, and policy IDs eligible for training."""
	if not frozen_opponent:
		return {"shared": PolicySpec()}, shared_policy_mapping, ["shared"]
	if not opponent_policy_ids:
		raise ValueError("At least one opponent policy is required.")
	policies = {"learner": PolicySpec()}
	policies.update({policy_id: PolicySpec() for policy_id in opponent_policy_ids})
	return (
		policies,
		league_policy_mapping(opponent_policy_ids),
		["learner"],
	)


def load_policy_from_checkpoint(
	algorithm: Any,
	checkpoint: str,
	source_policy_id: str = "shared",
	target_policy_id: str = "opponent",
) -> None:
	"""Copy one policy's weights from a checkpoint into a target algorithm."""
	if target_policy_id not in algorithm.config.policies:
		raise ValueError(f"Unknown target policy: {target_policy_id}")
	source_algorithm = type(algorithm).from_checkpoint(checkpoint)
	try:
		weights = source_algorithm.get_weights([source_policy_id])
		if source_policy_id not in weights:
			raise ValueError(f"Checkpoint has no policy named {source_policy_id!r}.")
		algorithm.set_weights({target_policy_id: weights[source_policy_id]})
	finally:
		source_algorithm.stop()