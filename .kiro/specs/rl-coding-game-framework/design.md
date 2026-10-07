# Design — rl_coding_game Framework

## Overview

`rl_coding_game` is a layered reinforcement-learning framework for two-player
CodinGame puzzles. It separates a **game-agnostic core** (`Core/`) from
**per-game packages** (`Games/<GAME>/`). The reference game is Cellularena
(CodinGame Winter Challenge 2024).

The design has four hard boundaries, each owning one concern:

1. **Game engine** (`Games/<GAME>/engine/game.py`) — pure simulation of the
   puzzle protocol. No ML features, no model encodings.
2. **Env + wrapper** (`engine/env.py`, `engine/action_env.py`, `ray/env_wrapper.py`)
   — PettingZoo ParallelEnv exposed to RLlib, adding the legal action mask from
   live game state.
3. **Feature connector** (`Core/ray_connectors.py`, `ray/<algo>/preprocessor.py`)
   — RLlib env-to-module ConnectorV2 that turns raw observations into model
   features and writes them back into the episode.
4. **Action mapper** (`bots/action_mapper.py`, `engine/action_adapter.py`) —
   decodes a model action into legal protocol commands.

Keeping these separate is what makes new games cheap: the engine author only
touches concern (1), and the generic `Core/` plumbing is reused unchanged.

This design maps directly to the requirements:
- Generic core & paths → Req 1
- Scaffold / rules / replays → Req 2, 3
- Engine & env & spaces → Req 4, 5
- Masking & features → Req 6, 7
- Training (DQN/SAC, fixed replay) → Req 8
- Config resolution → Req 9
- Self-play/league → Req 10
- Checkpoint/metrics/resume → Req 11
- Evaluation → Req 12
- Export → Req 13
- Viewer & conversion → Req 14
- Validation → Req 15
- Skills/docs → Req 16
- Deferred offline/pretrained → Req 17

---

## Architecture

```mermaid
graph TD
    subgraph CLI[Core/cli]
        SCAF[scaffold_game]
        RULES[download_rules]
        GAMES[download_games]
        EXPORT[export_to_codingame]
        PRE[preflight_sac]
    end

    subgraph GAME[Games/cellularena]
        ENGINE[engine/game.py<br/>pure simulation]
        ENV[engine/env.py<br/>PettingZoo ParallelEnv]
        AENV[engine/action_env.py<br/>Discrete 4033]
        ADAPT[engine/action_adapter.py<br/>action codec]
        WRAP[ray/env_wrapper.py<br/>+ action_mask]
        PREP[ray/dqn|sac/preprocessor.py]
        NET[ray/dqn|sac/modules.py<br/>masked RLModule]
        GCFG[ray/config.py<br/>+ ray/dqn|sac/config.py]
        TRAIN[ray/dqn|sac/train.py]
        MASK[policy/action_mask.py]
        MAPPER[bots/action_mapper.py]
    end

    subgraph CORE[Core - game-agnostic]
        REG[ray_env.register_env]
        RCFG[ray_config]
        POL[ray_policies]
        LOOP[ray_training.train]
        MET[ray_metrics]
        FIX[fixed_replay]
        STORE[replay_buffer_store]
        LEAGUE[league]
        AMASK[action_mask contract]
        PATHS[project_paths]
    end

    TB[(TensorBoard)]
    CKPT[(experiments/.../checkpoints)]

    ENGINE --> ENV --> AENV --> WRAP
    ADAPT --> AENV
    MASK --> WRAP
    WRAP --> REG
    PREP --> TRAIN
    NET --> GCFG --> TRAIN
    TRAIN --> LOOP
    LOOP --> MET --> TB
    LOOP --> CKPT
    LOOP --> STORE
    POL --> TRAIN
    LEAGUE --> TRAIN
    FIX --> GCFG
    AMASK --> WRAP
    PATHS --> TRAIN
    MAPPER --> EXPORT
```

### Layer responsibilities

