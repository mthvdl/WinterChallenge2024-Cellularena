"""Abstract training loop.

:class:`BaseTrainer` orchestrates the full RL training lifecycle:

1. Build bot and opponent.
2. Create :class:`~rl.env_runner.EnvRunner`.
3. Repeat until *total_steps* reached:
   a. Collect experience via :meth:`collect_experience`.
   b. Update the bot via :meth:`train_step`.
   c. Log metrics via :class:`~rl.logger.TrainingLogger`.
   d. Optionally evaluate and checkpoint.

This module is game-agnostic and works with any two-agent PettingZoo
:class:`~pettingzoo.ParallelEnv`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from pettingzoo import ParallelEnv
from rl.base_bot import RLBot
from rl.buffer import AbstractBuffer
from rl.env_runner import EnvRunner, EnvFactory, EpisodeEndCallback, OpponentSelector
from rl.experience import RolloutBatch
from rl.logger import TrainingLogger


log = logging.getLogger(__name__)


class BaseTrainer(ABC):
    """Abstract training loop for RL bots on PettingZoo parallel environments.

    Subclasses must implement :meth:`collect_experience` and
    :meth:`train_step` to define the algorithm-specific data flow.

    Parameters
    ----------
    bot:
        The learning bot (must have :meth:`~rl.base_bot.RLBot.build` called
        already, or the trainer will call it).
    opponent:
        The opponent bot used during training (fixed policy, self-play copy,
        etc.).
    env_factory:
        Zero-argument callable that returns a fresh
        :class:`~pettingzoo.ParallelEnv` instance.
    n_envs:
        Number of parallel environments for experience collection.
    learning_agent:
        Name of the PettingZoo agent that the bot controls (default:
        ``"player_0"``).
    logger:
        :class:`~rl.logger.TrainingLogger` instance.  If None, a default
        logger writing to ``runs/`` is created.
    eval_env_factory:
        Optional separate factory for evaluation environments.  Falls back to
        *env_factory* if not provided.
    checkpoint_dir:
        Directory to save periodic checkpoints.  No checkpoints are saved if
        None.
    eval_interval:
        Save a checkpoint and run evaluation every *eval_interval* training
        steps.  Disabled when None.
    """

    def __init__(
        self,
        bot: RLBot,
        opponent: RLBot,
        env_factory: EnvFactory,
        n_envs: int = 4,
        learning_agent: str = "player_0",
        logger: Optional[TrainingLogger] = None,
        eval_env_factory: Optional[EnvFactory] = None,
        checkpoint_dir: Optional[str | Path] = None,
        eval_interval: Optional[int] = 10_000,
        self_play_manager: Optional[Any] = None,
        opponent_selector: Optional[OpponentSelector] = None,
        on_episode_end: Optional[EpisodeEndCallback] = None,
        initial_global_step: int = 0,
        progress_interval_steps: int = 1000,
    ) -> None:
        self.bot = bot
        self.opponent = opponent
        self.env_factory = env_factory
        self.n_envs = n_envs
        self.learning_agent = learning_agent
        self.logger = logger or TrainingLogger()
        self.eval_env_factory = eval_env_factory or env_factory
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        self.eval_interval = eval_interval

        self.self_play_manager = self_play_manager
        if self.self_play_manager is not None:
            if opponent_selector is None and hasattr(self.self_play_manager, "select_opponent"):
                opponent_selector = self.self_play_manager.select_opponent
            if on_episode_end is None and hasattr(self.self_play_manager, "on_episode_end"):
                on_episode_end = self.self_play_manager.on_episode_end

        self.opponent_selector = opponent_selector
        self.on_episode_end = on_episode_end
        self.progress_interval_steps = max(1, int(progress_interval_steps))

        self._global_step: int = max(0, int(initial_global_step))
        if self._global_step > 0:
            self.logger.step(self._global_step)

        # Ensure networks are built
        if bot._network is None:
            bot.build()
        if opponent._network is None:
            opponent.build()

    # ------------------------------------------------------------------
    # Abstract interface – algorithm-specific
    # ------------------------------------------------------------------

    @abstractmethod
    def create_buffer(self) -> AbstractBuffer:
        """Instantiate the experience buffer appropriate for this algorithm.

        On-policy algorithms should return a
        :class:`~rl.buffer.RolloutBuffer`; off-policy algorithms a
        :class:`~rl.buffer.ReplayBuffer`.
        """

    @abstractmethod
    def collect_experience(
        self,
        runner: EnvRunner,
        buffer: AbstractBuffer,
    ) -> int:
        """Populate *buffer* with fresh experience using *runner*.

        Returns the number of new transitions added (used to advance
        :attr:`_global_step`).
        """

    @abstractmethod
    def train_step(self, buffer: AbstractBuffer) -> Dict[str, float]:
        """Consume *buffer* and perform one (or more) gradient update(s).

        Returns a metrics dict that will be passed to the logger.
        """

    # ------------------------------------------------------------------
    # Main training loop
    # ------------------------------------------------------------------

    def train(self, total_steps: int) -> None:
        """Run the training loop for *total_steps* environment steps.

        The loop:
        1. Creates an :class:`~rl.env_runner.EnvRunner`.
        2. Creates the experience buffer via :meth:`create_buffer`.
        3. Calls :meth:`collect_experience` → :meth:`train_step` repeatedly.
        4. Logs metrics and saves checkpoints at regular intervals.
        """
        buffer = self.create_buffer()

        with EnvRunner(
            env_factory=self.env_factory,
            bot=self.bot,
            opponent=self.opponent,
            n_envs=self.n_envs,
            learning_agent=self.learning_agent,
            opponent_selector=self.opponent_selector,
            on_episode_end=self.on_episode_end,
        ) as runner:
            self.bot.train_mode()
            next_progress_step = self._global_step + self.progress_interval_steps

            while self._global_step < total_steps:
                # --- collect ---
                new_steps = self.collect_experience(runner, buffer)
                self._global_step += new_steps
                self.logger.step(new_steps)

                if self._global_step >= next_progress_step:
                    pct = (100.0 * self._global_step / max(1, total_steps))
                    log.info(
                        "Progress %d/%d (%.2f%%) | collected=%d | replay=%d | ready=%s",
                        self._global_step,
                        total_steps,
                        pct,
                        new_steps,
                        len(buffer),
                        buffer.is_ready,
                    )
                    next_progress_step += self.progress_interval_steps

                # --- update ---
                if buffer.is_ready:
                    metrics = self.train_step(buffer)
                    self.logger.log_dict(metrics, prefix="train/")

                # --- eval & checkpoint ---
                if (
                    self.eval_interval
                    and self._global_step % self.eval_interval < new_steps
                ):
                    eval_metrics = self.evaluate()
                    self.logger.log_dict(eval_metrics, prefix="eval/")
                    if self.self_play_manager is not None and hasattr(
                        self.self_play_manager, "maybe_add_snapshot"
                    ):
                        snapshot_id = self.self_play_manager.maybe_add_snapshot(
                            step=self._global_step,
                            eval_win_rate=eval_metrics.get("win_rate"),
                        )
                        if snapshot_id:
                            self.logger.log_scalar(
                                "self_play/snapshot_added",
                                1.0,
                                step=self._global_step,
                            )
                    self._maybe_save_checkpoint()

        self.logger.close()

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        n_episodes: int = 20,
        deterministic: bool = True,
    ) -> Dict[str, float]:
        """Run *n_episodes* evaluation episodes and return aggregate metrics.

        Default metrics: ``win_rate``, ``avg_reward``, ``episode_length``.
        Subclasses may override to compute algorithm-specific statistics.

        Parameters
        ----------
        n_episodes:
            Number of complete episodes to play.
        deterministic:
            Pass ``deterministic=True`` to :meth:`~rl.base_bot.RLBot.select_action`
            so the greedy policy is evaluated.
        """
        self.bot.eval_mode()
        total_reward = 0.0
        wins = 0
        total_length = 0

        for _ in range(n_episodes):
            env: ParallelEnv = self.eval_env_factory()
            obs, _ = env.reset()
            # Derive the opponent agent name from the env's possible_agents
            opponent_agent = next(
                a for a in env.possible_agents if a != self.learning_agent
            )
            ep_reward = 0.0
            ep_length = 0
            done = False

            while not done:
                learn_action, _ = self.bot.select_action(
                    obs[self.learning_agent], deterministic=deterministic
                )
                opp_action, _ = self.opponent.select_action(
                    obs[opponent_agent], deterministic=True
                )
                obs, rewards, terminations, truncations, _ = env.step(
                    {self.learning_agent: learn_action, opponent_agent: opp_action}
                )
                ep_reward += rewards.get(self.learning_agent, 0.0)
                ep_length += 1
                done = terminations.get(self.learning_agent, False) or \
                       truncations.get(self.learning_agent, False)

            total_reward += ep_reward
            total_length += ep_length
            if ep_reward > 0:
                wins += 1

        self.bot.train_mode()
        return {
            "win_rate": wins / n_episodes,
            "avg_reward": total_reward / n_episodes,
            "avg_episode_length": total_length / n_episodes,
        }

    # ------------------------------------------------------------------
    # Checkpointing
    # ------------------------------------------------------------------

    def _maybe_save_checkpoint(self) -> None:
        """Save a checkpoint if *checkpoint_dir* is configured."""
        if self.checkpoint_dir is None:
            return
        path = self.checkpoint_dir / f"checkpoint_{self._global_step:010d}.pt"
        self.bot.save(path)
