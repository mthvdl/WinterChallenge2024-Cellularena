"""Replay-driven engine correctness check wired into the pytest suite.

`validate_engine.py` reconstructs the authoritative game state turn-by-turn
from real CodinGame replays (GROW / DEATH / CRASH events + storage) and compares
it against the engine's output for storage, organ positions/types/directions,
and the per-player observation tensor. It is the strongest correctness signal
for the simulation, so it belongs in CI rather than only in a manual CLI.

By default a representative sample of replays is validated to keep the suite
fast. Set CELLULARENA_VALIDATE_ALL=1 to validate every downloaded replay.
"""
from __future__ import annotations

import contextlib
import io
import os

import pytest

from Games.cellularena.engine.tools.validate_engine import REPLAY_DIR, validate_replay


def _replay_files():
    if not REPLAY_DIR.is_dir():
        return []
    files = sorted(REPLAY_DIR.glob("codingame_*.json"))
    if os.environ.get("CELLULARENA_VALIDATE_ALL") == "1":
        return files
    # A spread across the download range keeps the sample representative while
    # staying well under a second per file.
    return files[::12]


REPLAY_FILES = _replay_files()


@pytest.mark.skipif(not REPLAY_FILES, reason="no CodinGame replays available")
@pytest.mark.parametrize("replay_path", REPLAY_FILES, ids=lambda p: p.name)
def test_engine_matches_reference_replay(replay_path):
    with contextlib.redirect_stdout(io.StringIO()):
        result = validate_replay(replay_path)

    issues = result.get("issues", [])
    assert not issues, (
        f"{replay_path.name}: engine diverged from reference on "
        f"{len(issues)} check(s); first few: " + "; ".join(issues[:5])
    )