| Layer | Modules | Owns |
|---|---|---|
| Core (generic) | `Core/ray_*`, `Core/league.py`, `Core/fixed_replay.py`, `Core/replay_buffer_store.py`, `Core/action_mask.py`, `Core/project_paths.py`, `Core/factory.py`, `Core/cli/*` | RL plumbing reusable across games |
| Game engine | `engine/game.py`, `engine/grid.py`, `engine/organ.py`, `engine/coord.py`, `engine/grid_maker.py`, `engine/replay_loader.py` | Protocol-faithful simulation |
| Game env | `engine/env.py`, `engine/action_env.py`, `engine/action_adapter.py`, `engine/obs/*`, `ray/env_wrapper.py`, `factories.py` | Spaces, masking surface, RLlib adapter |
| Game training | `ray/config.py`, `ray/dqn/*`, `ray/sac/*`, `ray/evaluation.py` | Algorithm config, networks, preprocessors, entry points |
| Game policy/bot | `policy/action_mask.py`, `bots/action_mapper.py`, `offline_replay_adapter.py` | Legality, protocol decoding, offline transitions |
| Viewer | `Viewer/*` | Replay visualization + runtime conversion |

---

## Components and Interfaces

### Core: project paths (Req 1.4)

`Core/project_paths.py` centralizes the game-first layout. `ROOT` is the
`rl_coding_game/` directory. Key functions:

- `shared_replays_dir(game)` → `Games/<game>/experiments/shared/replays`
- `experiment_root(game, algo, exp)` → `.../experiments/<algo>/<exp>`
- `experiment_checkpoints_dir`, `experiment_replays_dir`,
  `experiment_snapshot_dir` (league_pool), `experiment_replay_buffer_path`
- `algorithm_config_example(game, algo)` → `.../experiments/<algo>/config.yaml.example`

All training artifacts resolve through these helpers so paths stay consistent.

### Core: action-mask contract (Req 6)

`Core/action_mask.py` defines the stable keys and default builder:

```python
OBSERVATIONS_KEY = "observations"
ACTION_MASK_KEY  = "action_mask"

def full_action_mask(action_count) -> np.ndarray  # all-ones

class ActionMaskBuilder:
    def build(self, game, player_idx, action_count) -> np.ndarray:  # all legal
```

A new game is immediately runnable (every action legal); it customizes behavior
by subclassing `ActionMaskBuilder`. Cellularena's `policy/action_mask.py`
produces a `Discrete(N_ACTIONS)` mask from live game state (affordability +
geometry) with player-perspective transforms (Req 6.4).

### Core: config resolution (Req 9)

- `Core/ray_config.py` defines frozen dataclasses: `RayRunSettings`,
  `LeaguePoolSettings`, `DQNSettings`; `load_overrides()` (JSON/YAML),
  `settings_dict()` (defaults + overrides, rejects unknown keys),
  `complete_episodes_only()`, and `validate_sampled_episodes()`.
- The game binds the schema in `Games/cellularena/ray/config.py`:
  `resolve_run_and_env_settings()` enforces exactly five top-level sections
  (`env`, `experiment`, `league_pool`, `dqn`, `sac`), the allowed `experiment`
  keys and `runner`/`learner`/`evaluator` subsections, and the game's
  `CellularenaEnvSettings` (map size, ratios, `obs_history_steps`,
  `reward_shaping` default **False**).

`complete_episodes_only()` applies three safeguards (Req 8.4):
`batch_mode="complete_episodes"`, fault tolerance fully disabled, and the
`on_sample_end` validator that rejects unfinished or non-finite episodes.

### Core: policy & self-play (Req 10)

`Core/ray_policies.py`:

- `policy_setup(frozen_opponent, opponent_policy_ids, auxiliary_policy_ids)`
  returns either one `"shared"` policy (both agents mapped to it) or a
  `"learner"` + N `"opponent_NNN"` policies (only learner trainable).
- Mapping functions: `shared_policy_mapping`, `learner_opponent_mapping`,
  `league_policy_mapping()` (deterministic per-episode opponent selection via
  SHA-256 of the episode id).
