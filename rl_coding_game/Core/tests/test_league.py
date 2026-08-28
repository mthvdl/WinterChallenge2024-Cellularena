import json

from Core.league import MANIFEST_NAME, discover_checkpoints, promote_checkpoint


def test_promote_checkpoint_keeps_newest_pool_entries(tmp_path) -> None:
	source = tmp_path / "source"
	source.mkdir()
	(source / "weights").write_text("weights")
	pool = tmp_path / "pool"

	first = promote_checkpoint(source, pool, max_size=1)
	assert first.is_dir()
	assert (first / "weights").read_text() == "weights"
	assert json.loads((first / MANIFEST_NAME).read_text()) == {"source_policy_id": "shared"}

	second_source = tmp_path / "source_2"
	second_source.mkdir()
	(second_source / "weights").write_text("new weights")
	second = promote_checkpoint(second_source, pool, max_size=1)

	assert second.is_dir()
	assert sorted(path.name for path in pool.iterdir()) == ["source_2"]


def test_discover_checkpoints_only_reads_the_given_experiment_pool(tmp_path) -> None:
	current = tmp_path / "current" / "league_pool" / "checkpoint_1"
	other = tmp_path / "other" / "league_pool" / "checkpoint_2"
	current.mkdir(parents=True)
	other.mkdir(parents=True)

	assert discover_checkpoints(current.parent) == [current]


def test_discover_checkpoints_skips_experiments_without_a_pool(tmp_path) -> None:
	assert discover_checkpoints(tmp_path / "missing" / "league_pool") == []