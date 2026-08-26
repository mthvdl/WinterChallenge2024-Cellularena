"""Metric helpers for local Ray runs."""
from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any


_METRIC_KEYS = (
	"training_iteration",
	"num_env_steps_sampled_lifetime",
	"num_env_steps_trained_lifetime",
	"episode_return_mean",
	"episode_len_mean",
	"loss",
	"evaluation/episode_return_mean",
)


def scalar_metrics(result: Mapping[str, Any]) -> dict[str, float]:
	"""Extract numeric top-level and nested evaluation metrics from a Ray result."""
	metrics: dict[str, float] = {}
	for key in _METRIC_KEYS:
		value: Any = result
		for part in key.split("/"):
			if not isinstance(value, Mapping) or part not in value:
				value = None
				break
			value = value[part]
		if isinstance(value, Real) and not isinstance(value, bool):
			metrics[key] = float(value)
	return metrics


def format_metrics(result: Mapping[str, Any]) -> str:
	"""Format the stable metric subset for console output."""
	return str(scalar_metrics(result))