- `resolve_opponent_modes/ids`, `seed_opponents_from_policy()` (copy learner
  weights to opponent slots), `load_policy_from_checkpoint()` (loads a single
  policy's `RLModule` from `checkpoint/learner_group/learner/rl_module/<id>`,
  reading `league_manifest.json` for the source id).

### Core: league pool (Req 10.4, 10.5)

`Core/league.py`:

- `promote_checkpoint(checkpoint, pool_dir, max_size, source_policy_id)` copies a
  checkpoint into a bounded pool atomically (temp dir + rename), writes
  `league_manifest.json`, and evicts the oldest beyond `max_size`.
- `discover_checkpoints(pool_dir)` (newest first) and
  `latest_checkpoint_before(dir, step)`.

### Core: training loop (Req 11, 12)

`Core/ray_training.py::train()` is algorithm-agnostic:

- Iterates `algorithm.train()` for `iterations`.
- Writes `scalar_metrics(result)` (from `Core/ray_metrics.py`) to a TensorBoard
  `SummaryWriter` each iteration.
- Runs `evaluation_callback` before scheduled eval iterations and
  `checkpoint_callback` after checkpoints.
- Saves checkpoints to `checkpoint_<iteration>/` on interval and at the final
  iteration; persists the replay buffer via `save_replay_buffer`.
- Supports `start_iteration` for resume.

### Core: fixed replay (Req 8.5)

`Core/fixed_replay.py` provides `FixedReplayDQN`/`FixedReplaySAC` via
`_FixedReplayMixin`. Both algorithms share DQN's new-stack training step. When
the buffer's lifetime added timesteps reach capacity, the mixin flips
`_fixed_replay_full` and permanently runs only the replay/learner/prioritization
half, stopping environment sampling. Selected via
`replay_buffer_rotation=false`.

### Core: replay buffer persistence (Req 11.3)

`Core/replay_buffer_store.py::save_replay_buffer/load_replay_buffer` use
`ray.cloudpickle` with atomic replace, plus two RLlib 2.58 `set_state`
workarounds (`sampled_timesteps_per_module` defaultdict fix; rebuilding
`_sample_idx_to_tree_idx`). `Core/ray_env.py::make_multi_agent_replay_buffer()`
returns a `MultiAgentPrioritizedEpisodeReplayBuffer` subclass with a metaclass
`__contains__` hack working around RLlib treating a resolved class as a string.

### Game engine & env (Req 4, 5)

- `engine/game.py` (`Game`, `PlayerState`): `reset()`,
  `step(actions: Dict[int, List[int]]) -> (done, rewards)`,
  `get_observation(player_idx)`, `compute_action_mask(player_idx)`, plus
  replay-ingestion methods (`init_from_global_data`, `set_storage`,
  `parse_raw_command`, `step_replay`, `get_state_snapshot`). Constants:
  `MAX_H=12`, `MAX_W=24`, `N_CHANNELS=17`, `MAX_ROOTS=5`, `MAX_TURNS=100`,
  `ACTIONS_PER_ORG=69`.
- `engine/env.py` (`CellularenaEnv(ParallelEnv)`): two agents, simultaneous
  resolution; Dict observation (`grid`/`storage`/`turn`) built via
  `TemporalObservationBuilder`; native action
  `MultiDiscrete([69]*MAX_ROOTS)`; sparse terminal rewards with optional
  policy-invariant potential-based shaping (`_state_potentials`, zero-sum tanh,
  gamma 0.99, **default True** at this layer); terminal `infos` with harvest
  counts, final storage/organs, terminal reason.
- `engine/action_env.py` (`CellularenaActionEnv`): collapses to
  `Discrete(N_ACTIONS=4033)`; adds `self_player_idx` to obs; decodes via
  `action_adapter.discrete_action_to_slot_actions` + `transform_action_index`;
  `make_action_env(...)` factory with `reward_shaping` **default False**.
