"""
scaffold_game.py – Bootstrap a new CodingGame in the rl_coding_game framework.

Creates the full directory structure and template files for a new 2-player game,
ready to be filled in with game-specific logic.

Usage
-----
    cd rl_coding_game

    # From a CodingGame URL:
    python scaffold_game.py --url https://www.codingame.com/contests/fall-challenge-2024

    # With explicit names:
    python scaffold_game.py --game blockout --puzzle-id fall-challenge-2024

Generated structure
-------------------
    games/<GAME>/
      __init__.py
      env.py                    PettingZoo ParallelEnv (fill in spaces + obs + rewards)
      factories.py              make_env() factory
      offline_replay_adapter.py Adapter stub (fill in iter_transitions)
      game/
        __init__.py
        game.py                 Game engine stub (fill in step + get_observation)
        replay_loader.py        Replay parsing stub (fill in load_replay)

    data/games/<GAME>/
      replays/                  (created, for downloaded CodingGame replays)
      README.md

    test_<GAME>.py              Smoke tests (in rl_coding_game/ root)
"""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path
from urllib.parse import urlparse

from project_paths import ensure_dir, shared_game_root, shared_replays_dir


def slug_from_url(url: str) -> str:
    parts = [p for p in urlparse(url).path.split("/") if p]
    return parts[-1] if parts else url


# ─────────────────────────────────────────────────────────────────────────────
# Template generators
# ─────────────────────────────────────────────────────────────────────────────

def _games_init(game: str) -> str:
    return f'"""PettingZoo environment for {game}."""\n'


def _factories(game: str) -> str:
    return textwrap.dedent(f'''\
        """{game} factory helpers for generic training scripts."""
        from __future__ import annotations

        from games.{game}.env import {_class(game)}Env


        def make_env() -> "{_class(game)}Env":
            return {_class(game)}Env()
    ''')


def _class(game: str) -> str:
    """Convert snake_case game slug to PascalCase."""
    return "".join(w.capitalize() for w in game.replace("-", "_").split("_"))


def _env(game: str) -> str:
    cls = _class(game)
    return textwrap.dedent(f'''\
        """
        {cls}Env  -  PettingZoo ParallelEnv for {game}.

        TODO: Fill in observation_space, action_space, and reward logic.
              See games/cellularena/env.py for a reference implementation.

        Quickstart checklist
        --------------------
        1. Implement the game engine in game/game.py
        2. Define observation channels and encode them in _observe()
        3. Define the action space (MultiDiscrete or Discrete)
        4. Implement step() reward logic
        5. Run:  python test_{game}.py
        """
        from __future__ import annotations

        import functools
        from typing import Any, Dict, List, Optional, Tuple

        import numpy as np
        from gymnasium import spaces
        from pettingzoo import ParallelEnv

        from .game.game import Game


        class {cls}Env(ParallelEnv):
            """PettingZoo ParallelEnv wrapping the {game} game."""

            metadata = {{
                "render_modes": [],
                "name": "{game}_v0",
            }}

            def __init__(
                self,
                seed: Optional[int] = None,
                render_mode: Optional[str] = None,
            ) -> None:
                super().__init__()
                self.possible_agents: List[str] = ["player_0", "player_1"]
                self._agent_to_idx: Dict[str, int] = {{"player_0": 0, "player_1": 1}}
                self.render_mode = render_mode
                self._seed = seed
                self._game = Game(seed)

            # ------------------------------------------------------------------
            # Spaces  (TODO: fill in your game's shapes)
            # ------------------------------------------------------------------

            @functools.lru_cache(maxsize=None)
            def observation_space(self, agent: str) -> spaces.Space:
                # TODO: replace with your actual observation shape
                raise NotImplementedError(
                    "Define the observation space for {game}. "
                    "See games/cellularena/env.py for an example."
                )

            @functools.lru_cache(maxsize=None)
            def action_space(self, agent: str) -> spaces.Space:
                # TODO: replace with your actual action space
                raise NotImplementedError(
                    "Define the action space for {game}. "
                    "Example: spaces.Discrete(N_ACTIONS) or "
                    "spaces.MultiDiscrete([N] * K)"
                )

            # ------------------------------------------------------------------
            # Core API
            # ------------------------------------------------------------------

            def reset(
                self,
                seed: Optional[int] = None,
                options: Optional[Dict[str, Any]] = None,
            ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
                if seed is not None:
                    self._seed = seed
                self._game = Game(self._seed)
                self._game.reset()
                self.agents = list(self.possible_agents)
                obs = {{agent: self._observe(idx) for agent, idx in self._agent_to_idx.items()}}
                infos = {{agent: {{}} for agent in self.agents}}
                return obs, infos

            def step(
                self, actions: Dict[str, Any]
            ) -> Tuple[
                Dict[str, Any],
                Dict[str, float],
                Dict[str, bool],
                Dict[str, bool],
                Dict[str, Any],
            ]:
                # Translate PettingZoo actions → game actions
                game_actions = {{
                    idx: actions.get(agent)
                    for agent, idx in self._agent_to_idx.items()
                    if agent in actions
                }}
                done, rewards_list = self._game.step(game_actions)

                obs = {{agent: self._observe(idx) for agent, idx in self._agent_to_idx.items()}}

                # TODO: map game rewards to agent rewards
                rewards = {{agent: float(rewards_list[idx]) for agent, idx in self._agent_to_idx.items()}}
                terminations = {{agent: done for agent in self.agents}}
                truncations = {{agent: False for agent in self.agents}}
                infos = {{agent: {{}} for agent in self.agents}}

                if done:
                    self.agents = []

                return obs, rewards, terminations, truncations, infos

            def observe(self, agent: str) -> Any:
                return self._observe(self._agent_to_idx[agent])

            # ------------------------------------------------------------------
            # Internal helpers  (TODO: implement)
            # ------------------------------------------------------------------

            def _observe(self, player_idx: int) -> Any:
                # TODO: build and return the observation dict/array for player_idx
                # See games/cellularena/env.py _observe() for reference
                raise NotImplementedError("Implement _observe() for {game}")
    ''')


