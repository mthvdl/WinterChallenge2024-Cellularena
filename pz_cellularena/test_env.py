"""
Basic smoke-test / demo for the Cellularena PettingZoo environment.

Run with:
    cd pz_cellularena
    python test_env.py
"""
import sys
import time

from games.cellularena import CellularenaEnv
from games.cellularena.game.game import MAX_TURNS


def run_random_episode(seed: int = 0) -> dict:
    env = CellularenaEnv(seed=seed)
    obs, infos = env.reset()

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


def test_full_episode():
    result = run_random_episode(seed=42)
    assert result["steps"] > 0
    assert result["reason"] in {"max_turns", "player_eliminated", "grid_full", "no_progress"}
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