- `engine/action_adapter.py`: the discrete action codec — encode/decode between
  index and (channel, coord)/(organ_type, growth_dir, face_dir),
  `build_action_mask`, `transform_action_index/values/mask` (perspective
  symmetry), affordability, `iterative_policy_masking_to_slot_actions`.

> **Reward-shaping default divergence:** shaping defaults to **True** in
> `CellularenaEnv` but **False** in `CellularenaActionEnv`/the Ray wrapper
> (passed via `env_config["reward_shaping"]`). This is intentional and documented
> in the requirements; training should set it explicitly.

### Game RLlib adapter (Req 6, 7)

- `ray/env_wrapper.py` (`CellularenaRayWrapper`): wraps `CellularenaActionEnv`,
  adds `ACTION_MASK_KEY` to each observation from live state, optionally records
  replays (`EpisodeRecorder`), and is wrapped by RLlib
  `ParallelPettingZooEnv`. `make_env_creator()` reads `env_config` (seed,
  `obs_history_steps`, map size, ratios, `reward_shaping`, `record_replay`);
  `register_cellularena_env()` registers under `cellularena_ray`.
- `Core/ray_connectors.py::env_to_module_connector()` + `FeaturePreprocessor`
  base: a `MultiAgentObservationPreprocessor` ConnectorV2 that builds features,
  appends the mask, rejects non-finite features, and writes features back into
  the episode so buffer and learner see exactly the module's input.
- `ray/dqn/modules.py` (`MaskedDQNTorchRLModule`, `DQNNetwork`) and
  `ray/sac/modules.py` (`MaskedSACTorchRLModule`, `CNNSACNetwork`,
  `SACNetwork`) apply the mask inside the RLModule.

### Game training configs (Req 8)

- `ray/dqn/config.py::build_config()`: `DQNConfig` with
  `MaskedDQNTorchRLModule`, torch, Rainbow knobs from `DQNSettings`
  (`num_atoms`, `noisy`, `dueling`, `double_q`, `training_intensity`),
  prioritized multi-agent episode buffer (default alpha 0.6 / beta 0.4,
  batch 32), `DQNPreprocessor` connector, `policy_setup`, evaluation wiring,
  `FixedReplayDQN` when rotation off, finalized by
  `network_factory().customize(complete_episodes_only(config))`.
- `ray/sac/config.py::build_config()`: discrete masked SAC with
  `MaskedSACTorchRLModule` + `CNNSACNetwork`; supports
  `training_intensity/actor_lr/critic_lr/target_entropy/initial_alpha/alpha_lr/replay_type`;
  **size-aware target entropy default `0.5*log(N_ACTIONS)`** replacing RLlib's
  broken `"auto"` (which collapses to -1 for Discrete). `FixedReplaySAC` when
  rotation off.

### Game training entry points (Req 8, 10, 11, 12)

`ray/dqn/train.py` and `ray/sac/train.py` share this flow:

```mermaid
sequenceDiagram
    participant U as User (CLI)
    participant T as train.py main()
    participant C as config resolution
    participant R as Ray/RLlib
    participant L as Core.ray_training.train
    participant F as filesystem

    U->>T: --iterations/--frozen-opponent/--config ...
    T->>F: resolve experiment dirs (project_paths)
    T->>C: load_overrides(config or config.yaml.example)
    T->>F: copy resolved config into experiment root
    T->>C: resolve_run_and_env_settings()
    T->>T: resolve opponent mode (frozen/league/checkpoints)
    T->>R: register_env + ray.init(dashboard)
    T->>R: build_config(...).build_algo()
    T->>R: seed eval/league/opponent policies; load opponent checkpoints
    T->>L: train(algo, iterations, callbacks, replay_buffer_path)
    loop each iteration
        L->>R: (eval callback) evaluate vs prior checkpoint
        L->>R: algorithm.train()
        L->>F: write TensorBoard scalars
        L->>F: checkpoint_<i>/ + replay_buffer.pkl (on interval/final)
        L->>F: (league) promote checkpoint + rotate opponent slot
    end
    T->>R: algorithm.stop(); ray.shutdown()
```