def _game_init(game: str) -> str:
    return f'"""Core game engine for {game}."""\n'


def _game_engine(game: str) -> str:
    cls = _class(game)
    return textwrap.dedent(f'''\
        """
        {cls} game engine.

        TODO: Implement the full game logic here.
              Reference: games/cellularena/game/game.py

        Checklist
        ---------
        - Implement reset() to set up a fresh game state
        - Implement step(actions) to advance one turn; return (done, [r0, r1])
        - Implement get_observation(player_idx) to return raw state for the env
        - Define constants: MAX_TURNS, any grid/board dimensions
        """
        from __future__ import annotations

        from typing import Any, Dict, List, Optional, Tuple


        # TODO: fill in your game constants
        MAX_TURNS: int = 100   # maximum turns before game ends


        class Game:
            """Core game engine for {game}."""

            def __init__(self, seed: Optional[int] = None) -> None:
                self._seed = seed
                self._turn = 0
                # TODO: initialise game state fields

            def reset(self) -> None:
                """Re-initialise to a new game (called by env.reset())."""
                self._turn = 0
                # TODO: reset board / state

            def step(
                self, actions: Dict[int, Any]
            ) -> Tuple[bool, List[float]]:
                """
                Apply both players' actions and advance the game state by one turn.

                Parameters
                ----------
                actions : dict mapping player_idx (0 or 1) → action value

                Returns
                -------
                done    : True if the game has ended
                rewards : [reward_player0, reward_player1]  (non-zero only at end)
                """
                self._turn += 1
                # TODO: implement game logic

                done = self._turn >= MAX_TURNS  # TODO: add win/loss conditions
                rewards = [0.0, 0.0]
                if done:
                    # TODO: compute terminal rewards
                    rewards = [0.0, 0.0]
                return done, rewards

            def get_observation(self, player_idx: int) -> Any:
                """
                Return the full game state from the perspective of player_idx.
                The env will encode this into observation arrays.
                """
                # TODO: return whatever the env needs to build observations
                raise NotImplementedError("Implement get_observation() for {game}")

            # ------------------------------------------------------------------
            # Replay initialisation (used by offline_replay_adapter)
            # ------------------------------------------------------------------

            def init_from_replay(self, global_data: Dict[str, Any]) -> None:
                """Initialise game state from replay global data (board layout etc.)."""
                # TODO: parse global_data and set up the board
                raise NotImplementedError("Implement init_from_replay() for {game}")

            def step_replay(
                self, commands: Dict[int, Any]
            ) -> Tuple[bool, List[float]]:
                """Like step(), but driven by recorded replay commands."""
                return self.step(commands)
    ''')


