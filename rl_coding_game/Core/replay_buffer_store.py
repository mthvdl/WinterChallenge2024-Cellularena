"""Persist an RLlib replay buffer to one experiment-level file, independent of checkpoints."""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Any

# Episode states hold the policy mapping fn, a local closure for league self-play.
from ray import cloudpickle


def save_replay_buffer(buffer: Any, path: str | Path) -> None:
    """Atomically overwrite `path` with the buffer state."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(path.name + ".tmp")
    with staged.open("wb") as file:
        cloudpickle.dump(buffer.get_state(), file, protocol=cloudpickle.DEFAULT_PROTOCOL)
    os.replace(staged, path)


def load_replay_buffer(buffer: Any, path: str | Path) -> None:
    with Path(path).open("rb") as file:
        state = cloudpickle.load(file)
    buffer.set_state(state)
    # RLlib (2.58) set_state bugs in multi-agent buffers:
    # this counter comes back as defaultdict(list), breaking `+= B` for new modules;
    if hasattr(buffer, "sampled_timesteps_per_module"):
        buffer.sampled_timesteps_per_module = defaultdict(
            int, buffer.sampled_timesteps_per_module
        )
    # and this inverse index is not saved, so the first eviction raises KeyError.
    if hasattr(buffer, "_sample_idx_to_tree_idx"):
        buffer._sample_idx_to_tree_idx = {
            sample_idx: tree_idx
            for tree_idx, sample_idx in buffer._tree_idx_to_sample_idx.items()
        }
