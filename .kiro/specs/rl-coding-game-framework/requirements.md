# Requirements — rl_coding_game Framework

## Introduction

`rl_coding_game` is a generic framework for training reinforcement-learning (RL)
agents on two-player [CodinGame](https://www.codingame.com) puzzles. It is built
on [PettingZoo](https://pettingzoo.farama.org/) (ParallelEnv API) and
[Ray RLlib](https://docs.ray.io/en/latest/rllib/index.html) (new-stack RLModule
API), and ships with **Rainbow DQN** and **discrete SAC** as the two supported
algorithms. **Cellularena** (CodinGame Winter Challenge 2024) is the reference
implementation.

The framework is organized into two layers with a strict separation of concerns:

- **`Core/`** — game-agnostic RL plumbing: environment registration, config
  resolution, self-play / league policy setup, the training loop, replay-buffer
  persistence, the action-mask contract, CLI tooling, and project path
  conventions.
- **`Games/<GAME>/`** — a per-game engine, PettingZoo environment, and RLlib
  adapters (preprocessors, networks, config/train modules, action mapper).

The guiding goal is that onboarding a new game costs roughly an hour of
boilerplate (auto-scaffolded) plus the time to implement the game engine, while
keeping the engine protocol-faithful and ML concerns out of it.

This document captures the behavior the system must provide, written as user
stories with EARS-style acceptance criteria. It documents both what exists today
and the two deferred capabilities (offline pretraining and self-play from a
pretrained checkpoint) so the spec is complete.

### Glossary

- **Game engine** — pure simulation of the puzzle rules; no ML features.
- **Env wrapper** — PettingZoo ParallelEnv exposed to RLlib, adding the legal
  action mask from live game state.
- **Preprocessor / feature builder** — RLlib env-to-module ConnectorV2 that turns
  raw observations into model features.
- **Action mask** — boolean vector marking which actions are legal this turn.
- **Self-play** — both players driven by one shared learning policy.
- **Frozen opponent** — player 1 driven by a non-training policy.
- **League pool** — bounded set of past checkpoints used as rotating opponents.
- **Experiment** — a named training run with its own checkpoints, replays, and
  config under `Games/<game>/experiments/<algorithm>/<experiment>/`.

---

## Requirements

### Requirement 1 — Generic, game-agnostic core

**User Story:** As a framework maintainer, I want the RL plumbing to be fully
game-agnostic, so that supporting a new two-player CodinGame puzzle does not
require changing `Core/`.

#### Acceptance Criteria

1. THE `Core/` package SHALL expose environment registration, config resolution,
   policy/self-play setup, the training loop, metric extraction, replay-buffer
   persistence, league management, and the action-mask contract without
   referencing any specific game.
2. WHEN a new game package provides a PettingZoo env factory and DQN/SAC
   config/train modules, THEN the framework SHALL train on it using the same
   `Core/` modules unchanged.
3. THE action-mask contract SHALL define stable keys (`observations`,
   `action_mask`) and a base builder that returns an all-legal mask by default,
   so games may override masking without altering the contract.
4. THE project path conventions SHALL be game-first: shared replays under
   `Games/<game>/experiments/shared/replays` and per-experiment artifacts under
   `Games/<game>/experiments/<algorithm>/<experiment>/`.

### Requirement 2 — Scaffold a new game

**User Story:** As a developer, I want to scaffold a new game package from a
CodinGame URL, so that I can start implementing the engine instead of writing
boilerplate.

#### Acceptance Criteria

1. WHEN the developer runs the scaffold CLI with a CodinGame URL or puzzle id,
   THEN THE system SHALL generate a `Games/<GAME>/` package containing the env,
   engine stub, replay loader, factories, Ray env wrapper, DQN and SAC
   preprocessor/network/config/train modules, action-mask builder, action mapper,
   offline adapter, a `config.yaml.example`, smoke tests, and empty replay
   directories.
2. WHEN a conda environment name is supplied, THEN THE scaffold SHALL persist it
   to the generated `Games/<GAME>/env.sh`.
3. THE generated engine module SHALL contain explicit TODO markers indicating
   where the developer implements game rules.
4. IF the target game package already exists, THEN THE scaffold SHALL NOT silently
   overwrite the developer's engine implementation.

### Requirement 3 — Download rules and expert replays

**User Story:** As a developer, I want to download the puzzle statement and
expert replays, so that I can implement and validate the engine against real
data.

#### Acceptance Criteria

1. WHEN the developer runs the rules CLI with a puzzle URL, THEN THE system SHALL
   save the statement as Markdown (plus HTML and plain-text copies) under the
   game directory.
2. WHEN the developer runs the replay-download CLI with a puzzle URL, THEN THE
   system SHALL fetch top-player replays, convert them to the core raw format, and
   save them to the shared replays directory as `core_<ID>.json`.
3. WHERE authentication is required, THE system SHALL use a `CG_SESSION` cookie
   (preferred) or `CG_USERNAME`/`CG_PASSWORD` read from the environment, and
   SHALL NOT commit those secrets.
4. WHEN a known game id is provided, THEN THE system SHALL download that single
   game regardless of leaderboard access.
5. IF credentials are missing or invalid for a gated request, THEN THE system
   SHALL report a clear error rather than saving an empty or partial replay.

### Requirement 4 — Game engine (Cellularena reference)

**User Story:** As a developer, I want a protocol-faithful game engine, so that
training and validation reflect the real puzzle rules.

#### Acceptance Criteria

1. THE engine SHALL simulate the full rule set: grid generation (point-symmetric
   obstacles and proteins), organ growth and costs, harvesting, tentacle combat
   (removing the killed organ's child subtree), sporing new ROOTs, growth
   collisions (both pay cost, cell becomes wall), and terminal conditions (max
   turns, elimination, full grid, or no progress).
2. THE engine SHALL expose a step API that accepts per-player actions and returns
   a done flag and per-player rewards, plus observation and action-mask queries.
3. THE engine SHALL provide replay-ingestion methods to initialize from global
   data, set initial storage, parse raw commands, and step through a reference
   replay for validation.
4. THE engine SHALL contain only simulation logic and SHALL NOT compute ML
   features or model-specific encodings.

### Requirement 5 — PettingZoo environment and spaces

**User Story:** As an RL engineer, I want a PettingZoo ParallelEnv with
well-defined observation and action spaces, so that standard RL tooling can
consume the game.

#### Acceptance Criteria

1. THE environment SHALL implement the PettingZoo ParallelEnv API with two agents
   acting simultaneously, resolving the turn after both submit.
2. THE observation SHALL be a Dict with a spatial `grid` tensor, a per-player
   `storage` tensor, and a normalized `turn` scalar, with temporal history
   stacking configurable via `obs_history_steps`.
3. THE native action space SHALL be `MultiDiscrete([ACTIONS_PER_ORG] * MAX_ROOTS)`
   (one slot per organism), and a wrapper SHALL also expose a collapsed
   `Discrete(N_ACTIONS)` "paper" action space used for RLlib training.
4. THE base game reward SHALL be sparse and terminal-only (+1/-1 win/loss,
   +0.5/-0.5 protein tie-break, 0 true tie).
5. WHERE reward shaping is enabled, THE environment SHALL add policy-invariant,
   zero-sum, potential-based shaping on non-terminal steps; reward shaping SHALL
   be configurable and its default documented per layer.
6. WHEN an episode terminates, THEN THE environment SHALL expose terminal metrics
   (harvest counts, final storage, organ counts, terminal reason) in `infos`.

### Requirement 6 — Legal-action masking

**User Story:** As an RL engineer, I want legal-action masks derived from live
game state, so that the agent never selects illegal actions.

#### Acceptance Criteria

1. THE env wrapper SHALL attach an `action_mask` entry to each agent observation
   computed from the current game state.
2. THE mask SHALL mark exactly the set of legal actions for the acting player,
   accounting for affordability and board geometry.
3. THE RLModule SHALL apply the mask so that masked (illegal) actions cannot be
   sampled or contribute to the policy distribution.
4. WHERE a player's perspective requires board symmetry transforms, THE mask and
   action indices SHALL be transformed consistently so both players share one
   policy.

### Requirement 7 — Observation feature engineering as connectors

**User Story:** As an RL engineer, I want feature engineering to live in RLlib
connectors rather than the engine, so that encodings can change without touching
simulation logic.

#### Acceptance Criteria

1. THE env-to-module connector SHALL build model features from raw observations,
   append the action mask, and write features back into the episode so the replay
   buffer and learner train on exactly what the module saw.
2. IF any built feature is non-finite, THEN THE connector SHALL raise rather than
   silently propagating NaN/Inf.
3. THE connector SHALL support the configured observation history depth.

### Requirement 8 — Local training with Rainbow DQN and SAC

**User Story:** As an RL engineer, I want to run Rainbow DQN or discrete SAC
locally with a single command, so that I can train agents on a workstation.

#### Acceptance Criteria

1. WHEN the developer runs the DQN or SAC train entry point, THEN THE system SHALL
   build the RLlib algorithm from resolved config and run the configured number of
   iterations.
2. THE DQN configuration SHALL support Rainbow components (distributional atoms,
   noisy nets, dueling, double-Q) and a prioritized multi-agent episode replay
   buffer with configurable alpha/beta.
3. THE SAC configuration SHALL target the masked discrete action space and SHALL
   use a size-aware target entropy default rather than RLlib's `"auto"` value,
   which collapses to -1 for any Discrete space.
4. THE system SHALL enforce complete-episode batching, disable fault tolerance so
   any env error stops training, and reject unfinished or non-finite sampled
   episodes.
5. WHERE `replay_buffer_rotation` is false, THE system SHALL use a fixed-replay
   mode that stops environment sampling once the buffer fills and continues
   learning from the stored transitions.
6. THE train entry points SHALL default to zero environment runners for a local
   smoke run and SHALL accept a flag to increase runner count.

### Requirement 9 — Configuration resolution and overrides

**User Story:** As an RL engineer, I want layered, validated configuration, so
that experiments are reproducible and typos fail fast.

#### Acceptance Criteria

1. THE system SHALL load overrides from JSON or YAML and merge them over typed
   defaults.
2. IF an override contains an unknown key or section, THEN THE system SHALL raise
   an error naming the offending key.
3. THE configuration schema SHALL be limited to the sections `env`, `experiment`
   (with nested `runner`/`learner`/`evaluator`), `league_pool`, and exactly one
   algorithm section (`dqn` or `sac`).
4. WHEN an experiment starts, THEN THE system SHALL copy the resolved config into
   the experiment directory for reproducibility.
5. THE SAC preflight CLI SHALL print the fully resolved effective settings and
   label each value's source (config file vs default).

### Requirement 10 — Self-play, frozen opponents, and league pool

**User Story:** As an RL engineer, I want self-play with optional frozen and
league opponents, so that the agent trains against progressively stronger play.

#### Acceptance Criteria

1. BY DEFAULT THE system SHALL use shared-policy self-play mapping both agents to
   one trainable policy.
2. WHEN a frozen opponent is requested, THEN THE system SHALL train only the
   learner policy while player 1 uses a non-trainable opponent policy.
3. WHEN opponent checkpoints are supplied, THEN THE system SHALL load those
   policies' weights into the opponent slots.
4. WHERE the league pool is enabled, THE system SHALL assign one deterministic
   opponent per episode from the pool, promote new checkpoints into a bounded
   pool (evicting oldest), and periodically refresh an opponent slot with current
   learner weights.
5. THE league checkpoint promotion SHALL record the source policy id in a
   manifest so opponents can be loaded without a full algorithm rebuild.

### Requirement 11 — Checkpointing, metrics, and resume

**User Story:** As an RL engineer, I want checkpoints, metrics, and resume, so
that long runs are durable and observable.

#### Acceptance Criteria

1. THE training loop SHALL save a checkpoint at the configured interval and at the
   final iteration into `checkpoint_<iteration>/`.
2. THE training loop SHALL write scalar metrics to TensorBoard event files on each
   iteration.
3. THE system SHALL persist the replay buffer alongside checkpoints and SHALL
   restore it on resume.
4. WHEN resuming from a checkpoint, THEN THE system SHALL derive the starting
   iteration from the checkpoint and continue numbering consistently.

### Requirement 12 — Evaluation and TV replays

**User Story:** As an RL engineer, I want periodic evaluation against a prior
checkpoint with optional recorded play, so that I can judge progress visually.

#### Acceptance Criteria

1. WHERE an evaluation interval is configured, THE system SHALL evaluate the
   current policy against a designated opponent policy before the scheduled
   training iteration.
2. WHERE evaluation-play saving is enabled, THE system SHALL record the evaluation
   episode and write a viewer-format replay into the experiment's replays
   directory.
3. THE evaluation configuration SHALL control number of episodes/runners,
   exploration during evaluation, and the saved-play toggle.

### Requirement 13 — Export a trained bot to CodinGame

**User Story:** As a developer, I want to export a trained network as a single
self-contained CodinGame bot file, so that I can submit it to the puzzle.

#### Acceptance Criteria

1. WHEN the developer runs the export CLI with a checkpoint, THEN THE system SHALL
   produce a single standalone Python bot file that embeds the network weights.
2. THE export SHALL support optional weight quantization (e.g. fp16/int8) and
   SHALL pack the weight blob compactly (compressed and encoded).
3. THE export SHALL verify numerical equivalence between the exported bot and the
   source network over sampled inputs before reporting success.
4. THE exported bot SHALL decode observations and produce legal protocol commands
   using the game's action mapper.

### Requirement 14 — Replay viewing and format conversion

**User Story:** As a developer, I want to visualize replays, so that I can
inspect agent behavior.

#### Acceptance Criteria

1. THE system SHALL convert between CodinGame, core, and viewer replay formats.
2. THE system SHALL provide a standalone viewer plus a runtime-conversion server
   that renders a raw replay without writing an intermediate viewer file.
3. THE viewer SHALL support turn navigation, play/pause, speed control, and
   jump-to-turn.

### Requirement 15 — Engine validation against reference replays

**User Story:** As a developer, I want to validate the engine against reference
replays, so that I can trust simulation correctness.

#### Acceptance Criteria

1. THE validator SHALL replay reference command streams through the engine and
   compare per-turn state (e.g. protein storage) against the reference.
2. WHERE the initial hidden state is unknown, THE validator SHALL infer it (e.g.
   brute-force the initial protein storage) before comparing.
3. WHEN all compared replays match, THEN THE validator SHALL report 100% accuracy;
   otherwise it SHALL report the first diverging turn and field.
4. THE system SHALL be able to generate synthetic reference replays when no real
   replays are available.

### Requirement 16 — Agent-driven workflows (skills) and docs

**User Story:** As an AI coding agent or developer, I want documented workflows
and command references, so that common tasks are executed consistently.

#### Acceptance Criteria

1. THE repository SHALL document end-to-end workflows (new game, run experiment,
   download replays, validate game, tensorboard, delete experiment) as skills.
2. THE run-experiment workflow SHALL require copying `config.yaml.example` to
   `config.yaml`, printing resolved settings, performing safe-start checks on the
   dashboard/trainer, running a smoke iteration, and opening fixed-port monitors.
3. THE safe-start checks SHALL NOT auto-kill a running dashboard or trainer; they
   SHALL warn and refuse to start a conflicting run.
4. THE command references (`AGENTS.md`) SHALL stay consistent with the actual CLI
   and training entry points.

### Requirement 17 — Deferred: offline pretraining and self-play from pretrained

**User Story:** As an RL engineer, I want offline imitation pretraining and the
ability to bootstrap self-play from a pretrained checkpoint, so that training
starts from expert behavior rather than scratch.

#### Acceptance Criteria

1. THE offline adapter SHALL convert core replays into RL transitions suitable for
   offline/imitation learning.
2. WHEN offline pretraining is run, THEN THE system SHALL produce a checkpoint
   loadable by the online self-play trainer.
3. WHEN self-play is started from a pretrained checkpoint, THEN THE system SHALL
   initialize the learner (and optionally opponents) from that checkpoint.
4. These capabilities are currently deferred during the Ray migration; until
   implemented, THE related skills SHALL direct users to the supported
   run-experiment path and SHALL NOT invoke retired trainers.

---

## Non-Functional Requirements

1. **Reproducibility** — Resolved config is copied per experiment; seeds flow
   through the env creator; metrics and checkpoints are durable.
2. **Fail-fast correctness** — Unknown config keys, non-finite features/rewards,
   and unfinished episodes raise rather than corrupt training.
3. **Portability of the exported bot** — The CodinGame bot must be a single file
   with no external dependencies beyond the puzzle's runtime.
4. **Dependency pinning** — The project is pinned to a specific Ray RLlib minor
   version (`ray[default,rllib]>=2.58,<2.59`) due to version-specific workarounds.
5. **Local-only execution** — Training runs locally; TensorBoard reads the Ray
   output directory directly. Remote/cloud trainers are retired.
6. **Separation of concerns** — Engine (simulation), connectors (features),
   mask builder (legality), and action mapper (protocol decoding) remain distinct.
7. **Environment** — Local execution assumes WSL/Linux with bash and a conda env
   named `cellularena`; the env is not assumed pre-activated.
