from Core.ray_policies import resolve_opponent_modes


def test_frozen_opponent_does_not_enable_league_refresh() -> None:
	assert resolve_opponent_modes(False, True, False) == (True, False)


def test_checkpoint_opponent_does_not_enable_league_refresh() -> None:
	assert resolve_opponent_modes(False, False, True) == (True, False)


def test_league_enables_frozen_opponents_and_refresh() -> None:
	assert resolve_opponent_modes(True, False, False) == (True, True)


def test_shared_self_play_enables_neither_mode() -> None:
	assert resolve_opponent_modes(False, False, False) == (False, False)