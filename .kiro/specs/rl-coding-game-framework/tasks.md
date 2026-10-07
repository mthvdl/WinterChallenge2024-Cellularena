# Implementation Plan — rl_coding_game Framework

This plan documents the framework as a buildable sequence of tasks. Most tasks
reflect code that **already exists** and are marked complete; the remaining
unchecked tasks are genuine gaps (chiefly the deferred offline / self-play-from-
pretrained paths) plus verification/hardening work. Each task cites the
requirements it satisfies.

Convention: `[x]` existing & verified in the repo, `[ ]` not yet implemented or
needs implementation/verification.

---

## 1. Game-agnostic Core foundation

- [x] 1.1 Define project path conventions (`Core/project_paths.py`): game-first
  shared replays and per-experiment artifact directories.
  - _Requirements: 1.4_
- [x] 1.2 Define the action-mask contract (`Core/action_mask.py`): stable keys
  and an all-legal default `ActionMaskBuilder`.
  - _Requirements: 1.3, 6.1_
- [x] 1.3 Define typed config dataclasses and merge/validation helpers
  (`Core/ray_config.py`): `RayRunSettings`, `LeaguePoolSettings`, `DQNSettings`,
  `load_overrides`, `settings_dict`, `complete_episodes_only`,
  `validate_sampled_episodes`.
  - _Requirements: 1.1, 8.4, 9.1, 9.2_
- [x] 1.4 Provide env registration + multi-agent replay buffer
  (`Core/ray_env.py`), including the RLlib string-check metaclass workaround.
  - _Requirements: 1.1, 1.2, 8.2_
- [x] 1.5 Add the dynamic factory loader (`Core/factory.py`,
  `load_symbol("module:attr")`).
  - _Requirements: 1.2_

## 2. Self-play, league, and checkpoints (Core)

- [x] 2.1 Implement policy setup and mappings (`Core/ray_policies.py`):
  shared / learner+opponent specs, deterministic league mapping,
  `resolve_opponent_modes/ids`, `seed_opponents_from_policy`,
  `load_policy_from_checkpoint`.
  - _Requirements: 10.1, 10.2, 10.3, 10.5_
- [x] 2.2 Implement league pool management (`Core/league.py`):
  `promote_checkpoint` (bounded, atomic, manifest, evict oldest),
  `discover_checkpoints`, `latest_checkpoint_before`.
  - _Requirements: 10.4, 10.5_
- [x] 2.3 Implement replay-buffer persistence (`Core/replay_buffer_store.py`):
  atomic save/load with RLlib 2.58 `set_state` workarounds.
  - _Requirements: 11.3_

## 3. Training loop and fixed replay (Core)

- [x] 3.1 Implement the algorithm-agnostic training loop
  (`Core/ray_training.py::train`): iterate, TensorBoard scalars, eval/checkpoint
  callbacks, checkpoint + replay-buffer persistence, `start_iteration` resume.
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 12.1_
- [x] 3.2 Implement scalar metric extraction (`Core/ray_metrics.py`).
  - _Requirements: 11.2_
- [x] 3.3 Implement fixed-replay mode (`Core/fixed_replay.py`):
  `FixedReplayDQN`/`FixedReplaySAC` stop sampling once the buffer fills and
  continue learning from stored transitions.
  - _Requirements: 8.5_

## 4. Cellularena game engine

- [x] 4.1 Implement grid primitives (`engine/coord.py`, `engine/grid.py`,
  `engine/organ.py`) and symmetric map generation (`engine/grid_maker.py`).
  - _Requirements: 4.1_
- [x] 4.2 Implement core simulation (`engine/game.py`): growth, costs,
  harvesting, tentacle combat with subtree removal, sporing, collisions,
  terminal conditions; step/observation/mask APIs.
  - _Requirements: 4.1, 4.2, 4.4_
- [x] 4.3 Implement replay ingestion (`engine/replay_loader.py` + game replay
  methods): init from global data, set storage, parse commands, step replay,
  snapshot.
  - _Requirements: 4.3, 15.1_

## 5. Cellularena environment and spaces

- [x] 5.1 Implement the PettingZoo ParallelEnv (`engine/env.py`): Dict obs,
  native `MultiDiscrete`, sparse terminal rewards, potential-based shaping,
  terminal `infos`, temporal observation builder.
  - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.6_
- [x] 5.2 Implement the discrete "paper" action env
  (`engine/action_env.py`): `Discrete(4033)`, `self_player_idx`, decode via
  adapter, `make_action_env` factory.
  - _Requirements: 5.3_
