"""Parallel environment runner for experience collection.

:class:`EnvRunner` manages a pool of independent PettingZoo
:class:`~pettingzoo.ParallelEnv` instances and collects
:class:`~rl.experience.Transition` objects by stepping all environments
in parallel.

Each environment is driven by two bots: the **learning bot** (the agent being
trained) and the **opponent bot** (fixed or self-play).  The runner only
stores transitions for the learning bot's perspective.

This runner is game-agnostic: it works with any PettingZoo
``ParallelEnv`` that has exactly two agents.

Threading model
---------------
Each environment runs in its own worker thread.  Because the game logic is
pure Python / NumPy, the GIL is the main concurrency bottleneck.  For heavier
workloads (e.g. rendering or complex feature extraction) consider switching
``_executor`` to a ``ProcessPoolExecutor`` by overriding :meth:`_make_executor`.
"""
from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

from pettingzoo import ParallelEnv
from rl.base_bot import RLBot
from rl.buffer import AbstractBuffer
from rl.experience import Transition


# A zero-argument factory that returns a freshly constructed PettingZoo ParallelEnv.
EnvFactory = Callable[[], ParallelEnv]

# Called at episode start for a given env index.
# Returns (opponent_bot, metadata_dict).
OpponentSelector = Callable[[int], Tuple[RLBot, Dict[str, Any]]]

# Called when an episode ends for a given env index.
EpisodeEndCallback = Callable[[Dict[str, Any]], None]


