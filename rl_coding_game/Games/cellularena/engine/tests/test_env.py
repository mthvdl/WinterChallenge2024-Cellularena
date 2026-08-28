"""
Basic smoke-test / demo for the Cellularena PettingZoo environment.

Run with:
    cd rl_coding_game
    python test_env.py
"""
import sys
import time

import numpy as np
import pytest

from Games.cellularena import CellularenaEnv
from Games.cellularena.engine.game import MAX_TURNS


def run_random_episode(seed: int = 0) -> dict:
    env = CellularenaEnv(seed=seed)
    obs, infos = env.reset()
    for agent in env.possible_agents:
        env.action_space(agent).seed(seed)

    step_count = 0
    total_rewards = {"player_0": 0.0, "player_1": 0.0}

    while env.agents:
        actions = {agent: env.action_space(agent).sample() for agent in env.agents}
        obs, rewards, terminations, truncations, infos = env.step(actions)

        for agent, r in rewards.items():
            total_rewards[agent] += r

        step_count += 1

    p0_organs = env._game.players[0].organ_count
    p1_organs = env._game.players[1].organ_count

    return {
        "steps": step_count,
        "reason": env._game.terminal_reason,
        "final_organs": (p0_organs, p1_organs),
        "rewards": total_rewards,
    }


def test_observation_shapes():
    env = CellularenaEnv(seed=1)
    obs, _ = env.reset()
    for agent, agent_obs in obs.items():
        assert "grid" in agent_obs and "storage" in agent_obs and "turn" in agent_obs
        g = agent_obs["grid"]
        s = agent_obs["storage"]
        t = agent_obs["turn"]
        assert g.shape == (12, 24, 17), f"grid shape {g.shape}"
        assert s.shape == (2, 4),        f"storage shape {s.shape}"
        assert t.shape == (1,),          f"turn shape {t.shape}"
        assert g.min() >= 0.0 and g.max() <= 1.0
    print("  observation shapes OK")


def test_action_spaces():
    env = CellularenaEnv(seed=2)
    env.reset()
    for agent in env.possible_agents:
        sp = env.action_space(agent)
        sample = sp.sample()
        assert sp.contains(sample), "sampled action not in action space"
    print("  action spaces OK")


def test_potential_shaping_is_zero_sum_and_terminal_safe():
    env = CellularenaEnv(seed=3, reward_shaping=True)
    env.reset()
    env._game.set_storage([0, 0, 0, 0], [0, 0, 0, 0])
    env._game.turn = MAX_TURNS - 1
    env._potentials = env._state_potentials()

    _, rewards, terminations, _, _ = env.step(
        {"player_0": np.zeros(8, dtype=np.int64), "player_1": np.zeros(8, dtype=np.int64)}
    )

    assert terminations == {"player_0": True, "player_1": True}
    assert rewards == {"player_0": 0.0, "player_1": 0.0}
    assert env._potentials == [0.0, 0.0]


def test_potential_shaping_matches_difference_of_potentials():
    env = CellularenaEnv(seed=4, reward_shaping=True)
    env.reset()
    current = env._potentials[:]
    actions = {
        "player_0": np.zeros(8, dtype=np.int64),
        "player_1": np.zeros(8, dtype=np.int64),
    }
    _, rewards, terminations, _, _ = env.step(actions)
    assert not any(terminations.values())

    next_potentials = env._potentials[:]
    for player_idx, agent in enumerate(("player_0", "player_1")):
        expected = env._shaping_gamma * next_potentials[player_idx] - current[player_idx]
        assert rewards[agent] == pytest.approx(expected)
    assert rewards["player_0"] == pytest.approx(-rewards["player_1"])


def test_terminal_info_reports_harvest_and_storage():
    env = CellularenaEnv(seed=3, reward_shaping=False)
    env.reset()
    env._game.set_storage([0, 0, 0, 0], [0, 0, 0, 0])
    env._game.turn = MAX_TURNS - 1
    _, _, terminations, _, infos = env.step(
        {"player_0": np.zeros(8, dtype=np.int64), "player_1": np.zeros(8, dtype=np.int64)}
    )

    assert all(terminations.values())
    for player_idx, agent in enumerate(("player_0", "player_1")):
        assert infos[agent]["harvest_count"] == env._game.harvested_by_player[player_idx]
        assert infos[agent]["final_storage_total"] == env._game.players[player_idx].protein_total
        assert infos[agent]["final_organ_count"] == env._game.players[player_idx].organ_count
        assert infos[agent]["terminal_reason"] == env._game.terminal_reason


def test_full_episode():
    result = run_random_episode(seed=42)
    assert result["steps"] > 0
    assert result["reason"] in {
        "max_turns",
        "player_eliminated",
        "player_starved",
        "both_players_starved",
        "grid_full",
    }
    print(
        f"  episode done in {result['steps']} steps, "
        f"reason={result['reason']}, organs={result['final_organs']}, "
        f"rewards={result['rewards']}"
    )


def test_determinism():
    r1 = run_random_episode(seed=7)
    r2 = run_random_episode(seed=7)
    # Same seed → same outcome (NumPy random used inside spaces.sample differs,
    # but game internal rng is the same → same terminal reason & organ counts)
    assert r1["reason"] == r2["reason"], "non-deterministic terminal reason"
    print("  determinism OK (same terminal reason with same seed)")


if __name__ == "__main__":
    print("Running Cellularena PettingZoo environment tests...\n")
    tests = [
        test_observation_shapes,
        test_action_spaces,
        test_full_episode,
        test_determinism,
    ]
    passed = 0
    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"PASS  {name}")
            passed += 1
        except Exception as exc:
            print(f"FAIL  {name}: {exc}")
            import traceback; traceback.print_exc()

    print(f"\n{passed}/{len(tests)} tests passed.")
    sys.exit(0 if passed == len(tests) else 1)