def _replay_loader(game: str) -> str:
    return textwrap.dedent(f'''\
        """
        Replay loader for {game}.

        TODO: Parse CodingGame replay JSON (frame-based format) into structured data.
              Reference: games/cellularena/game/replay_loader.py

        A CodingGame replay JSON looks like::

            {{
                "gameId": 12345,
                "agents": [{{"name": "PlayerA", ...}}, ...],
                "frames": [
                    {{"view": "...", "stdout": ["cmd1", "cmd2"], ...}},
                    ...
                ]
            }}

        Implement load_replay(path) to return a structured Replay object that
        offline_replay_adapter.py can iterate over.
        """
        from __future__ import annotations

        import json
        from dataclasses import dataclass, field
        from pathlib import Path
        from typing import Any, Dict, List


        @dataclass
        class ReplayTurn:
            turn: int
            commands: List[List[str]]   # commands[0] = player 0 stdout, [1] = player 1
            # TODO: add any per-turn state fields you need (e.g. view data)


        @dataclass
        class Replay:
            game_id: int
            global_data: Dict[str, Any]
            turns: List[ReplayTurn]


        def load_replay(path: Path) -> Replay:
            """
            Load a CodingGame replay JSON (raw or core format) into a Replay.

            TODO: Implement this for {game}.
            """
            data = json.loads(path.read_text(encoding="utf-8"))

            # Handle both raw CodingGame format and scaffolded "core" format
            if data.get("format") == "{game}-raw-v1":
                data = data["raw"]

            game_id = data.get("gameId", 0)

            # TODO: extract global_data (initial board layout, etc.)
            global_data: Dict[str, Any] = {{}}

            turns: List[ReplayTurn] = []
            frames = data.get("frames", [])
            for i, frame in enumerate(frames):
                stdout = frame.get("stdout", [])
                # CodingGame gives one stdout entry per agent
                cmds: List[List[str]] = []
                for agent_out in stdout if isinstance(stdout, list) else [stdout]:
                    cmds.append(
                        [line.strip() for line in str(agent_out).splitlines() if line.strip()]
                    )
                while len(cmds) < 2:
                    cmds.append([])
                turns.append(ReplayTurn(turn=i, commands=cmds))

            return Replay(game_id=game_id, global_data=global_data, turns=turns)
    ''')


def _offline_adapter(game: str) -> str:
    cls = _class(game)
    return textwrap.dedent(f'''\
        """
        {cls} offline replay adapter.

        TODO: Implement iter_transitions() to convert replay turns into RL Transitions.
              Reference: games/cellularena/offline_replay_adapter.py

        Steps
        -----
        1. Load a replay with load_replay(path)
        2. Initialise a Game from replay.global_data
        3. For each turn: encode observation, encode action, call game.step_replay(),
           encode next observation, yield Transition(obs, action, reward, next_obs, done)
        """
        from __future__ import annotations

        from pathlib import Path
        from typing import Iterable

        from rl.experience import Transition
        from rl.offline_adapter import ReplayTransitionAdapter

        from games.{game}.game.game import Game
        from games.{game}.game.replay_loader import load_replay


        def create_adapter() -> "ReplayTransitionAdapter":
            return {cls}ReplayAdapter()


        class {cls}ReplayAdapter(ReplayTransitionAdapter):
            """Convert {game} replay files into RL Transition objects."""

            def iter_transitions(self, replay_path: Path) -> Iterable[Transition]:
                replay = load_replay(replay_path)
                game = Game()
                game.init_from_replay(replay.global_data)

                for turn in replay.turns:
                    # TODO: encode observations before step
                    obs_p0 = game.get_observation(0)
                    obs_p1 = game.get_observation(1)

                    # TODO: encode actions from turn.commands
                    action_p0 = self._encode_action(turn.commands[0])
                    action_p1 = self._encode_action(turn.commands[1])

                    done, rewards = game.step_replay({{0: turn.commands[0], 1: turn.commands[1]}})

                    next_obs_p0 = game.get_observation(0)
                    next_obs_p1 = game.get_observation(1)

                    yield Transition(
                        obs=obs_p0,
                        action=action_p0,
                        reward=float(rewards[0]),
                        next_obs=next_obs_p0,
                        done=done,
                    )
                    yield Transition(
                        obs=obs_p1,
                        action=action_p1,
                        reward=float(rewards[1]),
                        next_obs=next_obs_p1,
                        done=done,
                    )

                    if done:
                        break

            def _encode_action(self, commands: list) -> int:
                # TODO: convert raw stdout command strings to action integers
                return 0
    ''')


