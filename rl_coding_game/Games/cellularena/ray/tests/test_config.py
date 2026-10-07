import pytest

from Games.cellularena.ray.config import resolve_run_and_env_settings
from Games.cellularena.ray.sac.train import _make_replay_env_factory


def test_resolves_separate_experiment_and_env_sections() -> None:
    run, env = resolve_run_and_env_settings(
        {
            "experiment": {"iterations": 12},
            "env": {"map_height": 10, "reward_shaping": True},
        },
        num_env_runners=3,
    )

    assert run["iterations"] == 12
    assert run["num_env_runners"] == 3
    assert "map_height" not in run
    assert env["map_height"] == 10
    assert env["reward_shaping"] is True


def test_resolves_runner_learner_and_evaluator_sections() -> None:
    run, env = resolve_run_and_env_settings(
        {
            "experiment": {
                "iterations": 12,
                "runner": {"num_env_runners": 4},
                "learner": {"num_gpus": 1},
                "evaluator": {"evaluation_interval": 5},
            },
        }
    )

    assert run["num_env_runners"] == 4
    assert run["iterations"] == 12
    assert run["num_gpus"] == 1
    assert run["evaluation_interval"] == 5
    assert env["map_height"] == 8


@pytest.mark.parametrize(
    "overrides",
    [
        {"run": {"iterations": 4}},
        {"runner": {"num_env_runners": 2}},
        {"experiment": {"replay_interval": 7}},
        {"experiment": {"replay_tv_interval": 7}},
        {"experiment": {"num_env_runners": 2}},
        {"experiment": {"map_height": 8}},
        {"experiment": {"learner": {"iterations": 4}}},
        {"experiment": {"runner": {"num_gpus": 1}}},
    ],
)
def test_rejects_legacy_structure(overrides) -> None:
    with pytest.raises(ValueError, match="Unknown"):
        resolve_run_and_env_settings(overrides)


def test_resolves_save_evaluation_play() -> None:
    run, env = resolve_run_and_env_settings(
        {"experiment": {"evaluator": {"save_evaluation_play": True}}}
    )

    assert run["save_evaluation_play"] is True
    assert "replay_tv_interval" not in run
    assert env["map_height"] == 8


def test_resolves_shared_replay_capacity_from_experiment_section() -> None:
    run, _ = resolve_run_and_env_settings({"experiment": {"replay_capacity": 1234}})

    assert run["replay_capacity"] == 1234


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