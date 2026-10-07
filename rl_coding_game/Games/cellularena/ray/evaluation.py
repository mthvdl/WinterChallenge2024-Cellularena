"""Asynchronous RLlib evaluation against the previous checkpoint, with optional TV replay."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from Core.league import latest_checkpoint_before
from Core.ray_policies import load_policy_from_checkpoint
from Games.cellularena.engine.tools.game_recorder import write_viewer_replay

EVAL_OPPONENT_POLICY_ID = "eval_previous"
_REPLAY_TAG_ATTR = "_cellularena_eval_replay_tag"


def evaluation_policy_mapping(main_policy_id: str) -> Callable[..., str]:
    """Player 0 plays the current policy; player 1 plays the previous checkpoint."""

    def mapping(agent_id: str, *args: Any, **kwargs: Any) -> str:
        del args, kwargs
        return main_policy_id if agent_id.endswith("0") else EVAL_OPPONENT_POLICY_ID

    return mapping


def save_evaluation_replay(*, env_runner: Any, env: Any, env_index: int, **kwargs: Any) -> None:
    """RLlib `on_episode_end` hook: save the first evaluation game of each round as TV replay."""
    tag = getattr(env_runner, _REPLAY_TAG_ATTR, None)
    if tag is None or env_runner.worker_index > 1:
        return
    setattr(env_runner, _REPLAY_TAG_ATTR, None)
    frames = env.envs[env_index].unwrapped.par_env.completed_replay_frames
    if frames:
        write_viewer_replay(
            frames,
            Path(tag["output_dir"]),
            f"iteration_{tag['step']}",
            tag["experiment_name"],
            tag["step"],
            tag["opponent_name"],
        )


def configure_evaluation(config: Any, run: dict[str, Any], env_settings: dict[str, Any], main_policy_id: str) -> Any:
    """Run RLlib evaluation in parallel with training, against `EVAL_OPPONENT_POLICY_ID`."""
    if not run["evaluation_interval"]:
        return config
    if run["evaluation_num_env_runners"] < 1:
        raise ValueError("Asynchronous evaluation requires evaluation_num_env_runners >= 1.")
    evaluation_config: dict[str, Any] = {
        "explore": run["evaluation_explore"],
        "policy_mapping_fn": evaluation_policy_mapping(main_policy_id),
    }
    if run["save_evaluation_play"]:
        evaluation_config["env_config"] = {**env_settings, "record_replay": True}
        config.callbacks(on_episode_end=save_evaluation_replay)
    return config.evaluation(
        evaluation_interval=run["evaluation_interval"],
        evaluation_num_env_runners=run["evaluation_num_env_runners"],
        evaluation_duration=run["evaluation_duration"],
        evaluation_duration_unit=run["evaluation_duration_unit"],
        evaluation_parallel_to_training=True,
        evaluation_config=evaluation_config,
    )


def prepare_evaluation(
    algorithm: Any,
    checkpoints_dir: Path,
    step: int,
    experiment_name: str,
    replays_dir: Path | None,
    fallback_checkpoint: Path | None = None,
) -> str:
    """Load the checkpoint preceding `step` as the evaluation opponent before `train()` runs it."""
    previous_checkpoint = latest_checkpoint_before(checkpoints_dir, step, fallback_checkpoint)
    opponent_name = "initial_network"
    if previous_checkpoint is not None:
        load_policy_from_checkpoint(
            algorithm, str(previous_checkpoint), target_policy_id=EVAL_OPPONENT_POLICY_ID
        )
        opponent_name = previous_checkpoint.name
    if replays_dir is not None:
        tag = {
            "step": step,
            "experiment_name": experiment_name,
            "opponent_name": opponent_name,
            "output_dir": str(replays_dir),
        }
        algorithm.eval_env_runner_group.foreach_env_runner(
            lambda runner: setattr(runner, _REPLAY_TAG_ATTR, tag)
        )
    return opponent_name