- [x] 5.3 Implement the action codec (`engine/action_adapter.py`): encode/decode,
  mask build, perspective transforms, affordability.
  - _Requirements: 5.3, 6.2, 6.4_
- [x] 5.4 Implement observation feature builders (`engine/obs/*`).
  - _Requirements: 7.1, 7.3_

## 6. RLlib adapter and masking (Cellularena)

- [x] 6.1 Implement the RLlib env wrapper (`ray/env_wrapper.py`): add
  `action_mask`, optional replay recording, env creator, env registration.
  - _Requirements: 6.1, 6.2_
- [x] 6.2 Implement the game's mask builder (`policy/action_mask.py`) producing
  the `Discrete(N_ACTIONS)` legal mask from live state.
  - _Requirements: 6.2, 6.4_
- [x] 6.3 Implement the env-to-module connector and feature preprocessor
  (`Core/ray_connectors.py`, `ray/dqn/preprocessor.py`,
  `ray/sac/preprocessor.py`): build features, append mask, reject non-finite,
  write back to episode.
  - _Requirements: 7.1, 7.2, 7.3_
- [x] 6.4 Implement masked RLModules (`ray/dqn/modules.py`,
  `ray/sac/modules.py`): apply mask inside the policy distribution.
  - _Requirements: 6.3_

## 7. Config binding and algorithm configs (Cellularena)

- [x] 7.1 Bind the config schema (`ray/config.py`): five top-level sections,
  experiment/runner/learner/evaluator keys, `CellularenaEnvSettings`.
  - _Requirements: 9.1, 9.2, 9.3_
- [x] 7.2 Build the Rainbow DQN config (`ray/dqn/config.py`): masked module,
  Rainbow knobs, prioritized buffer, connector, policy setup, fixed-replay
  toggle, evaluation wiring.
  - _Requirements: 8.1, 8.2, 8.4, 8.5_
- [x] 7.3 Build the discrete SAC config (`ray/sac/config.py`): masked module,
  CNN network, size-aware target entropy, SAC hyperparameters, fixed-replay
  toggle.
  - _Requirements: 8.1, 8.3, 8.4, 8.5_
- [x] 7.4 Implement evaluation wiring (`ray/evaluation.py`): opponent policy id,
  `configure_evaluation`, `prepare_evaluation`, TV-replay saving.
  - _Requirements: 12.1, 12.2, 12.3_

## 8. Training entry points (Cellularena)

- [x] 8.1 Implement the DQN entry point (`ray/dqn/train.py`): config load + copy,
  CLI flags, opponent/league resolution, env registration, build, seed/load
  opponents, run loop with checkpoint/eval callbacks.
  - _Requirements: 8.1, 8.6, 10.1, 10.2, 10.3, 10.4, 11.1, 12.1_
- [x] 8.2 Implement the SAC entry point (`ray/sac/train.py`) including
  `--resume-checkpoint` (restore algo + buffer, derive `start_iteration`).
  - _Requirements: 8.1, 8.6, 11.4_

## 9. CLI tooling (Core)

- [x] 9.1 Scaffold CLI (`Core/cli/scaffold_game.py`): generate a full game
  package from a URL/puzzle id; persist conda env to `env.sh`.
  - _Requirements: 2.1, 2.2, 2.3_
- [x] 9.2 Rules download CLI (`Core/cli/download_rules.py`): Markdown/HTML/text.
  - _Requirements: 3.1_
- [x] 9.3 Replay download CLI (`Core/cli/download_games.py`): top-player /
  single-game; `CG_SESSION` or credentials; convert to core raw.
  - _Requirements: 3.2, 3.3, 3.4_
- [x] 9.4 Bot export CLI (`Core/cli/export_to_codingame.py`): single-file bot,
  quantization, packed blob, numerical-equivalence verification.
  - _Requirements: 13.1, 13.2, 13.3, 13.4_
- [x] 9.5 SAC preflight CLI (`Core/cli/preflight_sac.py`): print resolved
  settings with source; refuse to start on dashboard/trainer conflict.
  - _Requirements: 9.5, 16.3_

## 10. Replay viewing, conversion, and validation

- [x] 10.1 Implement replay format conversion (`replay_transform.py`): CodinGame
  ↔ core ↔ viewer.
  - _Requirements: 14.1_
- [x] 10.2 Implement the standalone viewer and runtime server
  (`Viewer/`, `Viewer/viewer_server.py`).
  - _Requirements: 14.2, 14.3_
- [x] 10.3 Implement self-play episode export (`export_episode_replay.py`).
  - _Requirements: 14.1_
