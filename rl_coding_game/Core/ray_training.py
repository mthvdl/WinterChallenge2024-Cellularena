"""Small algorithm-agnostic Ray training loop."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from Core.ray_metrics import scalar_metrics


def train(
	algorithm: Any,
	iterations: int,
	checkpoint_dir: str | Path | None = None,
	metric_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
	"""Train for a fixed number of iterations and optionally save a checkpoint."""
	if iterations < 1:
		raise ValueError("iterations must be at least 1")
	results: list[dict[str, Any]] = []
	for _ in range(iterations):
		result = algorithm.train()
		results.append(result)
		if metric_callback is not None:
			metric_callback(result)
	if checkpoint_dir is not None:
		Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
		algorithm.save(str(checkpoint_dir))
	return results


def print_metrics(result: Mapping[str, Any]) -> None:
	"""Print the common Ray metrics without dumping the full result tree."""
	print(scalar_metrics(result))
