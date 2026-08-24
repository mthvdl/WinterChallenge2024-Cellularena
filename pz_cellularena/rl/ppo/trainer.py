from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from rl.base_bot import RLBot
from rl.base_trainer import BaseTrainer
from rl.buffer import AbstractBuffer
from rl.env_runner import EnvRunner, EnvFactory, EpisodeEndCallback, OpponentSelector
from rl.logger import TrainingLogger
from rl.ppo.bot import PPOBot
from rl.ppo.buffer import PPORolloutBuffer


class PPOTrainer(BaseTrainer):
    """On-policy PPO trainer with multi-environment rollout collection.

    Parameters
    ----------
    bot:
        A :class:`~rl.ppo.bot.PPOBot` instance.
    opponent:
        The opponent bot used during training.
    env_factory:
        Zero-argument callable that returns a fresh
        :class:`~pettingzoo.ParallelEnv`.
    n_envs:
        Number of parallel environments.
    n_steps_per_rollout:
        Steps per environment per rollout.  Total rollout size =
        ``n_envs * n_steps_per_rollout``.
    learning_agent:
        Name of the PettingZoo agent being trained (default: ``"player_0"``).
    logger:
        :class:`~rl.logger.TrainingLogger` instance.
    eval_env_factory:
        Separate factory for evaluation environments.
    checkpoint_dir:
        Directory for periodic checkpoint files.
    eval_interval:
        Save checkpoint and evaluate every *eval_interval* training steps.
    self_play_manager:
        Optional league self-play manager.
    opponent_selector:
        Optional callback to select a per-episode opponent.
    on_episode_end:
        Optional callback invoked at the end of each episode.
    initial_global_step:
        Resume training from this step count.
    progress_interval_steps:
        How often to log progress to the console.
    """

    def __init__(
        self,
        bot: PPOBot,
        opponent: RLBot,
        env_factory: EnvFactory,
        n_envs: int = 4,
        n_steps_per_rollout: int = 128,
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
        super().__init__(
            bot=bot,
            opponent=opponent,
            env_factory=env_factory,
            n_envs=n_envs,
            learning_agent=learning_agent,
            logger=logger,
            eval_env_factory=eval_env_factory,
            checkpoint_dir=checkpoint_dir,
            eval_interval=eval_interval,
            self_play_manager=self_play_manager,
            opponent_selector=opponent_selector,
            on_episode_end=on_episode_end,
            initial_global_step=initial_global_step,
            progress_interval_steps=progress_interval_steps,
        )
        if not isinstance(bot, PPOBot):
            raise TypeError(f"PPOTrainer requires a PPOBot; got {type(bot).__name__}.")
        self.n_steps_per_rollout = int(n_steps_per_rollout)

    def create_buffer(self) -> PPORolloutBuffer:
        capacity = self.n_envs * self.n_steps_per_rollout
        return PPORolloutBuffer(capacity=capacity)

    def collect_experience(self, runner: EnvRunner, buffer: AbstractBuffer) -> int:
        """Fill *buffer* with one rollout and compute GAE advantages."""
        assert isinstance(buffer, PPORolloutBuffer)
        buffer.clear()

        self.bot.eval_mode()
        runner.collect(buffer, self.n_steps_per_rollout)
        self.bot.train_mode()

        bootstrap_values: Dict[int, float] = {}
        for env_idx, indices in buffer._per_env_order.items():
            if not indices:
                bootstrap_values[env_idx] = 0.0
                continue
            last_trans = buffer._storage[indices[-1]]
            if last_trans.done:
                bootstrap_values[env_idx] = 0.0
            else:
                bootstrap_values[env_idx] = self.bot.get_value(last_trans.next_obs)

        buffer.compute_advantages(
            gamma=self.bot.gamma,
            gae_lambda=self.bot.gae_lambda,
            bootstrap_values=bootstrap_values,
        )
        return len(buffer)

    def train_step(self, buffer: AbstractBuffer) -> Dict[str, float]:
        """Consume the full rollout buffer and perform PPO gradient updates."""
        assert isinstance(buffer, PPORolloutBuffer)
        batch = buffer.sample()
        return self.bot.update(batch)
