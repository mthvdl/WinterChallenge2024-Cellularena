"""DQN/SAC variants that stop collecting games after filling the replay buffer.

Both algorithms use DQN's new-stack training step in RLlib. Only the offline
branch is implemented here; normal collection delegates to RLlib unchanged.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from ray.rllib.algorithms.dqn.dqn import DQN, calculate_rr_weights
from ray.rllib.algorithms.sac.sac import SAC
from ray.rllib.utils.metrics import (
    ALL_MODULES,
    ENV_RUNNER_RESULTS,
    LEARNER_RESULTS,
    LEARNER_UPDATE_TIMER,
    NUM_AGENT_STEPS_SAMPLED_LIFETIME,
    NUM_ENV_STEPS_SAMPLED_LIFETIME,
    REPLAY_BUFFER_RESULTS,
    REPLAY_BUFFER_SAMPLE_TIMER,
    REPLAY_BUFFER_UPDATE_PRIOS_TIMER,
    TD_ERROR_KEY,
    TIMERS,
)
from ray.rllib.utils.numpy import convert_to_numpy
from ray.rllib.utils.replay_buffers.utils import update_priorities_in_episode_replay_buffer


class _FixedReplayMixin:
    """Switch permanently to replay-only learning when the buffer is full.

    Episodic eviction may leave fewer stored transitions than `capacity` even
    after the buffer has filled. Use lifetime additions to detect first fill.
    """

    def _training_step_new_api_stack(self):
        buffer = self.local_replay_buffer
        if not getattr(self, "_fixed_replay_full", False):
            if buffer.get_added_timesteps() < buffer.capacity:
                return super()._training_step_new_api_stack()
            self._fixed_replay_full = True
            print(
                f"Replay buffer filled after {buffer.get_added_timesteps()} steps "
                f"({len(buffer)} stored / {buffer.capacity} capacity); "
                "stopping environment sampling."
            )

        # RLlib's DQN/SAC training step always calls EnvRunner.sample(). Run only
        # its replay/learner/prioritization half after the buffer is full.
        _, update_count = calculate_rr_weights(self.config)
        for _ in range(update_count):
            with self.metrics.log_time((TIMERS, REPLAY_BUFFER_SAMPLE_TIMER)):
                episodes = buffer.sample(
                    num_items=self.config.total_train_batch_size,
                    n_step=self.config.n_step,
                    batch_length_T=(
                        self._module_is_stateful
                        * self.config.model_config.get("max_seq_len", 0)
                    ),
                    lookback=int(self._module_is_stateful),
                    min_batch_length_T=getattr(self.config, "burn_in_len", 0),
                    gamma=self.config.gamma,
                    beta=self.config.replay_buffer_config.get("beta"),
                    sample_episodes=True,
                )
                self.metrics.aggregate([buffer.get_metrics()], key=REPLAY_BUFFER_RESULTS)

            with self.metrics.log_time((TIMERS, LEARNER_UPDATE_TIMER)):
                learner_results = self.learner_group.update(
                    episodes=episodes,
                    timesteps={
                        NUM_ENV_STEPS_SAMPLED_LIFETIME: self.metrics.peek(
                            (ENV_RUNNER_RESULTS, NUM_ENV_STEPS_SAMPLED_LIFETIME), default=0
                        ),
                        NUM_AGENT_STEPS_SAMPLED_LIFETIME: self.metrics.peek(
                            (ENV_RUNNER_RESULTS, NUM_AGENT_STEPS_SAMPLED_LIFETIME), default=0
                        ),
                    },
                )
                td_errors = defaultdict(list)
                for result in learner_results:
                    for module_id, module_results in result.items():
                        if TD_ERROR_KEY in module_results:
                            td_errors[module_id].extend(
                                convert_to_numpy(module_results.pop(TD_ERROR_KEY).peek())
                            )
                td_errors = {
                    module_id: {TD_ERROR_KEY: np.concatenate(errors, axis=0)}
                    for module_id, errors in td_errors.items()
                }
                self.metrics.aggregate(learner_results, key=LEARNER_RESULTS)

            with self.metrics.log_time((TIMERS, REPLAY_BUFFER_UPDATE_PRIOS_TIMER)):
                update_priorities_in_episode_replay_buffer(
                    replay_buffer=buffer, td_errors=td_errors
                )

        # Replay export, checkpoints, and league snapshots use the Algorithm's
        # inference modules; keep them in sync with the learner even offline.
        modules_to_update = set(learner_results[0]) - {ALL_MODULES}
        self.env_runner_group.sync_weights(
            from_worker_or_learner_group=self.learner_group,
            policies=modules_to_update,
            global_vars=None,
            inference_only=True,
        )


class FixedReplayDQN(_FixedReplayMixin, DQN):
    """Rainbow DQN with a fixed replay dataset after capacity is reached."""


class FixedReplaySAC(_FixedReplayMixin, SAC):
    """SAC with a fixed replay dataset after capacity is reached."""