def _smoke_tests(game: str) -> str:
    cls = _class(game)
    return textwrap.dedent(f'''\
        """Smoke tests for the {game} PettingZoo environment.

        Run:  cd rl_coding_game && python test_{game}.py
        """
        from __future__ import annotations

        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))

        from games.{game}.env import {cls}Env


        def test_env_reset() -> None:
            env = {cls}Env()
            obs, infos = env.reset()
            assert set(obs.keys()) == {{"player_0", "player_1"}}, f"Missing agents: {{obs.keys()}}"
            print("PASS test_env_reset")


        def test_env_spaces() -> None:
            env = {cls}Env()
            env.reset()
            for agent in env.possible_agents:
                obs_space = env.observation_space(agent)
                act_space = env.action_space(agent)
                assert obs_space is not None
                assert act_space is not None
            print("PASS test_env_spaces")


        def test_env_random_episode() -> None:
            env = {cls}Env(seed=0)
            obs, _ = env.reset()
            step = 0
            while env.agents:
                actions = {{agent: env.action_space(agent).sample() for agent in env.agents}}
                obs, rewards, terms, truncs, infos = env.step(actions)
                step += 1
                assert step < 10_000, "Episode did not terminate"
            print(f"PASS test_env_random_episode  ({{step}} steps)")


        if __name__ == "__main__":
            test_env_reset()
            test_env_spaces()
            test_env_random_episode()
            print("\\nAll {game} smoke tests passed.")
    ''')


def _data_readme(game: str, puzzle_id: str) -> str:
    return textwrap.dedent(f'''\
        # {game} replays

        CodingGame puzzle: `{puzzle_id}`
        Game rules:        https://www.codingame.com/contests/{puzzle_id}

        ## Downloading replays

        ```bash
        cd rl_coding_game
        python download_games.py --game {game} --puzzle-id {puzzle_id}
        ```

        ## Downloading game rules

        ```bash
        python download_rules.py --game {game} --puzzle-id {puzzle_id}
        ```
    ''')


# ─────────────────────────────────────────────────────────────────────────────
# Scaffolding
# ─────────────────────────────────────────────────────────────────────────────

def _write(path: Path, content: str, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        print(f"  SKIP (exists)  {path}")
        return
    path.write_text(content, encoding="utf-8")
    print(f"  CREATED        {path}")


def scaffold(game: str, puzzle_id: str, overwrite: bool = False) -> None:
    root = Path(__file__).parent

    # games/<game>/
    game_dir = root / "games" / game
    game_game_dir = game_dir / "game"
    ensure_dir(game_game_dir)

    _write(game_dir / "__init__.py", _games_init(game), overwrite)
    _write(game_dir / "factories.py", _factories(game), overwrite)
    _write(game_dir / "env.py", _env(game), overwrite)
    _write(game_dir / "offline_replay_adapter.py", _offline_adapter(game), overwrite)
    _write(game_game_dir / "__init__.py", _game_init(game), overwrite)
    _write(game_game_dir / "game.py", _game_engine(game), overwrite)
    _write(game_game_dir / "replay_loader.py", _replay_loader(game), overwrite)

    # data/games/<game>/replays/
    replays_dir = ensure_dir(root / "data" / "games" / game / "replays")
    _write(replays_dir.parent / "README.md", _data_readme(game, puzzle_id), overwrite)

    # smoke test in root
    _write(root / f"test_{game}.py", _smoke_tests(game), overwrite)

    print(f"""
Scaffold complete for '{game}'.

Next steps
----------
1. Download game rules:
     python download_rules.py --game {game} --puzzle-id {puzzle_id}

2. Download expert replays:
     python download_games.py --game {game} --puzzle-id {puzzle_id}

3. Implement the game engine:
     games/{game}/game/game.py          ← core logic (step, get_observation)
     games/{game}/game/replay_loader.py ← parse CodingGame JSON frames

4. Implement the observation space in:
     games/{game}/env.py                ← observation_space, action_space, _observe

5. Implement the offline adapter:
     games/{game}/offline_replay_adapter.py  ← iter_transitions, _encode_action

6. Run smoke tests:
     python test_{game}.py

7. Validate engine against downloaded replays (once implemented):
     python validate_engine.py --game {game}

8. Run self-play training:
     conda run -n cellularena python train_rainbow.py \\
         --env-factory games.{game}.factories:make_env \\
         --game {game} \\
         --experiment-name exp_001_baseline \\
         --total-steps 500000 --n-envs 4 --self-play --reset-replay

See AGENTS.md and .github/skills/ for detailed workflow guides.
""")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a new CodingGame in the rl_coding_game framework"
    )
    parser.add_argument("--url", type=str, default="", help="Full CodingGame URL")
    parser.add_argument("--game", type=str, default="", help="Local game name (snake_case)")
    parser.add_argument("--puzzle-id", type=str, default="", help="CodingGame puzzle slug")
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing template files (use with care!)"
    )
    args = parser.parse_args()

    puzzle_id = args.puzzle_id
    if not puzzle_id and args.url:
        puzzle_id = slug_from_url(args.url)
    if not puzzle_id:
        print("ERROR: provide --url or --puzzle-id")
        sys.exit(1)

    game = args.game or puzzle_id.replace("-", "_")

    print(f"Scaffolding game '{game}' (puzzle: {puzzle_id}) ...")
    scaffold(game, puzzle_id, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