SAC additionally supports `--resume-checkpoint` (restores algo + buffer, derives
`start_iteration`).

### CLI tools (Req 2, 3, 9, 13)

| CLI | Responsibility |
|---|---|
| `Core/cli/scaffold_game.py` | Generate a full `Games/<GAME>/` package from a URL/puzzle id; persist conda env to `env.sh` |
| `Core/cli/download_rules.py` | Download statement as Markdown/HTML/text; public endpoint, optional `CG_SESSION` for gated statements |
| `Core/cli/download_games.py` | Fetch top-player replays via CodinGame services API; `CG_SESSION` or username/password; `--game-id`, `--top`, `--per-player`; convert to core raw |
| `Core/cli/export_to_codingame.py` | Export a trained network as one self-contained bot `.py`; optional fp16/int8 quantization; gzip+base64 blob; verify numerical equivalence |
| `Core/cli/preflight_sac.py` | Print resolved SAC settings with per-value source; refuse to start if dashboard (8265) or matching trainer already running |

### Viewer & conversion (Req 14)

- `replay_transform.py`: CodinGame ↔ core ↔ viewer format conversion.
- `Viewer/`: standalone TS viewer; `Viewer/viewer_server.py` serves the UI and
  converts raw replays to viewer JSON in-memory on request.
- `export_episode_replay.py`: export a self-play episode to a core-raw replay.

### Validation (Req 15)

- `validate_engine.py`: replays reference command streams through the engine and
  compares per-turn protein storage; infers unknown initial storage by
  brute-force (8⁴ combinations); reports 100% or the first diverging turn/field;
  `--loop` re-runs after fixes.
- `generate_test_replay.py`: synthesize reference replays when none are
  downloaded.

---

## Data Models

### Observation (per agent)

```
Dict {
  "grid":    Box(float32, (MAX_H=12, MAX_W=24, N_CHANNELS=17))
             ch0 obstacle; ch1-4 proteins A/B/C/D;
             ch5-9 P0 organ type (ROOT/BASIC/TENTACLE/HARVESTER/SPORER);
             ch10-14 P1 organ type; ch15-16 facing dir per player
  "storage": Box(float32, (2, 4))   # proteins A/B/C/D per player, /50
  "turn":    Box(float32, (1,))     # turn / MAX_TURNS
  # action_env adds:
  "self_player_idx": Box(int32, (1,))
  # ray wrapper adds:
  "action_mask": Box(float32, (N_ACTIONS,))
}
```

With `obs_history_steps > 1`, the `TemporalObservationBuilder` stacks history.

### Action spaces

- Native: `MultiDiscrete([69] * 5)` — per-organism slot.
  - `0` WAIT; `1..64` GROW (`raw=action-1`, `growth_dir=raw//16`,
    `facing_dir=(raw//4)%4`, `type=raw%4`); `65..68` SPORE.
- Paper (training): `Discrete(4033)` — one organism action per step, others WAIT.

### Rewards

Terminal-only base: +1/-1 win/loss, +0.5/-0.5 protein tie-break, 0 true tie.
Optional potential shaping on non-terminal steps:
`r' = r + gamma*phi(s') - phi(s)` with zero-sum bounded `phi` (tanh of organ +
protein deltas).

### Config schema

```yaml
env:            { map_height, map_width, wall_ratio, protein_ratio,
                  obs_history_steps, reward_shaping }
experiment:
  iterations, checkpoint_interval, replay_capacity, replay_buffer_rotation,
  train_batch_size, num_steps_sampled_before_learning_starts, gamma,
  replay_alpha, replay_beta
  runner:     { num_env_runners, num_cpus_per_env_runner }
  learner:    { num_cpus_for_main_process, num_gpus }
  evaluator:  { evaluation_interval, evaluation_num_env_runners,
                evaluation_duration, evaluation_duration_unit,
                evaluation_explore, save_evaluation_play }
league_pool:  { enabled, max_size }
dqn:          { num_atoms, noisy, dueling, double_q, training_intensity }   # or
sac:          { training_intensity, actor_lr, critic_lr, target_entropy,
                initial_alpha, alpha_lr, replay_type }
```

