# Moved to rl.rainbow.trainer.  Re-exported here for backward compatibility.
from rl.rainbow.trainer import RainbowTrainer as RainbowTrainer  # noqa: F401

__all__ = ["RainbowTrainer"]



class RainbowTrainer(BaseTrainer):
    """Off-policy Rainbow trainer with PER and n-step replay."""

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
        self_play_manager: Optional[object] = None,
        opponent_selector: Optional[OpponentSelector] = None,
        on_episode_end: Optional[EpisodeEndCallback] = None,
        buffer_size: int = 100_000,
        replay_min_size: int = 2_000,
        batch_size: int = 32,
        collect_steps_per_env: int = 1,
        updates_per_iteration: int = 1,
        replay_dir: str | Path = "replay_store",
        reset_replay: bool = False,
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
        self.buffer_size = int(buffer_size)
        self.replay_min_size = int(replay_min_size)
        self.batch_size = int(batch_size)
        self.collect_steps_per_env = int(collect_steps_per_env)
        self.updates_per_iteration = int(updates_per_iteration)
        self.replay_dir = Path(replay_dir)
        self.reset_replay = bool(reset_replay)

        self._replay: Optional[PrioritizedReplayBuffer] = None
        self._collector_buffer: Optional[NStepBufferWrapper] = None

    def create_buffer(self) -> AbstractBuffer:
        if not hasattr(self.bot, "per_alpha") or not hasattr(self.bot, "per_eps"):
            raise TypeError("RainbowTrainer expects a DQN/Rainbow-style bot with PER hyper-parameters.")

        self._replay = PrioritizedReplayBuffer(
            capacity=self.buffer_size,
            min_size=self.replay_min_size,
            storage_dir=self.replay_dir,
            per_alpha=float(getattr(self.bot, "per_alpha")),
            per_eps=float(getattr(self.bot, "per_eps")),
        )
        if self.reset_replay:
            self._replay.clear()

        n_step = int(getattr(self.bot, "n_step", 1))
        gamma = float(getattr(self.bot, "gamma", 0.99))
        self._collector_buffer = NStepBufferWrapper(self._replay, n_step=n_step, gamma=gamma)
        return self._collector_buffer

    def collect_experience(self, runner: EnvRunner, buffer: AbstractBuffer) -> int:
        runner.collect(buffer=buffer, n_steps=self.collect_steps_per_env)
        return self.n_envs * self.collect_steps_per_env

    def train_step(self, buffer: AbstractBuffer) -> Dict[str, float]:
        del buffer
        if self._replay is None:
            raise RuntimeError("Replay buffer is not initialized.")
        if not self._replay.is_ready:
            return {}

        metric_list = []
        for _ in range(self.updates_per_iteration):
            beta = self._replay.beta_by_step(
                step=int(getattr(self.bot, "_steps_done", 0)),
                beta_start=float(getattr(self.bot, "per_beta_start", 0.4)),
                beta_steps=int(getattr(self.bot, "per_beta_steps", 100_000)),
            )
            batch = self._replay.sample(batch_size=self.batch_size, beta=beta)
            metrics = self.bot.update(batch)

            indices = getattr(self.bot, "_last_priority_update_indices", None)
            priorities = getattr(self.bot, "_last_priority_update_values", None)
            if indices is not None and priorities is not None:
                self._replay.update_priorities(indices=indices, priorities=priorities)
                setattr(self.bot, "_last_priority_update_indices", None)
                setattr(self.bot, "_last_priority_update_values", None)

            metric_list.append(metrics)

        out: Dict[str, float] = {}
        if not metric_list:
            return out

        keys = metric_list[0].keys()
        for key in keys:
            out[key] = float(np.mean([m[key] for m in metric_list]))
        return out

    def train(self, total_steps: int) -> None:
        try:
            super().train(total_steps)
        finally:
            if self._replay is not None:
                self._replay.close()