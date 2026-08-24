"""Generic Rainbow training entrypoint for two-agent PettingZoo environments.

Environment-specific details are injected via factories and optional adapter
paths, keeping this script game-agnostic.
"""
from __future__ import annotations

import argparse
import logging
import re
import shutil
from pathlib import Path
from typing import Optional

from project_paths import (
    ensure_dir,
    experiment_replay_store_dir,
    experiment_run_dir,
    experiment_snapshot_dir,
)
from rl.factory import load_symbol


def _setup_logging(run_dir: Path) -> Path:
    """Configure stdout + file logging for training runs."""
    log_path = run_dir / "training.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root.addHandler(console_handler)
    root.addHandler(file_handler)
    return log_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--env-factory",
        required=True,
        help="module:factory that returns a new PettingZoo ParallelEnv",
    )
    parser.add_argument("--total-steps", type=int, default=200_000)
    parser.add_argument("--n-envs", type=int, default=4)
    parser.add_argument("--learning-agent", default="player_0")
    parser.add_argument("--device", default="cpu")

    parser.add_argument("--run-dir", default="runs/rainbow")
    parser.add_argument(
        "--game",
        default="cellularena",
        help="Game namespace used for experiment folder layout.",
    )
    parser.add_argument(
        "--experiment-name",
        default="",
        help=(
            "If set, route run-dir/replay-dir/snapshot-dir under "
            "experiments/<game>/<experiment-name>/ unless explicitly overridden."
        ),
    )
    parser.add_argument("--eval-interval", type=int, default=10_000)
    parser.add_argument(
        "--resume-checkpoint",
        default=None,
        help="Optional path to a checkpoint to resume bot/optimizer state from.",
    )
    parser.add_argument(
        "--resume-global-step",
        type=int,
        default=None,
        help="Optional starting global step for logging/checkpoints when resuming.",
    )

    parser.add_argument("--buffer-size", type=int, default=100_000)
    parser.add_argument("--replay-min-size", type=int, default=2_000)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--collect-steps-per-env", type=int, default=1)
    parser.add_argument("--updates-per-iteration", type=int, default=1)
    parser.add_argument("--replay-dir", default="replay_store")
    parser.add_argument(
        "--reset-replay",
        action="store_true",
        help="If set, clear existing replay data in replay-dir before training.",
    )
    parser.add_argument(
        "--seed-replay-dir",
        default=None,
        help=(
            "Path to a pre-filled replay store to copy into the experiment replay dir "
            "before training starts. Only copied when the destination is empty (no "
            "existing replay.duckdb), so re-runs are safe. "
            "The source directory is never modified."
        ),
    )

    parser.add_argument("--lr", type=float, default=6.25e-5)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--target-update", type=int, default=500)
    parser.add_argument("--n-step", type=int, default=3)
    parser.add_argument("--n-quantiles", type=int, default=200)
    parser.add_argument("--kappa", type=float, default=1.0)
    parser.add_argument("--per-alpha", type=float, default=0.5)
    parser.add_argument("--per-beta-start", type=float, default=0.4)
    parser.add_argument("--per-beta-steps", type=int, default=100_000)
    parser.add_argument("--per-eps", type=float, default=1e-6)
    parser.add_argument("--hidden-dim", type=int, default=256)

    parser.add_argument("--self-play", action="store_true")
    parser.add_argument(
        "--progress-interval-steps",
        type=int,
        default=1000,
        help="Emit a progress log line every N collected environment steps.",
    )
    parser.add_argument("--snapshot-dir", default="league_pool")
    parser.add_argument("--snapshot-interval-steps", type=int, default=10_000)
    parser.add_argument("--max-historical", type=int, default=128)
    parser.add_argument("--mix-direct", type=float, default=0.50)
    parser.add_argument("--mix-historical", type=float, default=0.35)
    parser.add_argument("--mix-prioritized", type=float, default=0.15)

    parser.add_argument(
        "--main-exploiter-ckpt",
        action="append",
        default=[],
        help="Checkpoint path for a fixed main exploiter opponent (repeatable).",
    )
    parser.add_argument(
        "--league-exploiter-ckpt",
        action="append",
        default=[],
        help="Checkpoint path for a fixed league exploiter opponent (repeatable).",
    )

    return parser


