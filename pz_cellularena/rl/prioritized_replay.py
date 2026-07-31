"""DuckDB/Parquet-backed prioritized replay buffer.

This module provides an offline-friendly replay buffer for PER:
- Transition payloads are stored in DuckDB and can be exported to Parquet.
- A lightweight SQLite index stores sampling priorities for PER.

The design keeps transition storage and priority indexing separate so replay data
can be archived cheaply while maintaining fast priority updates.
"""
from __future__ import annotations

from pathlib import Path
import pickle
import sqlite3

import numpy as np

try:
    import duckdb
except ImportError as exc:  # pragma: no cover - import-time guard
    raise ImportError(
        "duckdb is required for PrioritizedReplayBuffer. Install with 'pip install duckdb'."
    ) from exc

from rl.buffer import ReplayBuffer
from rl.experience import RolloutBatch, Transition


class PrioritizedReplayBuffer(ReplayBuffer):
    """Prioritized replay with DuckDB storage and SQLite priority index.

    Parameters
    ----------
    capacity:
        Maximum number of transitions retained in the ring buffer.
    min_size:
        Minimum number of transitions before :attr:`is_ready` is true.
    storage_dir:
        Directory containing the DuckDB file, SQLite index, and Parquet export.
    per_alpha:
        PER priority exponent alpha.
    per_eps:
        Small epsilon added to priorities to keep them positive.
    parquet_export_interval:
        Export to Parquet every N added transitions. Set to 0 to disable
        periodic export and call :meth:`export_to_parquet` manually.
    """

    def __init__(
        self,
        capacity: int,
        min_size: int = 1000,
        storage_dir: str | Path = "replay_store",
        per_alpha: float = 0.5,
        per_eps: float = 1e-6,
        parquet_export_interval: int = 10_000,
    ) -> None:
        super().__init__(capacity=capacity, min_size=min_size)

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.per_alpha = per_alpha
        self.per_eps = per_eps
        self.parquet_export_interval = parquet_export_interval

        self._duckdb_path = self.storage_dir / "replay.duckdb"
        self._sqlite_path = self.storage_dir / "per_index.sqlite"
        self._parquet_path = self.storage_dir / "replay_transitions.parquet"

        self._db = duckdb.connect(str(self._duckdb_path))
        # EnvRunner collects transitions from multiple worker threads; access to
        # this buffer is serialized by a lock, so cross-thread connection use is safe.
        self._index = sqlite3.connect(str(self._sqlite_path), check_same_thread=False)
        self._index.execute("PRAGMA journal_mode=WAL")
        self._index.execute("PRAGMA synchronous=NORMAL")

        self._setup_duckdb()
        self._setup_sqlite()

        self._raw_priorities = np.zeros(self.capacity, dtype=np.float64)
        self._scaled_priorities = np.zeros(self.capacity, dtype=np.float64)
        self._valid_slots = np.zeros(self.capacity, dtype=bool)
        self._slot_versions = np.zeros(self.capacity, dtype=np.int64)

        self._max_raw_priority = 1.0
        self._adds_since_export = 0
        self._next_version = 1
        self._closed = False

        self._restore_index_state()

    # ------------------------------------------------------------------
    # ReplayBuffer interface
    # ------------------------------------------------------------------

    def add(self, transition: Transition) -> None:
        slot = self._ptr
        version = self._next_version
        self._next_version += 1

        payload = pickle.dumps(transition, protocol=pickle.HIGHEST_PROTOCOL)
        self._db.execute(
            """
            INSERT INTO transitions (slot, version, payload, reward, done)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(slot) DO UPDATE
            SET version = excluded.version,
                payload = excluded.payload,
                reward = excluded.reward,
                done = excluded.done
            """,
            [slot, version, payload, float(transition.reward), bool(transition.done)],
        )

        raw_priority = self._max_raw_priority
        scaled_priority = self._to_scaled_priority(raw_priority)

        self._index.execute(
            """
            INSERT INTO priorities (slot, version, raw_priority, scaled_priority)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slot) DO UPDATE
            SET version = excluded.version,
                raw_priority = excluded.raw_priority,
                scaled_priority = excluded.scaled_priority
            """,
            (slot, version, raw_priority, scaled_priority),
        )

        self._raw_priorities[slot] = raw_priority
        self._scaled_priorities[slot] = scaled_priority
        self._valid_slots[slot] = True
        self._slot_versions[slot] = version

        self._ptr = (self._ptr + 1) % self.capacity
        self._size = min(self._size + 1, self.capacity)

        self._persist_meta()
        self._index.commit()

        self._adds_since_export += 1
        if (
            self.parquet_export_interval > 0
            and self._adds_since_export >= self.parquet_export_interval
        ):
            self.export_to_parquet()

    def sample(self, batch_size: int, beta: float = 0.4) -> RolloutBatch:
        if self._size == 0:
            raise ValueError("Cannot sample from an empty replay buffer.")
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0.")

        live_slots = np.flatnonzero(self._valid_slots)
        if live_slots.size == 0:
            raise RuntimeError("Priority index has no valid slots to sample from.")

        replace = live_slots.size < batch_size
        probs = self._scaled_priorities[live_slots]
        total_prob = probs.sum()
        if total_prob <= 0:
            probs = np.full_like(probs, 1.0 / probs.size)
        else:
            probs = probs / total_prob

        sampled_positions = np.random.choice(
            live_slots.size,
            size=batch_size,
            replace=replace,
            p=probs,
        )
        sampled_slots = live_slots[sampled_positions]
        sampled_probs = probs[sampled_positions]

        weights = np.power(live_slots.size * sampled_probs, -beta)
        weights = weights / max(weights.max(), 1e-12)

        transitions = self._load_transitions(sampled_slots)
        batch = self._pack_transitions(transitions)
        batch.indices = sampled_slots.astype(np.int64)
        batch.weights = weights.astype(np.float32)
        return batch

    def clear(self) -> None:
        super().clear()
        self._db.execute("DELETE FROM transitions")
        self._index.execute("DELETE FROM priorities")

        self._raw_priorities.fill(0.0)
        self._scaled_priorities.fill(0.0)
        self._valid_slots.fill(False)
        self._slot_versions.fill(0)
        self._max_raw_priority = 1.0
        self._next_version = 1
        self._adds_since_export = 0

        self._persist_meta()
        self._index.commit()

    # ------------------------------------------------------------------
    # PER helpers
    # ------------------------------------------------------------------

    def update_priorities(self, indices: np.ndarray, priorities: np.ndarray) -> None:
        """Update sampled priorities after a gradient step."""
        if indices.shape[0] != priorities.shape[0]:
            raise ValueError("indices and priorities must have the same length.")

        updates = []
        for slot_raw, priority_raw in zip(indices, priorities):
            slot = int(slot_raw)
            if slot < 0 or slot >= self.capacity or not self._valid_slots[slot]:
                continue

            raw_priority = max(float(priority_raw), self.per_eps)
            scaled_priority = self._to_scaled_priority(raw_priority)
            version = int(self._slot_versions[slot])

            self._raw_priorities[slot] = raw_priority
            self._scaled_priorities[slot] = scaled_priority
            self._max_raw_priority = max(self._max_raw_priority, raw_priority)

            updates.append((version, raw_priority, scaled_priority, slot))

        if not updates:
            return

        self._index.executemany(
            """
            UPDATE priorities
            SET version = ?, raw_priority = ?, scaled_priority = ?
            WHERE slot = ?
            """,
            updates,
        )
        self._index.commit()

    def beta_by_step(
        self,
        step: int,
        beta_start: float,
        beta_steps: int,
    ) -> float:
        """Anneal beta linearly from beta_start to 1.0."""
        if beta_steps <= 0:
            return 1.0
        frac = min(1.0, max(0.0, step / float(beta_steps)))
        return min(1.0, beta_start + frac * (1.0 - beta_start))

    def export_to_parquet(self) -> Path:
        """Export current transitions table to a Parquet snapshot."""
        parquet_sql_path = str(self._parquet_path).replace("'", "''")
        self._db.execute(
            f"""
            COPY (
                SELECT slot, version, reward, done, payload
                FROM transitions
                ORDER BY slot
            ) TO '{parquet_sql_path}'
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )
        self._adds_since_export = 0
        return self._parquet_path

    def close(self) -> None:
        """Flush and close backing databases."""
        if self._closed:
            return
        self._persist_meta()
        self._index.commit()
        self._db.close()
        self._index.close()
        self._closed = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _setup_duckdb(self) -> None:
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS transitions (
                slot INTEGER PRIMARY KEY,
                version BIGINT NOT NULL,
                payload BLOB NOT NULL,
                reward DOUBLE NOT NULL,
                done BOOLEAN NOT NULL
            )
            """
        )

    def _setup_sqlite(self) -> None:
        self._index.execute(
            """
            CREATE TABLE IF NOT EXISTS priorities (
                slot INTEGER PRIMARY KEY,
                version INTEGER NOT NULL,
                raw_priority REAL NOT NULL,
                scaled_priority REAL NOT NULL
            )
            """
        )
        self._index.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

    def _restore_index_state(self) -> None:
        rows = self._index.execute(
            "SELECT slot, version, raw_priority, scaled_priority FROM priorities"
        ).fetchall()

        for slot, version, raw_priority, scaled_priority in rows:
            slot_i = int(slot)
            if slot_i < 0 or slot_i >= self.capacity:
                continue
            self._raw_priorities[slot_i] = float(raw_priority)
            self._scaled_priorities[slot_i] = float(scaled_priority)
            self._valid_slots[slot_i] = True
            self._slot_versions[slot_i] = int(version)
            self._max_raw_priority = max(self._max_raw_priority, float(raw_priority))

        self._ptr = self._read_meta_int("ptr", 0)
        self._size = self._read_meta_int("size", int(self._valid_slots.sum()))
        self._next_version = self._read_meta_int("next_version", 1)
        self._adds_since_export = self._read_meta_int("adds_since_export", 0)

        self._ptr %= max(1, self.capacity)
        self._size = min(max(0, self._size), self.capacity)

    def _persist_meta(self) -> None:
        payload = {
            "ptr": str(self._ptr),
            "size": str(self._size),
            "next_version": str(self._next_version),
            "adds_since_export": str(self._adds_since_export),
            "capacity": str(self.capacity),
            "min_size": str(self.min_size),
            "per_alpha": str(self.per_alpha),
            "per_eps": str(self.per_eps),
        }
        self._index.executemany(
            """
            INSERT INTO meta (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            payload.items(),
        )

    def _read_meta_int(self, key: str, default: int) -> int:
        row = self._index.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return int(row[0])
        except (TypeError, ValueError):
            return default

    def _to_scaled_priority(self, raw_priority: float) -> float:
        return max(raw_priority, self.per_eps) ** self.per_alpha

    def _load_transitions(self, slots: np.ndarray) -> list[Transition]:
        slot_tokens = ",".join(str(int(s)) for s in slots)
        rows = self._db.execute(
            f"SELECT slot, payload FROM transitions WHERE slot IN ({slot_tokens})"
        ).fetchall()

        by_slot = {int(slot): pickle.loads(payload) for slot, payload in rows}
        missing = [int(slot) for slot in slots if int(slot) not in by_slot]
        if missing:
            raise RuntimeError(f"Missing transitions for slots: {missing}")

        return [by_slot[int(slot)] for slot in slots]

    def _pack_masks(self, masks: list) -> "np.ndarray | None":
        """Stack a list of per-transition masks into a batch array.

        Returns ``None`` when all masks are ``None`` (env has no masking).
        When only *some* masks are ``None`` (e.g. terminal next-state masks),
        those entries are filled with all-True so they never restrict the
        network.
        """
        if all(m is None for m in masks):
            return None
        # Replace None entries (terminal steps) with all-True masks.
        reference = next(m for m in masks if m is not None)
        filled = [
            np.ones_like(reference) if m is None else m
            for m in masks
        ]
        return np.stack(filled, axis=0)

    def _pack_transitions(self, transitions: list[Transition]) -> RolloutBatch:
        obs_keys = list(transitions[0].obs.keys())

        obs = {
            key: np.stack([t.obs[key] for t in transitions], axis=0)
            for key in obs_keys
        }
        next_obs = {
            key: np.stack([t.next_obs[key] for t in transitions], axis=0)
            for key in obs_keys
        }

        actions = np.stack([t.action for t in transitions], axis=0)
        rewards = np.asarray([t.reward for t in transitions], dtype=np.float32)
        dones = np.asarray([t.done for t in transitions], dtype=np.bool_)

        log_probs = np.asarray(
            [np.nan if t.log_prob is None else float(t.log_prob) for t in transitions],
            dtype=np.float32,
        )
        values = np.asarray(
            [np.nan if t.value is None else float(t.value) for t in transitions],
            dtype=np.float32,
        )

        return RolloutBatch(
            obs=obs,
            actions=actions,
            rewards=rewards,
            next_obs=next_obs,
            dones=dones,
            log_probs=log_probs,
            values=values,
            action_masks=self._pack_masks([t.action_mask for t in transitions]),
            next_action_masks=self._pack_masks([t.next_action_mask for t in transitions]),
        )

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        try:
            self.close()
        except Exception:
            pass