Unknown keys or sections raise (fail-fast).

### Experiment layout on disk

```
Games/<game>/experiments/
├── shared/replays/                         # curated/downloaded replays
└── <algorithm>/
    ├── config.yaml.example
    └── <experiment>/
        ├── config.yaml                      # resolved config copy
        ├── checkpoints/checkpoint_<i>/
        ├── league_pool/<checkpoint>/league_manifest.json
        ├── replays/                         # eval TV replays
        ├── replay_buffer.pkl
        └── tensorboard/
```

---

## Error Handling

| Condition | Behavior | Req |
|---|---|---|
| Unknown config key/section | Raise naming the key | 9.2 |
| Non-finite feature in connector | Raise | 7.2 |
| Unfinished / non-finite sampled episode | Raise via `on_sample_end` | 8.4 |
| Any env-runner / sub-env error | Stop training (fault tolerance disabled) | 8.4 |
| `replay_capacity < 1` with fixed replay | Raise | 8.5 |
| Opponent checkpoints exceed policy slots | Raise | 10.3 |
| Missing/invalid CG credentials on gated request | Clear error, no partial save | 3.5 |
| Dashboard/trainer already running (SAC preflight) | Refuse, do not auto-kill | 9.5 / 16.3 |
| Export numerical mismatch | Report failure before success | 13.3 |
| Validation divergence | Report first diverging turn/field | 15.3 |

---

## Testing Strategy

Existing coverage (keep green):

- `Core/tests/`: `test_ray_config.py`, `test_ray_policies.py`,
  `test_ray_training.py`, `test_ray_metrics.py`, `test_league.py`,
  `test_fixed_replay.py`, `test_replay_buffer.py`,
  `test_replay_buffer_store.py`, `test_dqn_config.py`, `test_sac_config.py`.
- `Games/cellularena/ray/tests/test_config.py`,
  `ray/sac/test_modules.py`.
- `Games/cellularena/engine/tests/`: env compiles + random episode terminates;
  replay infra.

Validation strategy:

- Engine correctness via `validate_engine.py` against synthetic/real replays
  (target: 100%).
- Local smoke training: `--iterations 1 --num-env-runners 0` for both DQN and
  SAC before scaling runners.

Testing principles:

- Core tests must not import a specific game (Req 1).
- Config tests assert fail-fast on unknown keys and correct section split.
- Policy tests assert mapping determinism and weight-seeding/loading.
- Fixed-replay tests assert sampling stops at capacity and learning continues.

---

## Key Design Decisions & Trade-offs

1. **Two action representations.** Native `MultiDiscrete` mirrors the protocol;
   the collapsed `Discrete(4033)` "paper" head is what RLlib trains on. One
   discrete action per step keeps the policy head tractable at the cost of
   multiple steps to move several organisms.
2. **Shared training step for DQN and SAC.** Both use DQN's new-stack step via
   the fixed-replay mixin, reducing bespoke code at the cost of coupling SAC's
   fixed-replay behavior to DQN internals.
3. **Pinned RLlib (`>=2.58,<2.59`).** Several targeted workarounds (replay buffer
   metaclass, `set_state` fixes, target-entropy override) depend on this exact
   minor; upgrading requires re-validating them.
4. **Reward-shaping default divergence** between env layers is deliberate;
   training sets it explicitly via config, keeping raw-engine semantics intact.
5. **Local-only execution.** Simpler and reproducible; remote/cloud trainers and
   the legacy custom PPO/DQN/ACA paths are retired.
6. **Deferred offline/pretrained paths.** The offline adapter and scaffolding
   exist, but the online bootstrap-from-checkpoint and offline-pretrain trainers
   are not yet wired; skills route users to `run-experiment` until then.
