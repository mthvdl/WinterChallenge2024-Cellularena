from pathlib import Path

from Viewer.viewer_server import _experiment_name_for_replay


def test_experiment_name_for_shared_experiments_root(tmp_path: Path) -> None:
    run_dir = tmp_path / "sac_full_run" / "replays"
    replay = run_dir / "episode.viewer.json"

    assert _experiment_name_for_replay(replay, tmp_path) == "sac_full_run"


def test_experiment_name_for_run_replays_root(tmp_path: Path) -> None:
    replay_root = tmp_path / "sac_full_run" / "replays"
    replay = replay_root / "episode.viewer.json"

    assert _experiment_name_for_replay(replay, replay_root) == "sac_full_run"


def test_experiment_name_for_flat_unassigned_root(tmp_path: Path) -> None:
    replay = tmp_path / "episode.viewer.json"

    assert _experiment_name_for_replay(replay, tmp_path) == "Unassigned"
