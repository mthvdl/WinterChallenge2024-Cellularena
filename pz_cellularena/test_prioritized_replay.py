"""Small smoke test for DuckDB/Parquet + SQLite PER replay storage.

Run with:
    cd pz_cellularena
    python test_prioritized_replay.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import types

import numpy as np


def _load_rl_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_replay_classes():
    """Load rl modules directly from files to avoid importing heavy optional deps."""
    root = Path(__file__).parent
    rl_dir = root / "rl"

    if "rl" not in sys.modules:
        pkg = types.ModuleType("rl")
        pkg.__path__ = [str(rl_dir)]
        sys.modules["rl"] = pkg

    experience_mod = _load_rl_module("rl.experience", rl_dir / "experience.py")
    _load_rl_module("rl.buffer", rl_dir / "buffer.py")
    prioritized_mod = _load_rl_module("rl.prioritized_replay", rl_dir / "prioritized_replay.py")

    return experience_mod.Transition, prioritized_mod.PrioritizedReplayBuffer


def test_prioritized_replay_storage() -> None:
    Transition, PrioritizedReplayBuffer = _load_replay_classes()

    with tempfile.TemporaryDirectory(prefix="per_store_") as tmp:
        store_dir = Path(tmp)
        buffer = PrioritizedReplayBuffer(
            capacity=32,
            min_size=1,
            storage_dir=store_dir,
            per_alpha=0.6,
            per_eps=1e-6,
            parquet_export_interval=0,
        )

        obs = {
            "grid": np.zeros((2, 2), dtype=np.float32),
            "turn": np.array([0.0], dtype=np.float32),
        }
        next_obs = {
            "grid": np.ones((2, 2), dtype=np.float32),
            "turn": np.array([1.0], dtype=np.float32),
        }

        for i in range(12):
            transition = Transition(
                obs=obs,
                action=np.array([i % 5], dtype=np.int64),
                reward=float(i),
                next_obs=next_obs,
                done=False,
            )
            buffer.add(transition)

        assert len(buffer) == 12, f"Expected 12 transitions, got {len(buffer)}"

        batch = buffer.sample(batch_size=6, beta=0.4)
        assert batch.indices is not None and batch.weights is not None
        assert batch.actions.shape[0] == 6
        assert batch.rewards.shape == (6,)
        assert batch.indices.shape == (6,)
        assert batch.weights.shape == (6,)
        assert np.all(np.isfinite(batch.weights))
        assert np.all(batch.weights > 0.0)
        assert np.all(batch.weights <= 1.0 + 1e-6)

        new_priorities = np.linspace(0.1, 1.0, num=6, dtype=np.float32)
        buffer.update_priorities(batch.indices, new_priorities)

        parquet_path = buffer.export_to_parquet()
        assert parquet_path.exists(), "Parquet export was not created"
        assert parquet_path.stat().st_size > 0, "Parquet export is empty"

        buffer.close()

        reopened = PrioritizedReplayBuffer(
            capacity=32,
            min_size=1,
            storage_dir=store_dir,
            per_alpha=0.6,
            per_eps=1e-6,
            parquet_export_interval=0,
        )
        assert len(reopened) == 12, f"Expected persisted size 12, got {len(reopened)}"

        batch2 = reopened.sample(batch_size=4, beta=0.5)
        assert batch2.indices is not None and batch2.weights is not None
        assert batch2.actions.shape[0] == 4

        reopened.close()


if __name__ == "__main__":
    print("Running prioritized replay storage smoke test...\n")
    try:
        test_prioritized_replay_storage()
        print("PASS  test_prioritized_replay_storage")
        sys.exit(0)
    except Exception as exc:
        print(f"FAIL  test_prioritized_replay_storage: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
