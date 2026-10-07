"""Small algorithm-agnostic Ray training loop."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from Core.ray_metrics import scalar_metrics
from Core.replay_buffer_store import save_replay_buffer


def train(
	algorithm: Any,
	iterations: int,
	checkpoint_dir: str | Path | None = None,
	metric_callback: Callable[[Mapping[str, Any]], None] | None = None,
	checkpoint_callback: Callable[[Path, int], None] | None = None,
	evaluation_callback: Callable[[int], None] | None = None,
	checkpoint_interval: int = 0,
	evaluation_interval: int = 0,
	start_iteration: int = 0,
	replay_buffer_path: str | Path | None = None,
) -> list[dict[str, Any]]:
	"""Train and optionally save checkpoints on a schedule.

	`evaluation_callback` runs before each `train()` call in which RLlib evaluates.
	With `replay_buffer_path`, the algorithm's replay buffer is overwritten there at each checkpoint.
	"""
	if iterations < 1:
		raise ValueError("iterations must be at least 1")
	if checkpoint_interval < 0 or evaluation_interval < 0:
		raise ValueError("checkpoint_interval and evaluation_interval cannot be negative")
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
			if evaluation_callback is not None and evaluation_interval and iteration % evaluation_interval == 0:
				evaluation_callback(iteration)
			result = algorithm.train()
			results.append(result)
			if writer is not None:
				for key, value in scalar_metrics(result).items():
					writer.add_scalar(key, value, iteration)
				writer.flush()
			if metric_callback is not None:
				metric_callback(result)
			should_checkpoint = checkpoint_interval and iteration % checkpoint_interval == 0
			if checkpoint_dir is not None and (should_checkpoint or iteration == final_iteration):
				checkpoint_path = Path(checkpoint_dir) / f"checkpoint_{iteration}"
				checkpoint_path.mkdir(parents=True, exist_ok=True)
				checkpoint = algorithm.save(str(checkpoint_path))
				if replay_buffer_path is not None:
					save_replay_buffer(algorithm.local_replay_buffer, replay_buffer_path)
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
