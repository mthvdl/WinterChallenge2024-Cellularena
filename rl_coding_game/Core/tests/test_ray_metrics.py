from Core.ray_metrics import scalar_metrics


def test_scalar_metrics_extracts_common_and_evaluation_values() -> None:
	metrics = scalar_metrics({
		"training_iteration": 2,
		"episode_return_mean": 1.5,
		"evaluation": {"episode_return_mean": 0.25},
		"ignored": "text",
	})

	assert metrics == {
		"training_iteration": 2.0,
		"episode_return_mean": 1.5,
		"evaluation/episode_return_mean": 0.25,
	}


def test_scalar_metrics_flattens_nested_rlib_metrics() -> None:
	metrics = scalar_metrics({
		"env_runners": {"episode_return_mean": 0.75},
		"learners": {"learner": {"total_loss": 3.0}},
	})

	assert metrics == {
		"env_runners/episode_return_mean": 0.75,
		"learners/learner/total_loss": 3.0,
	}