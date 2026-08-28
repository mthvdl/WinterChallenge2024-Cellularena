"""Metric helpers for local Ray runs."""
from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any


def scalar_metrics(result: Mapping[str, Any]) -> dict[str, float]:
	"""Extract numeric scalar metrics from a Ray result, including nested values."""
	metrics: dict[str, float] = {}

	def visit(value: Any, prefix: str = "") -> None:
		if isinstance(value, Mapping):
			for key, child in value.items():
				child_key = str(key)
				path = f"{prefix}/{child_key}" if prefix else child_key
				visit(child, path)
		elif prefix and isinstance(value, Real) and not isinstance(value, bool):
			metrics[prefix] = float(value)

	visit(result)
	return metrics


def format_metrics(result: Mapping[str, Any]) -> str:
	"""Format the stable metric subset for console output."""
	return str(scalar_metrics(result))