def _seed_replay_store(src: Path, dst: Path) -> None:
    """Copy *src* replay store into *dst* if *dst* has no replay.duckdb yet.

    The source is never modified.  Re-running the same experiment is safe
    because the copy is skipped once the destination already has data.
    """
    dst_db = dst / "replay.duckdb"
    if dst_db.exists():
        print(f"[seed-replay] Destination already has data — skipping copy ({dst_db})")
        return
    if not src.is_dir():
        raise FileNotFoundError(f"--seed-replay-dir not found: {src}")
    print(f"[seed-replay] Copying seed store {src} → {dst} ...")
    ensure_dir(dst)
    for f in src.iterdir():
        if f.is_file():
            target = dst / f.name
            try:
                # Preserve metadata when possible on local filesystems.
                shutil.copy2(f, target)
            except PermissionError:
                # Azure Files may reject utime/chmod operations from copy2.
                shutil.copyfile(f, target)
    print(f"[seed-replay] Done — {sum(1 for _ in dst.iterdir())} files copied.")


def _infer_step_from_checkpoint(path: Path) -> Optional[int]:
    match = re.search(r"checkpoint_(\d+)\.pt$", path.name)
    if not match:
        return None
    return int(match.group(1))


def _resolve_layout_paths(args: argparse.Namespace) -> tuple[Path, Path, str]:
    run_dir = Path(args.run_dir)
    replay_dir = Path(args.replay_dir)
    snapshot_dir = str(args.snapshot_dir)

    if args.experiment_name:
        if args.run_dir == "runs/rainbow":
            run_dir = experiment_run_dir(args.game, args.experiment_name)
        if args.replay_dir == "replay_store":
            replay_dir = experiment_replay_store_dir(args.game, args.experiment_name)
        if args.snapshot_dir == "league_pool":
            snapshot_dir = str(experiment_snapshot_dir(args.game, args.experiment_name))

    ensure_dir(run_dir)
    ensure_dir(replay_dir)
    ensure_dir(Path(snapshot_dir))
    return run_dir, replay_dir, snapshot_dir


