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