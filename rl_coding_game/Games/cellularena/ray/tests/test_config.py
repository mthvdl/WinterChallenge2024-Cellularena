import pytest

from Games.cellularena.ray.config import resolve_run_and_env_settings
from Games.cellularena.ray.sac.train import _make_replay_env_factory


def test_resolves_separate_run_and_env_sections() -> None:
    run, env = resolve_run_and_env_settings(
        {
            "run": {"iterations": 12},
            "env": {"map_height": 10, "reward_shaping": True},
        },
        num_env_runners=3,
    )

    assert run["iterations"] == 12
    assert run["num_env_runners"] == 3
    assert "map_height" not in run
    assert env["map_height"] == 10
    assert env["reward_shaping"] is True


def test_resolves_legacy_env_settings_from_run_section() -> None:
    run, env = resolve_run_and_env_settings(
        {"run": {"iterations": 4, "map_width": 18, "wall_ratio": 0.2}}
    )

    assert run["iterations"] == 4
    assert env["map_width"] == 18
    assert env["wall_ratio"] == 0.2


def test_rejects_env_setting_in_both_sections() -> None:
    with pytest.raises(ValueError, match="both 'run' and 'env'.*map_height"):
        resolve_run_and_env_settings(
            {"run": {"map_height": 8}, "env": {"map_height": 10}}
        )


def test_sac_replay_factory_propagates_resolved_env_settings(monkeypatch) -> None:
    env_settings = {
        "map_height": 6,
        "map_width": 10,
        "wall_ratio": 0.25,
        "protein_ratio": 0.1,
        "obs_history_steps": 2,
        "reward_shaping": True,
    }
    monkeypatch.setattr(
        "Games.cellularena.ray.sac.train.make_action_env",
        lambda **kwargs: kwargs,
    )

    result = _make_replay_env_factory(env_settings, seed=42)()

    assert result == {"seed": 42, **env_settings}