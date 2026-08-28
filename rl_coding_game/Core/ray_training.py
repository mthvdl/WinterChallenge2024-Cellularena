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
	checkpoint_callback: Callable[[Path, int], None] | None = None,
	replay_callback: Callable[[int], None] | None = None,
	checkpoint_interval: int = 0,
	replay_interval: int = 0,
	start_iteration: int = 0,
) -> list[dict[str, Any]]:
	"""Train and optionally save checkpoints or record replays on schedules."""
	if iterations < 1:
		raise ValueError("iterations must be at least 1")
	if checkpoint_interval < 0 or replay_interval < 0:
		raise ValueError("checkpoint_interval and replay_interval cannot be negative")
	if start_iteration < 0:
		raise ValueError("start_iteration cannot be negative")
	results: list[dict[str, Any]] = []
	final_iteration = start_iteration + iterations
	if checkpoint_dir is not None:
		from torch.utils.tensorboard import SummaryWriter

		writer = SummaryWriter(log_dir=Path(checkpoint_dir).parent / "tensorboard")
	else:
		writer = None
	try:
		for iteration in range(start_iteration + 1, final_iteration + 1):
			result = algorithm.train()
			results.append(result)
			if writer is not None:
				for key, value in scalar_metrics(result).items():
					writer.add_scalar(key, value, iteration)
				writer.flush()
			if metric_callback is not None:
				metric_callback(result)
			if replay_callback is not None and replay_interval and iteration % replay_interval == 0:
				replay_callback(iteration)
			should_checkpoint = checkpoint_interval and iteration % checkpoint_interval == 0
			if checkpoint_dir is not None and (should_checkpoint or iteration == final_iteration):
				checkpoint_path = Path(checkpoint_dir) / f"checkpoint_{iteration}"
				checkpoint_path.mkdir(parents=True, exist_ok=True)
				checkpoint = algorithm.save(str(checkpoint_path))
				if checkpoint_callback is not None:
					checkpoint_value = getattr(checkpoint, "checkpoint", checkpoint)
					checkpoint_path = Path(getattr(checkpoint_value, "path", checkpoint_value))
					checkpoint_callback(checkpoint_path, iteration)
	finally:
		if writer is not None:
			writer.close()
	return results


def print_metrics(result: Mapping[str, Any]) -> None:
	"""Print the common Ray metrics without dumping the full result tree."""
	print(scalar_metrics(result))