class EnvRunner:
    """Manages *n_envs* parallel PettingZoo :class:`~pettingzoo.ParallelEnv` instances.

    Parameters
    ----------
    env_factory:
        Callable that produces a new :class:`~pettingzoo.ParallelEnv`
        instance on each call.  Called once per worker at construction time.
    bot:
        The learning bot.  Its :meth:`~rl.base_bot.RLBot.select_action` is
        called for the *learning_agent* perspective in every environment.
    opponent:
        The opponent bot.  Its :meth:`~rl.base_bot.RLBot.select_action` is
        called for the other agent's perspective.  May be the same object as
        *bot* for self-play (access is protected by :attr:`_lock`).
    n_envs:
        Number of environments (and worker threads) to run in parallel.
    learning_agent:
        Name of the PettingZoo agent whose transitions are collected into the
        buffer (default: ``"player_0"``).
    """

    def __init__(
        self,
        env_factory: EnvFactory,
        bot: RLBot,
        opponent: RLBot,
        n_envs: int = 4,
        learning_agent: str = "player_0",
        opponent_selector: Optional[OpponentSelector] = None,
        on_episode_end: Optional[EpisodeEndCallback] = None,
    ) -> None:
        self.bot = bot
        self.opponent = opponent
        self.n_envs = n_envs
        self.learning_agent = learning_agent
        self.opponent_selector = opponent_selector
        self.on_episode_end = on_episode_end

        self._envs: List[ParallelEnv] = [env_factory() for _ in range(n_envs)]
        # Derive opponent agent name from the first env's possible_agents list;
        # this works for any PettingZoo env regardless of agent naming conventions.
        self._opponent_agent = next(
            a for a in self._envs[0].possible_agents if a != self.learning_agent
        )
        self._obs_cache: List[Optional[dict]] = [None] * n_envs
        self._active_opponents: List[RLBot] = [opponent] * n_envs
        self._active_opponent_meta: List[Dict[str, Any]] = [{} for _ in range(n_envs)]
        self._lock = threading.Lock()

        self._executor = self._make_executor()

        # Initialise all environments
        for i, env in enumerate(self._envs):
            obs, _ = env.reset()
            self._obs_cache[i] = obs
            self._assign_opponent(i)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self, buffer: AbstractBuffer, n_steps: int) -> None:
        """Step all environments for *n_steps* steps each and add transitions
        to *buffer*.

        Parameters
        ----------
        buffer:
            The buffer to populate (either a
            :class:`~rl.buffer.RolloutBuffer` or
            :class:`~rl.buffer.ReplayBuffer`).
        n_steps:
            Number of steps to collect **per environment**.  Total transitions
            added ≈ ``n_envs * n_steps``.
        """
        futures: List[Future] = [
            self._executor.submit(self._collect_worker, env_idx, buffer, n_steps)
            for env_idx in range(self.n_envs)
        ]
        # Re-raise any exception that occurred in a worker thread.
        for f in futures:
            f.result()

    def close(self) -> None:
        """Shut down the thread pool and close all environments."""
        self._executor.shutdown(wait=True)
        for env in self._envs:
            env.close()

    # ------------------------------------------------------------------
    # Extension hook
    # ------------------------------------------------------------------

    def _make_executor(self) -> ThreadPoolExecutor:
        """Create the executor used for parallel stepping.

        Override to return a ``ProcessPoolExecutor`` or a custom executor.
        """
        return ThreadPoolExecutor(max_workers=self.n_envs)

    def _assign_opponent(self, env_idx: int) -> None:
        """Assign the opponent for the next episode in environment *env_idx*."""
        if self.opponent_selector is None:
            self._active_opponents[env_idx] = self.opponent
            self._active_opponent_meta[env_idx] = {"kind": "fixed"}
            return

        opponent, meta = self.opponent_selector(env_idx)
        self._active_opponents[env_idx] = opponent
        self._active_opponent_meta[env_idx] = dict(meta)

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------

    def _collect_worker(
        self,
        env_idx: int,
        buffer: AbstractBuffer,
        n_steps: int,
    ) -> None:
        """Run one environment for *n_steps* and push transitions to *buffer*.

        Runs inside a worker thread; all shared state (bot, buffer) is
        protected by :attr:`_lock` only where necessary.
        """
        env = self._envs[env_idx]
        obs = self._obs_cache[env_idx]
        _supports_mask = hasattr(env, "action_mask")

        for _ in range(n_steps):
            # Collect per-agent action masks if the env supports it.
            if _supports_mask:
                learn_mask = env.action_mask(self.learning_agent)
                opp_mask = env.action_mask(self._opponent_agent)
            else:
                learn_mask = None
                opp_mask = None

            # Select actions for both players (lock protects shared bot state)
            with self._lock:
                opponent = self._active_opponents[env_idx]
                learn_action, learn_extras = self.bot.select_action(
                    obs[self.learning_agent], deterministic=False,
                    action_mask=learn_mask,
                )
                opp_action, _ = opponent.select_action(
                    obs[self._opponent_agent], deterministic=True,
                    action_mask=opp_mask,
                )

            actions = {
                self.learning_agent: learn_action,
                self._opponent_agent: opp_action,
            }

            next_obs, rewards, terminations, truncations, _ = env.step(actions)

            done = terminations.get(self.learning_agent, False) or \
                   truncations.get(self.learning_agent, False)

            # Capture the next-state mask before a potential reset so we can
            # use it for target action selection in Double DQN.
            if _supports_mask and not done:
                next_learn_mask = env.action_mask(self.learning_agent)
            else:
                next_learn_mask = None

            transition = Transition(
                obs=obs[self.learning_agent],
                action=learn_action,
                reward=rewards.get(self.learning_agent, 0.0),
                next_obs=next_obs[self.learning_agent],
                done=done,
                log_prob=learn_extras.get("log_prob"),
                value=learn_extras.get("value"),
                action_mask=learn_mask,
                next_action_mask=next_learn_mask,
                info={
                    "env_idx": env_idx,
                    "opponent_meta": dict(self._active_opponent_meta[env_idx]),
                },
            )

            with self._lock:
                buffer.add(transition)

            if done:
                if self.on_episode_end is not None:
                    summary = {
                        "env_idx": env_idx,
                        "reward": rewards.get(self.learning_agent, 0.0),
                        "done": done,
                        "opponent_meta": dict(self._active_opponent_meta[env_idx]),
                    }
                    self.on_episode_end(summary)
                reset_obs, _ = env.reset()
                obs = reset_obs
                with self._lock:
                    self._assign_opponent(env_idx)
            else:
                obs = next_obs

        self._obs_cache[env_idx] = obs

    def __enter__(self) -> "EnvRunner":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
