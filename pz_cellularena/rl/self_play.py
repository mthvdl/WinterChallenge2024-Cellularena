"""Game-agnostic league self-play management.

This module implements a dynamic opponent pool that mitigates strategy
cycling in naive self-play. It is designed to work with any two-agent
PettingZoo environment because it depends only on RLBot interfaces and
episode outcomes from the learning agent perspective.

Key features
------------
- Snapshot pool of historical opponents.
- Mixed opponent sampling:
  - direct self-play
  - historical opponents
  - prioritized hard opponents
- PFSP-style weighting based on current win-rate against each opponent.
- Optional support for explicit exploiter roles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path
import random
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from rl.base_bot import RLBot


class OpponentRole(str, Enum):
    """Logical role of an opponent in the league."""

    MAIN = "main"
    HISTORICAL = "historical"
    MAIN_EXPLOITER = "main_exploiter"
    LEAGUE_EXPLOITER = "league_exploiter"


class MatchBucket(str, Enum):
    """High-level bucket used for mixed opponent selection."""

    DIRECT_SELF_PLAY = "direct_self_play"
    HISTORICAL = "historical"
    PRIORITIZED = "prioritized"


@dataclass
class OpponentStats:
    """Running head-to-head stats from the main agent perspective."""

    episodes: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    ema_win_rate: float = 0.5

    def update(self, result: int, ema_alpha: float) -> None:
        """Update stats with one episode result.

        Parameters
        ----------
        result:
            +1 if main agent won, 0 if draw, -1 if main agent lost.
        ema_alpha:
            Exponential moving average factor in [0, 1].
        """
        self.episodes += 1
        if result > 0:
            self.wins += 1
            target = 1.0
        elif result < 0:
            self.losses += 1
            target = 0.0
        else:
            self.draws += 1
            target = 0.5

        alpha = max(0.0, min(1.0, ema_alpha))
        self.ema_win_rate = (1.0 - alpha) * self.ema_win_rate + alpha * target

    @property
    def empirical_win_rate(self) -> float:
        """Empirical win-rate from the main agent perspective."""
        if self.episodes == 0:
            return 0.5
        return (self.wins + 0.5 * self.draws) / float(self.episodes)


@dataclass
class OpponentEntry:
    """One opponent registered in the league."""

    opponent_id: str
    role: OpponentRole
    bot: RLBot
    source: str
    created_step: int = 0
    checkpoint_path: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    stats: OpponentStats = field(default_factory=OpponentStats)


class LeagueSelfPlayManager:
    """Dynamic opponent-pool manager with PFSP-style prioritization.

    Parameters
    ----------
    main_bot:
        The currently training bot (the "main agent").
    opponent_factory:
        Zero-argument callable that returns a bot instance compatible with
        *main_bot* checkpoints. It is used to materialize historical snapshots.
    snapshot_dir:
        Directory where historical checkpoints are saved.
    snapshot_interval_steps:
        Minimum training-step gap between automatic snapshots.
    max_historical:
        Maximum number of historical snapshots kept active in the pool.
    mix_direct, mix_historical, mix_prioritized:
        Relative weights of the three sampling buckets. They are normalized.
    pfsp_sigma:
        Width of the bell-shaped PFSP term centered at win-rate 0.5.
    pfsp_easy_cutoff:
        Opponents with win-rate >= cutoff receive zero PFSP weight.
    pfsp_under50_bonus:
        Extra weight for opponents currently beating the main agent.
    pfsp_floor:
        Minimum non-zero weight used for numerical stability.
    hard_top_k:
        Prioritized bucket candidates are restricted to the K hardest opponents.
    ema_alpha:
        EMA factor used to smooth win-rate estimates.
    rng_seed:
        Optional deterministic seed.
    """

    MAIN_OPPONENT_ID = "main_live"

    def __init__(
        self,
        main_bot: RLBot,
        opponent_factory: Callable[[], RLBot],
        snapshot_dir: str | Path = "league_pool",
        snapshot_interval_steps: int = 10_000,
        max_historical: int = 128,
        mix_direct: float = 0.50,
        mix_historical: float = 0.35,
        mix_prioritized: float = 0.15,
        pfsp_sigma: float = 0.18,
        pfsp_easy_cutoff: float = 0.95,
        pfsp_under50_bonus: float = 0.5,
        pfsp_floor: float = 1e-6,
        hard_top_k: int = 8,
        ema_alpha: float = 0.1,
        rng_seed: Optional[int] = None,
    ) -> None:
        self.main_bot = main_bot
        self.opponent_factory = opponent_factory
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        self.snapshot_interval_steps = max(1, int(snapshot_interval_steps))
        self.max_historical = max(1, int(max_historical))
        self.hard_top_k = max(1, int(hard_top_k))
        self.ema_alpha = max(0.0, min(1.0, float(ema_alpha)))

        self.pfsp_sigma = max(1e-6, float(pfsp_sigma))
        self.pfsp_easy_cutoff = max(0.0, min(1.0, float(pfsp_easy_cutoff)))
        self.pfsp_under50_bonus = max(0.0, float(pfsp_under50_bonus))
        self.pfsp_floor = max(0.0, float(pfsp_floor))

        mix_total = max(1e-12, mix_direct + mix_historical + mix_prioritized)
        self.mix_direct = mix_direct / mix_total
        self.mix_historical = mix_historical / mix_total
        self.mix_prioritized = mix_prioritized / mix_total

        self._rng = random.Random(rng_seed)
        self._lock = threading.Lock()

        self._entries: Dict[str, OpponentEntry] = {
            self.MAIN_OPPONENT_ID: OpponentEntry(
                opponent_id=self.MAIN_OPPONENT_ID,
                role=OpponentRole.MAIN,
                bot=self.main_bot,
                source="live",
            )
        }
        self._historical_ids: List[str] = []
        self._episode_assignment: Dict[int, str] = {}
        self._last_snapshot_step: int = -self.snapshot_interval_steps
        self._best_eval_win_rate: float = float("-inf")

    # ------------------------------------------------------------------
    # Runner hooks
    # ------------------------------------------------------------------

    def select_opponent(self, env_idx: int) -> Tuple[RLBot, Dict[str, Any]]:
        """Select and return the opponent for one environment episode."""
        with self._lock:
            bucket = self._sample_bucket()
            opponent_id = self._sample_opponent_id(bucket)

            entry = self._entries[opponent_id]
            self._episode_assignment[env_idx] = opponent_id

            meta = {
                "opponent_id": entry.opponent_id,
                "role": entry.role.value,
                "bucket": bucket.value,
                "source": entry.source,
            }
            return entry.bot, meta

    def on_episode_end(self, summary: Dict[str, Any]) -> None:
        """Update head-to-head stats after one finished episode.

        Expected fields in *summary*:
        - env_idx: int
        - reward: float (from main agent perspective)
        - opponent_meta: dict with optional opponent_id
        """
        env_idx = int(summary.get("env_idx", -1))
        reward = float(summary.get("reward", 0.0))
        opponent_meta = summary.get("opponent_meta") or {}

        with self._lock:
            opponent_id = opponent_meta.get("opponent_id")
            if opponent_id is None:
                opponent_id = self._episode_assignment.get(env_idx)
            if opponent_id is None or opponent_id not in self._entries:
                return

            if reward > 0.0:
                result = 1
            elif reward < 0.0:
                result = -1
            else:
                result = 0

            self._entries[opponent_id].stats.update(result=result, ema_alpha=self.ema_alpha)

    # ------------------------------------------------------------------
    # Snapshot management
    # ------------------------------------------------------------------

    def maybe_add_snapshot(
        self,
        step: int,
        eval_win_rate: Optional[float] = None,
        min_eval_improvement: float = 0.0,
        force: bool = False,
    ) -> Optional[str]:
        """Create a historical snapshot if scheduling/quality criteria pass.

        Returns opponent_id when a snapshot is added, else None.
        """
        with self._lock:
            if not force and (step - self._last_snapshot_step) < self.snapshot_interval_steps:
                return None

            if eval_win_rate is not None:
                threshold = self._best_eval_win_rate + float(min_eval_improvement)
                if not force and eval_win_rate < threshold:
                    return None
                self._best_eval_win_rate = max(self._best_eval_win_rate, eval_win_rate)

            opponent_id = self._add_main_snapshot_unlocked(step=step)
            self._last_snapshot_step = int(step)
            self._trim_historical_unlocked()
            return opponent_id

    def add_external_opponent(
        self,
        opponent_id: str,
        bot: RLBot,
        role: OpponentRole,
        source: str = "external",
        created_step: int = 0,
        tags: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a non-main opponent (e.g. exploiter) into the league."""
        if role == OpponentRole.MAIN:
            raise ValueError("External opponents cannot use role MAIN.")

        with self._lock:
            if opponent_id in self._entries:
                raise ValueError(f"Opponent '{opponent_id}' already exists.")
            self._entries[opponent_id] = OpponentEntry(
                opponent_id=opponent_id,
                role=role,
                bot=bot,
                source=source,
                created_step=int(created_step),
                tags=dict(tags or {}),
            )
            if role == OpponentRole.HISTORICAL:
                self._historical_ids.append(opponent_id)
                self._trim_historical_unlocked()

    def add_checkpoint_opponent(
        self,
        checkpoint_path: str | Path,
        opponent_id: str,
        role: OpponentRole = OpponentRole.HISTORICAL,
        created_step: int = 0,
        tags: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Load a bot checkpoint and register it as an opponent."""
        path = Path(checkpoint_path)
        if not path.exists():
            raise FileNotFoundError(path)

        bot = self._load_bot_from_checkpoint(path)
        with self._lock:
            if opponent_id in self._entries:
                raise ValueError(f"Opponent '{opponent_id}' already exists.")
            self._entries[opponent_id] = OpponentEntry(
                opponent_id=opponent_id,
                role=role,
                bot=bot,
                source="checkpoint",
                created_step=int(created_step),
                checkpoint_path=str(path),
                tags=dict(tags or {}),
            )
            if role == OpponentRole.HISTORICAL:
                self._historical_ids.append(opponent_id)
                self._trim_historical_unlocked()

    # ------------------------------------------------------------------
    # Monitoring helpers
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return aggregate pool information and per-opponent stats."""
        with self._lock:
            opponents: Dict[str, Any] = {}
            for opponent_id, entry in self._entries.items():
                stats = entry.stats
                opponents[opponent_id] = {
                    "role": entry.role.value,
                    "source": entry.source,
                    "created_step": entry.created_step,
                    "checkpoint_path": entry.checkpoint_path,
                    "episodes": stats.episodes,
                    "wins": stats.wins,
                    "losses": stats.losses,
                    "draws": stats.draws,
                    "win_rate": stats.empirical_win_rate,
                    "ema_win_rate": stats.ema_win_rate,
                }

            return {
                "mix": {
                    "direct": self.mix_direct,
                    "historical": self.mix_historical,
                    "prioritized": self.mix_prioritized,
                },
                "n_opponents": len(self._entries),
                "n_historical": len(self._historical_ids),
                "best_eval_win_rate": self._best_eval_win_rate,
                "opponents": opponents,
            }

    # ------------------------------------------------------------------
    # Internal helpers (lock required)
    # ------------------------------------------------------------------

    def _sample_bucket(self) -> MatchBucket:
        has_non_main = any(oid != self.MAIN_OPPONENT_ID for oid in self._entries)
        has_history = len(self._historical_ids) > 0

        if not has_non_main:
            return MatchBucket.DIRECT_SELF_PLAY

        roll = self._rng.random()
        if roll < self.mix_direct:
            return MatchBucket.DIRECT_SELF_PLAY
        if roll < (self.mix_direct + self.mix_historical) and has_history:
            return MatchBucket.HISTORICAL
        return MatchBucket.PRIORITIZED

    def _sample_opponent_id(self, bucket: MatchBucket) -> str:
        if bucket == MatchBucket.DIRECT_SELF_PLAY:
            return self.MAIN_OPPONENT_ID

        if bucket == MatchBucket.HISTORICAL:
            if not self._historical_ids:
                return self.MAIN_OPPONENT_ID
            return self._rng.choice(self._historical_ids)

        # Prioritized bucket
        candidates = [
            oid for oid in self._entries
            if oid != self.MAIN_OPPONENT_ID
        ]
        if not candidates:
            return self.MAIN_OPPONENT_ID

        # Keep only hardest K according to EMA win-rate (lowest = hardest).
        candidates.sort(key=lambda oid: self._entries[oid].stats.ema_win_rate)
        candidates = candidates[: self.hard_top_k]

        weights = [self._pfsp_weight(self._entries[oid].stats.ema_win_rate) for oid in candidates]
        if sum(weights) <= 0.0:
            return self._rng.choice(candidates)
        return self._weighted_choice(candidates, weights)

    def _pfsp_weight(self, win_rate: float) -> float:
        """PFSP-style weight from main-vs-opponent win-rate.

        The weight combines:
        - a bell-shaped term centered at 0.5 (most instructive close games),
        - an extra bonus when win-rate < 0.5 (main is currently exploited),
        - hard cutoff for very easy opponents.
        """
        v = max(0.0, min(1.0, float(win_rate)))
        if v >= self.pfsp_easy_cutoff:
            return 0.0

        z = (v - 0.5) / self.pfsp_sigma
        close_game_term = math.exp(-0.5 * z * z)
        under50_term = max(0.0, 0.5 - v) * 2.0

        return max(self.pfsp_floor, close_game_term + self.pfsp_under50_bonus * under50_term)

    def _weighted_choice(self, values: List[str], weights: List[float]) -> str:
        total = float(sum(weights))
        if total <= 0.0:
            return self._rng.choice(values)

        threshold = self._rng.random() * total
        acc = 0.0
        for value, weight in zip(values, weights):
            acc += weight
            if acc >= threshold:
                return value
        return values[-1]

    def _add_main_snapshot_unlocked(self, step: int) -> str:
        opponent_id = f"hist_{int(step):010d}"
        path = self.snapshot_dir / f"{opponent_id}.pt"

        self.main_bot.save(path)
        bot = self._load_bot_from_checkpoint(path)

        self._entries[opponent_id] = OpponentEntry(
            opponent_id=opponent_id,
            role=OpponentRole.HISTORICAL,
            bot=bot,
            source="snapshot",
            created_step=int(step),
            checkpoint_path=str(path),
            tags={"from": "main"},
        )
        self._historical_ids.append(opponent_id)
        return opponent_id

    def _trim_historical_unlocked(self) -> None:
        if len(self._historical_ids) <= self.max_historical:
            return

        active_assignments = set(self._episode_assignment.values())
        kept: List[str] = []
        dropped: List[str] = []

        # Keep newest snapshots and avoid dropping those currently assigned.
        for opponent_id in reversed(self._historical_ids):
            if len(kept) < self.max_historical or opponent_id in active_assignments:
                kept.append(opponent_id)
            else:
                dropped.append(opponent_id)

        self._historical_ids = list(reversed(kept))
        for opponent_id in dropped:
            self._entries.pop(opponent_id, None)

    def _load_bot_from_checkpoint(self, checkpoint_path: Path) -> RLBot:
        bot = self.opponent_factory()
        if bot._network is None:
            bot.build()
        bot.load(checkpoint_path)
        bot.eval_mode()
        return bot
