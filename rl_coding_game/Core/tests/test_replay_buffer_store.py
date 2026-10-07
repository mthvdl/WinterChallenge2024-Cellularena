import pickle
from collections import defaultdict

from ray.rllib.env.single_agent_episode import SingleAgentEpisode
from ray.rllib.utils.replay_buffers.episode_replay_buffer import EpisodeReplayBuffer

from Core.replay_buffer_store import load_replay_buffer, save_replay_buffer


def _episode(length):
	episode = SingleAgentEpisode(
		observations=list(range(length + 1)),
		actions=[0] * length,
		rewards=[0.5] * length,
		len_lookback_buffer=0,
	)
	episode.is_terminated = True
	return episode


def test_replay_buffer_round_trips_through_single_overwritten_file(tmp_path):
	path = tmp_path / "replay_buffer.pkl"
	source = EpisodeReplayBuffer(capacity=100)
	source.add(_episode(2))
	save_replay_buffer(source, path)
	source.add(_episode(3))
	save_replay_buffer(source, path)

	assert [p.name for p in tmp_path.iterdir()] == ["replay_buffer.pkl"]
	target = EpisodeReplayBuffer(capacity=100)
	load_replay_buffer(target, path)

	assert target.get_added_timesteps() == 5
	assert len(target) == 5


def test_multi_agent_buffer_with_closure_mapping_round_trips(tmp_path):
	from ray.rllib.env.multi_agent_episode import MultiAgentEpisode
	from ray.rllib.utils.replay_buffers.multi_agent_episode_buffer import (
		MultiAgentEpisodeReplayBuffer,
	)

	def make_mapping(module_id):
		return lambda agent_id, episode: module_id

	episode = MultiAgentEpisode(
		observations=[{"a": 0}, {"a": 1}],
		actions=[{"a": 0}],
		rewards=[{"a": 1.0}],
		terminateds={"a": True, "__all__": True},
		len_lookback_buffer=0,
		agent_to_module_mapping_fn=make_mapping("learner"),
	)
	source = MultiAgentEpisodeReplayBuffer(capacity=100)
	source.add(episode)
	path = tmp_path / "replay_buffer.pkl"
	save_replay_buffer(source, path)

	target = MultiAgentEpisodeReplayBuffer(capacity=100)
	load_replay_buffer(target, path)

	assert target.get_added_timesteps() == 1
	assert target.episodes[0].agent_to_module_mapping_fn("a", None) == "learner"


def test_loaded_prioritized_multi_agent_buffer_can_evict_and_sample(tmp_path):
	from ray.rllib.env.multi_agent_episode import MultiAgentEpisode
	from ray.rllib.utils.replay_buffers.multi_agent_prioritized_episode_buffer import (
		MultiAgentPrioritizedEpisodeReplayBuffer,
	)

	def _ma_episode():
		return MultiAgentEpisode(
			observations=[{"a": 0.0}, {"a": 1.0}, {"a": 2.0}],
			actions=[{"a": 0}, {"a": 1}],
			rewards=[{"a": 0.0}, {"a": 1.0}],
			terminateds={"a": True, "__all__": True},
			len_lookback_buffer=0,
		)

	source = MultiAgentPrioritizedEpisodeReplayBuffer(capacity=4)
	source.add([_ma_episode(), _ma_episode()])
	path = tmp_path / "replay_buffer.pkl"
	save_replay_buffer(source, path)

	target = MultiAgentPrioritizedEpisodeReplayBuffer(capacity=4)
	load_replay_buffer(target, path)
	assert target._sample_idx_to_tree_idx == source._sample_idx_to_tree_idx

	target.add(_ma_episode())
	target.sample(num_items=2)

	assert target.get_num_episodes_evicted() == 1


def test_load_repairs_rllib_sampled_counter(tmp_path):
	class _MultiAgentBuffer:
		def set_state(self, state):
			self.sampled_timesteps_per_module = defaultdict(list, state)

	path = tmp_path / "replay_buffer.pkl"
	path.write_bytes(pickle.dumps({"learner": 5}))
	buffer = _MultiAgentBuffer()
	load_replay_buffer(buffer, path)
	buffer.sampled_timesteps_per_module["learner"] += 2
	buffer.sampled_timesteps_per_module["new_module"] += 3

	assert dict(buffer.sampled_timesteps_per_module) == {"learner": 7, "new_module": 3}
