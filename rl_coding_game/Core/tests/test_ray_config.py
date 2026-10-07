import json

import pytest

from Core.ray_config import DQNSettings, LeaguePoolSettings, load_overrides, settings_dict


def test_settings_dict_merges_known_overrides() -> None:
	values = settings_dict(DQNSettings(), {"num_atoms": 51})

	assert values["num_atoms"] == 51
	assert values["noisy"] is True


def test_settings_dict_rejects_unknown_keys() -> None:
	with pytest.raises(ValueError, match="Unknown configuration keys"):
		settings_dict(DQNSettings(), {"not_a_setting": 1})


def test_league_pool_is_disabled_by_default() -> None:
	assert settings_dict(LeaguePoolSettings()) == {"enabled": False, "max_size": 8}


def test_load_overrides_reads_json(tmp_path) -> None:
	path = tmp_path / "ray.json"
	path.write_text(json.dumps({"experiment": {"runner": {"num_env_runners": 1}}}), encoding="utf-8")

	assert load_overrides(path)["experiment"]["runner"]["num_env_runners"] == 1