- [x] 10.4 Implement engine validation (`validate_engine.py`): replay-driven
  per-turn comparison, initial-storage inference, loop mode.
  - _Requirements: 15.1, 15.2, 15.3_
- [x] 10.5 Implement synthetic replay generation (`generate_test_replay.py`).
  - _Requirements: 15.4_

## 11. Documentation and agent workflows (skills)

- [x] 11.1 Author command references (`AGENTS.md` at repo and game level) kept
  consistent with the CLI and entry points.
  - _Requirements: 16.4_
- [x] 11.2 Author workflow skills under `.github/skills/`: `new-game`,
  `run-experiment`, `download-replays`, `validate-game`, `tensorboard`,
  `delete-experiment`.
  - _Requirements: 16.1, 16.2, 16.3_
- [x] 11.3 Centralize AI guidance (`ai/memory/*`) surfaced via `.kiro/steering`
  and `.github/copilot-instructions.md`.
  - _Requirements: 16.4_

## 12. Test coverage (verification)

> Baseline measured with `coverage` over the full suite: 115 tests passing,
> 54% line coverage overall; `engine/game.py` at 73%. After the additions
> below: 143 tests passing, `engine/game.py` at 85%, core rule paths directly
> asserted. The engine is byte-exact against 286 real-replay validations
> (storage + full organ state + observation tensors), exit 0.

- [x] 12.1 Core tests (`Core/tests/*`) for config, policies, training, metrics,
  league, fixed replay, buffer persistence, DQN/SAC config.
  - _Requirements: 1.1, 8.*, 9.*, 10.*, 11.*_
- [x] 12.2 Cellularena config/module tests
  (`ray/tests/test_config.py`, `ray/sac/test_modules.py`).
  - _Requirements: 6.3, 9.3_
- [x] 12.3 Engine smoke/replay tests (`engine/tests/*`).
  - _Requirements: 4.*, 5.1_
- [x] 12.4 Add isolated unit tests for each core game rule
  (`engine/tests/test_game_rules.py`): protein absorption, harvesting,
  tentacle kill + child-subtree cascade, growth collision → wall, sporing a
  new ROOT, affordability per organ cost. Previously these rules were only
  exercised incidentally by random episodes.
  - _Requirements: 4.1, 4.2_
- [x] 12.5 Wire the replay validator into pytest
  (`engine/tests/test_engine_validation.py`): validate a representative sample
  of real replays (full run via `CELLULARENA_VALIDATE_ALL=1`) so an engine
  regression fails CI instead of only the manual CLI.
  - _Requirements: 15.1, 15.2, 15.3_
- [x] 12.6 Cover the Discrete(4033) SPORE/ROOT decode branch
  (`engine/tests/test_action_adapter_spore.py`): channel-0 ROOT action decodes
  to a legal SPORE slot action, executes to create a new ROOT, and returns no
  action when ROOT is unaffordable.
  - _Requirements: 5.3, 6.2_
- [ ] 12.7 Add an end-to-end smoke test that runs one DQN and one SAC iteration
  with zero runners and asserts a checkpoint + replay buffer are written.
  - _Requirements: 8.1, 8.6, 11.1, 11.3_
- [ ] 12.8 Add a fail-fast test asserting that an unfinished or non-finite
  sampled episode raises during training.
  - _Requirements: 8.4_

## 13. Deferred: offline pretraining and self-play from pretrained

- [ ] 13.1 Fix and implement the offline replay adapter
  (`engine/offline_replay_adapter.py`). **BUG (confirmed):** the module fails
  to import — it references `Core.experience.Transition` and
  `Core.offline_adapter.ReplayTransitionAdapter`, neither of which exists in
  `Core/`. It is the only module in the codebase that fails an import sweep.
  Either restore the missing `Core.experience` / `Core.offline_adapter`
  modules or rewrite the adapter against the current transition representation.
  - _Requirements: 17.1_
- [ ] 13.2 Implement an offline pretraining entry point that consumes adapter
  transitions and writes a checkpoint loadable by the online trainers.
  - _Requirements: 17.2_
- [ ] 13.3 Wire self-play bootstrap from a pretrained checkpoint (initialize
  learner and optionally opponents) into the DQN/SAC entry points.
  - _Requirements: 17.3_
- [ ] 13.4 Update the `offline-training` and `selfplay-from-pretrained` skills to
  invoke the implemented paths once (13.2)/(13.3) land; until then keep them
  routing to `run-experiment` and never invoking retired trainers.
  - _Requirements: 17.4_
