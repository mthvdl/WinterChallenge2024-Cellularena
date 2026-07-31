"""Prefill a prioritized replay buffer from offline replay files.

This script is game-agnostic. Replay parsing is delegated to a game-specific
 adapter implementing :class:`rl.offline_adapter.ReplayTransitionAdapter`.

Example
-------
python prefill_replay_buffer.py \
    --adapter games.cellularena.offline_replay_adapter:create_adapter \
    --glob "data/games/cellularena/replays/core_*.json" \
  --storage-dir replay_store \
  --capacity 200000
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from project_paths import shared_replays_dir
from rl.factory import load_symbol
from rl.offline_adapter import ReplayTransitionAdapter
from rl.prioritized_replay import PrioritizedReplayBuffer


def _iter_replay_paths(patterns: list[str]) -> Iterable[Path]:
    for pattern in patterns:
        p = Path(pattern)
        if p.exists() and p.is_file():
            yield p
            continue

        # Absolute path glob (Python 3.12 requires rooting from the pattern's anchor).
        if p.is_absolute():
            root = Path(p.anchor)
            rel = str(p.relative_to(root))
            for m in sorted(root.glob(rel)):
                if m.is_file():
                    yield m
        else:
            # Relative pattern — root at CWD.
            for m in sorted(Path(".").glob(pattern)):
                if m.is_file():
                    yield m


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adapter",
        required=True,
        help="module:factory returning ReplayTransitionAdapter",
    )
    parser.add_argument(
        "--glob",
        action="append",
        dest="patterns",
        default=[],
        help="Replay file path or glob pattern. Can be passed multiple times.",
    )
    parser.add_argument(
        "--game",
        default="cellularena",
        help="Game namespace used to resolve default replay glob.",
    )
    parser.add_argument("--storage-dir", default="replay_store")
    parser.add_argument("--capacity", type=int, default=200_000)
    parser.add_argument("--min-size", type=int, default=2_000)
    parser.add_argument("--per-alpha", type=float, default=0.5)
    parser.add_argument("--per-eps", type=float, default=1e-6)
    parser.add_argument("--parquet-export-interval", type=int, default=10_000)
    parser.add_argument(
        "--clear-first",
        action="store_true",
        help="Clear existing replay buffer contents before prefilling.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    if not args.patterns:
        default_pattern = str(shared_replays_dir(args.game) / "core_*.json")
        args.patterns = [default_pattern]

    factory = load_symbol(args.adapter)
    adapter = factory()
    if not isinstance(adapter, ReplayTransitionAdapter):
        raise TypeError(
            "Adapter factory must return ReplayTransitionAdapter. "
            f"Got: {type(adapter).__name__}"
        )

    replay_paths = list(dict.fromkeys(_iter_replay_paths(args.patterns)))
    if not replay_paths:
        raise FileNotFoundError("No replay files matched the provided --glob patterns.")

    buffer = PrioritizedReplayBuffer(
        capacity=args.capacity,
        min_size=args.min_size,
        storage_dir=args.storage_dir,
        per_alpha=args.per_alpha,
        per_eps=args.per_eps,
        parquet_export_interval=args.parquet_export_interval,
    )
    try:
        if args.clear_first:
            buffer.clear()

        total_transitions = 0
        total_files = 0

        for path in replay_paths:
            file_count = 0
            for transition in adapter.iter_transitions(path):
                buffer.add(transition)
                file_count += 1
                total_transitions += 1
            total_files += 1
            print(f"Loaded {file_count} transitions from {path}")

        print("---")
        print(f"Replay files processed: {total_files}")
        print(f"Transitions written:    {total_transitions}")
        print(f"Buffer size now:        {len(buffer)}")
        print(f"Buffer ready:           {buffer.is_ready}")
    finally:
        buffer.close()


if __name__ == "__main__":
    main()