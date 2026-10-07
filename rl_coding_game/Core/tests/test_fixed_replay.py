from contextlib import nullcontext
from types import SimpleNamespace

import Core.fixed_replay as fixed_replay


class _CollectingAlgorithm:
    def _training_step_new_api_stack(self):
        self.collections += 1


class _Buffer:
    capacity = 3

    def __init__(self):
        self.size = 0
        self.added = 0
        self.samples = 0

    def __len__(self):
        return self.size

    def get_added_timesteps(self):
        return self.added

    def sample(self, **kwargs):
        self.samples += 1
        return ["saved episode"]

    def get_metrics(self):
        return {"buffer": self.size}


class _Metrics:
    def log_time(self, key):
        return nullcontext()

    def aggregate(self, values, key):
        pass

    def peek(self, key, default=None):
        return 3


class _Learner:
    def __init__(self):
        self.updates = 0

    def update(self, **kwargs):
        self.updates += 1
        return [{"shared": {}}]


class _EnvRunnerGroup:
    def __init__(self):
        self.synced = []

    def sync_weights(self, **kwargs):
        self.synced.append(kwargs)


class _Algorithm(fixed_replay._FixedReplayMixin, _CollectingAlgorithm):
    def __init__(self):
        self.local_replay_buffer = _Buffer()
        self.collections = 0
        self.learner_group = _Learner()
        self.env_runner_group = _EnvRunnerGroup()
        self.metrics = _Metrics()
        self._module_is_stateful = False
        self.config = SimpleNamespace(
            total_train_batch_size=2,
            n_step=1,
            model_config={},
            gamma=0.99,
            replay_buffer_config={"beta": 0.4},
        )


def test_fixed_replay_stops_collecting_and_keeps_learning(monkeypatch):
    algorithm = _Algorithm()
    priorities = []
    monkeypatch.setattr(fixed_replay, "calculate_rr_weights", lambda config: [1, 2])
    monkeypatch.setattr(
        fixed_replay, "update_priorities_in_episode_replay_buffer",
        lambda **kwargs: priorities.append(kwargs),
    )

    algorithm._training_step_new_api_stack()
    assert algorithm.collections == 1
    assert algorithm.learner_group.updates == 0

    # Whole-episode eviction can leave less than capacity stored at first fill.
    algorithm.local_replay_buffer.size = 2
    algorithm.local_replay_buffer.added = 4
    algorithm._training_step_new_api_stack()
    algorithm._training_step_new_api_stack()

    assert algorithm.collections == 1
    assert algorithm.local_replay_buffer.samples == 4
    assert algorithm.learner_group.updates == 4
    assert len(priorities) == 4
    assert all(item["replay_buffer"] is algorithm.local_replay_buffer for item in priorities)
    assert len(algorithm.env_runner_group.synced) == 2
    assert all(item["policies"] == {"shared"} for item in algorithm.env_runner_group.synced)