def main() -> None:
    args = _build_parser().parse_args()

    try:
        from rl.rainbow.bot import DQNBot
        from rl.logger import TrainingLogger
        from rl.rainbow.trainer import RainbowTrainer
        from rl.self_play import LeagueSelfPlayManager, OpponentRole
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing training dependencies. Install environment.yml (notably pytorch) "
            "before running train_rainbow.py."
        ) from exc

    env_factory = load_symbol(args.env_factory)
    if not callable(env_factory):
        raise TypeError("--env-factory must resolve to a callable.")

    probe_env = env_factory()
    try:
        obs_space = probe_env.observation_space(args.learning_agent)
        action_space = probe_env.action_space(args.learning_agent)
    finally:
        probe_env.close()

    bot = DQNBot(
        obs_space=obs_space,
        action_space=action_space,
        lr=args.lr,
        gamma=args.gamma,
        target_update=args.target_update,
        n_step=args.n_step,
        n_quantiles=args.n_quantiles,
        kappa=args.kappa,
        per_alpha=args.per_alpha,
        per_beta_start=args.per_beta_start,
        per_beta_steps=args.per_beta_steps,
        per_eps=args.per_eps,
        hidden_dim=args.hidden_dim,
        device=args.device,
    ).build()

    initial_global_step = 0
    if args.resume_checkpoint:
        resume_path = Path(args.resume_checkpoint)
        if not resume_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {resume_path}")
        bot.load(resume_path)

        if args.resume_global_step is not None:
            initial_global_step = max(0, int(args.resume_global_step))
        else:
            inferred_step = _infer_step_from_checkpoint(resume_path)
            if inferred_step is not None:
                initial_global_step = inferred_step

    opponent = DQNBot(
        obs_space=obs_space,
        action_space=action_space,
        lr=args.lr,
        gamma=args.gamma,
        target_update=args.target_update,
        n_step=args.n_step,
        n_quantiles=args.n_quantiles,
        kappa=args.kappa,
        per_alpha=args.per_alpha,
        per_beta_start=args.per_beta_start,
        per_beta_steps=args.per_beta_steps,
        per_eps=args.per_eps,
        hidden_dim=args.hidden_dim,
        device=args.device,
    ).build()
    opponent.eval_mode()

    run_dir, replay_dir, snapshot_dir = _resolve_layout_paths(args)
    log_path = _setup_logging(run_dir)
    logging.info("Training logs will be written to %s", log_path)

    if args.seed_replay_dir:
        _seed_replay_store(Path(args.seed_replay_dir), replay_dir)

    checkpoint_dir = run_dir / "checkpoints"
    ensure_dir(checkpoint_dir)

    self_play_manager = None
    if args.self_play:
        def _opponent_factory() -> DQNBot:
            return DQNBot(
                obs_space=obs_space,
                action_space=action_space,
                lr=args.lr,
                gamma=args.gamma,
                target_update=args.target_update,
                n_step=args.n_step,
                n_quantiles=args.n_quantiles,
                kappa=args.kappa,
                per_alpha=args.per_alpha,
                per_beta_start=args.per_beta_start,
                per_beta_steps=args.per_beta_steps,
                per_eps=args.per_eps,
                hidden_dim=args.hidden_dim,
                device=args.device,
            )

        self_play_manager = LeagueSelfPlayManager(
            main_bot=bot,
            opponent_factory=_opponent_factory,
            snapshot_dir=snapshot_dir,
            snapshot_interval_steps=args.snapshot_interval_steps,
            max_historical=args.max_historical,
            mix_direct=args.mix_direct,
            mix_historical=args.mix_historical,
            mix_prioritized=args.mix_prioritized,
        )

        for idx, ckpt in enumerate(args.main_exploiter_ckpt):
            self_play_manager.add_checkpoint_opponent(
                checkpoint_path=ckpt,
                opponent_id=f"main_exploiter_{idx}",
                role=OpponentRole.MAIN_EXPLOITER,
            )
        for idx, ckpt in enumerate(args.league_exploiter_ckpt):
            self_play_manager.add_checkpoint_opponent(
                checkpoint_path=ckpt,
                opponent_id=f"league_exploiter_{idx}",
                role=OpponentRole.LEAGUE_EXPLOITER,
            )

    trainer = RainbowTrainer(
        bot=bot,
        opponent=opponent,
        env_factory=env_factory,
        n_envs=args.n_envs,
        learning_agent=args.learning_agent,
        logger=TrainingLogger(log_dir=run_dir),
        checkpoint_dir=checkpoint_dir,
        eval_interval=args.eval_interval,
        self_play_manager=self_play_manager,
        buffer_size=args.buffer_size,
        replay_min_size=args.replay_min_size,
        batch_size=args.batch_size,
        collect_steps_per_env=args.collect_steps_per_env,
        updates_per_iteration=args.updates_per_iteration,
        replay_dir=replay_dir,
        reset_replay=args.reset_replay,
        initial_global_step=initial_global_step,
        progress_interval_steps=args.progress_interval_steps,
    )
    try:
        logging.info(
            "Starting training: game=%s experiment=%s total_steps=%d n_envs=%d",
            args.game,
            args.experiment_name or "<default>",
            args.total_steps,
            args.n_envs,
        )
        trainer.train(args.total_steps)
        logging.info("Training completed successfully.")
    except Exception:
        logging.exception("Training failed with an unhandled exception.")
        raise


if __name__ == "__main__":
    main()