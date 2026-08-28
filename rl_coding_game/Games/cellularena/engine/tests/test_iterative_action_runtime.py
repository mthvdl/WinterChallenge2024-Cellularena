import numpy as np
import torch
from ray.rllib.core.columns import Columns

from Games.cellularena.engine.action_adapter import (
    N_ACTIONS,
    transform_action_index,
    transform_action_values,
)
from Games.cellularena.engine.game import Game, MAX_ROOTS, MAX_TURNS
from Games.cellularena.engine.obs.runtime_bridge import IterativeActionRuntime
from Games.cellularena.engine.tools.game_recorder import record_episode
from Games.cellularena.factories import make_action_env
from Games.cellularena.ray.sac.train import _AlgorithmBot


def _two_root_game() -> Game:
    lines = ["24 12"]
    lines.extend("0 X" for _ in range(24 * 12))
    lines.extend(("2", "1 1 1 ROOT N 0", "2 10 1 ROOT N 0"))
    lines.extend(("1", "3 22 10 ROOT N 0"))
    game = Game()
    game.init_from_global_data("\n".join(lines))
    game.set_storage([10, 10, 10, 10], [10, 10, 10, 10])
    return game


def test_one_score_vector_selects_actions_for_multiple_roots() -> None:
    game = _two_root_game()
    scores = np.full(N_ACTIONS, -10.0, dtype=np.float32)
    per_channel = 12 * 24
    scores[per_channel + 1 * 24 + 2] = 10.0
    scores[per_channel + 1 * 24 + 11] = 9.0

    joint_action = IterativeActionRuntime().build_joint_action(game, 0, scores)

    assert joint_action.shape == (MAX_ROOTS,)
    assert np.count_nonzero(joint_action) == 2


def test_player_one_scores_transform_to_raw_coordinates() -> None:
    local_action = 7 * (12 * 24) + 3 * 24 + 2
    raw_action = transform_action_index(local_action, player_idx=1)
    scores = np.zeros(N_ACTIONS, dtype=np.float32)
    scores[local_action] = 7.0

    transformed = transform_action_values(scores, player_idx=1)

    assert transformed[raw_action] == 7.0


def test_algorithm_bot_uses_one_forward_for_joint_action() -> None:
    env = make_action_env(seed=1, map_height=8, reward_shaping=False)
    observations, _ = env.reset()

    class FakeModule:
        def __init__(self) -> None:
            self.forward_calls = 0

        def forward_inference(self, batch):
            self.forward_calls += 1
            return {
                Columns.ACTION_DIST_INPUTS: torch.zeros(
                    (1, N_ACTIONS), dtype=torch.float32
                )
            }

    module = FakeModule()
    algorithm = type("FakeAlgorithm", (), {"get_module": lambda self, policy_id: module})()
    bot = _AlgorithmBot(algorithm, "learner")

    action, _ = bot.select_joint_action(
        observations["player_0"],
        game=env._game,
        player_idx=0,
        action_mask=env.action_mask("player_0"),
    )

    assert module.forward_calls == 1
    assert action.shape == (MAX_ROOTS,)
    env.close()


def test_replay_recorder_executes_joint_actions() -> None:
    created_envs = []

    def env_factory():
        env = make_action_env(seed=2, map_height=8, reward_shaping=False)
        original_reset = env.reset

        def reset(*args, **kwargs):
            observations, infos = original_reset(*args, **kwargs)
            env._game.set_storage([0, 0, 0, 0], [0, 0, 0, 0])
            env._game.turn = MAX_TURNS - 1
            return observations, infos

        env.reset = reset
        created_envs.append(env)
        return env

    class JointBot:
        def __init__(self) -> None:
            self.calls = 0

        def select_joint_action(self, observation, **kwargs):
            self.calls += 1
            return np.zeros(MAX_ROOTS, dtype=np.int64), None

        def select_action(self, observation, **kwargs):
            raise AssertionError("Scalar action path should not be used")

    main_bot = JointBot()
    opponent_bot = JointBot()

    frames = record_episode(env_factory, main_bot, "player_0", opponent_bot)

    assert len(created_envs) == 1
    assert len(frames) == 2
    assert main_bot.calls == 1
    assert opponent_bot.calls == 1