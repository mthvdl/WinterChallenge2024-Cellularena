# Ray RLlib Rainbow DQN, SAC, and Self-Play

**Status:** Ray-only migration complete; algorithm-specific extensions remain deferred
**Scope:** Make every newly scaffolded game Ray-ready for Rainbow DQN and SAC, replacing the custom RL training framework with Ray RLlib while retaining the game engine and game-specific adapters.

## Goal

Use Ray RLlib as the sole training, rollout, checkpointing, evaluation, and self-play orchestration framework. The supported algorithms are Rainbow DQN and SAC; other algorithms are out of scope. After creating a game, the scaffold should already contain runnable Ray training entry points and explicit customization hooks for observations, wrappers, action masks, policies, hyperparameters, and self-play. Confirm the stock algorithms first, then fill in game-specific behavior through those hooks.

The Cellularena engine, PettingZoo environment behavior, replay format, viewer, and CodingGame export remain in place. The existing custom PPO and DQN/Rainbow trainers, bots, networks, buffers, logging, and league-training machinery become legacy code and should be removed after equivalent Ray paths are validated. Neither custom PPO nor custom DQN/Rainbow is a supported algorithm implementation in the replacement framework.

TensorBoard remains part of the training workflow. Ray Tune/RLlib supplies metric reporting and TensorBoard-compatible event output; the project keeps TensorBoard installed and retains a simple command to inspect each experiment's metrics.

The existing remote deployment and remote training feature is out of scope for the final architecture and should be completely removed after migration validation. Local Ray training, local TensorBoard, the game engine, replay tooling, viewer, and CodingGame export remain supported.

## Decision

The shared environment boundary, stock RLlib validation, local training loop,
checkpoint loading, metrics, and league policy selection are implemented. The
legacy custom trainers and remote deployment have been removed. Custom modules,
mirroring, and offline-data migration remain deferred extensions.

## Definition of ready

Running the game scaffold should provide, without manually wiring Ray internals:

- A registered Ray environment factory that creates a fresh game environment.
- A game-specific wrapper with raw-to-agent observation transformation hooks.
- A declared transformed observation space matching the wrapper output.
- An action-mask hook, with the mask included in the RLlib observation contract.
- A default Rainbow DQN configuration with documented, easy-to-edit hyperparameters.
- A default SAC configuration with documented, easy-to-edit hyperparameters.
- A multi-agent policy configuration supporting shared weights or learner-versus-frozen opponent modes.
- Checkpoint save and restore paths, evaluation, and a short end-to-end smoke command.
- Clear extension points for a custom RLlib `RLModule`, CNN, or mapper.

## Implementation sequence

- [x] Add Ray/RLlib to the shared conda environment and dependency documentation.
- [x] Review all existing repository skills and update, split, or retire instructions that assume the custom PPO/DQN framework; ensure training, setup, TensorBoard, validation, deployment, and experiment-cleanup workflows match the Ray structure.
- [x] Update game scaffolding so a new game generates a Ray environment wrapper.
- [x] Create a fresh-environment factory around `make_action_env()`.
- [x] Add a PettingZoo parallel observation wrapper and registration helper.
- [x] Give the wrapper explicit `transform_observation()` and `observation_space()` hooks.
- [x] Give the wrapper an explicit `action_mask()` hook and return masks in observations.
- [x] Start with a simple transformed observation, using a flattened `Box` with the action mask appended.
- [x] Run stock RLlib Rainbow DQN with `num_env_runners=0` and a short smoke run.
- [x] Run stock RLlib SAC with `num_env_runners=0` and a short smoke run.
- [x] Increase rollout workers after the local smoke test passes.
- [x] Add a centralized Ray hyperparameter configuration with CLI or YAML overrides.
- [x] Keep Rainbow DQN and SAC hyperparameters in separate algorithm-specific sections.
- [x] Verify each generated game's action space against both algorithms; add an explicit SAC action adapter when the native space is unsupported.
- [x] Add default shared-policy and trainable-versus-frozen policy configurations.
- [ ] Add game-specific player-perspective mirroring and verify both players receive canonical observations (deferred; not part of the generic Ray scaffold).
- [ ] Mask invalid logits using an RLlib connector or custom `RLModule` (deferred until the algorithm-specific RLModules replace the stock flat-observation path).
- [x] Configure two policy IDs: a trainable learner and a frozen opponent.
- [x] Load the frozen policy from a checkpoint and keep only the learner in `policies_to_train`.
- [x] Add deterministic episode-level opponent selection for league self-play.
- [ ] Port `CellularenaObsMapper` and the game-specific network into custom RLlib `RLModule` implementations for Rainbow DQN and SAC after the stock algorithms work.
- [ ] Port checkpoint replay generation and experiment directory conventions.
- [x] Configure stable Ray metric reporting and TensorBoard-compatible output.
- [x] Preserve a project TensorBoard command that opens local Ray experiment results.
- [x] Decide that offline pretraining is not required for the supported Ray-only workflow.
- [ ] Compare Ray training against the current reference runs before deleting the custom framework.
- [x] Remove the custom PPO and DQN/Rainbow algorithms and their dedicated trainers, bots, networks, buffers, and CLIs after Ray replacements are validated.
- [x] Remove or archive remaining custom `Core` training code after all required workflows have Ray replacements.
- [x] Verify that no custom PPO or DQN/Rainbow training entry point or algorithm dependency remains in the Ray-only framework.
- [x] Remove the existing remote deployment and remote training implementation, including its scripts, infrastructure helpers, container/deployment configuration, and remote-training entry points.
- [x] Update or retire remote deployment, Azure training, and remote TensorBoard skills and documentation.
- [x] Remove obsolete remote environment variables, deployment-only dependencies, and experiment paths after confirming they are not needed by local Ray workflows.
- [x] Verify that the final project has no supported remote deployment workflow and documents local Ray execution as the supported path.

## Scaffold layout

The repository should have a clean ownership boundary:

```text
rl_coding_game/Core/                 # reusable Ray framework only
    ray_env.py                       # registration and environment factory helpers
    ray_config.py                    # shared RLlib configuration helpers
    ray_policies.py                  # generic policy mapping and frozen-policy helpers
    ray_training.py                  # generic train/evaluate/checkpoint loop
    ray_metrics.py                   # Ray Tune reporting and TensorBoard integration
    ray_algorithms/
        dqn/                          # shared Rainbow DQN configuration/helpers
            config.py                 # reusable DQN configuration helpers
        sac/                          # shared SAC configuration/helpers
            config.py                 # reusable SAC configuration helpers

rl_coding_game/Games/<game>/         # game-specific code and customization
    ray/
        env_wrapper.py               # observation transform, mirroring, action mask
        policies.py                   # game policy mappings and opponent selection
        dqn/
            config.py                 # game-specific Rainbow DQN hyperparameters
            train.py                  # game-specific Rainbow DQN entry point
            modules.py                # optional custom DQN RLModule/network
        sac/
            config.py                 # game-specific SAC hyperparameters
            train.py                  # game-specific SAC entry point
            modules.py                # optional custom SAC RLModule/network
        smoke_test.py                # game-specific end-to-end checks
```

Separate folders do not imply that every algorithm needs a custom class immediately. The initial scaffold should configure RLlib's built-in Rainbow DQN and SAC implementations directly. Add a game-specific `RLModule`, encoder, action distribution, learner, or connector only when the default RLlib component cannot express the required behavior.

Expected class ownership:

- `Core/ray_algorithms/dqn/`: reusable DQN configuration and generic helpers.
- `Core/ray_algorithms/sac/`: reusable SAC configuration and generic helpers.
- `Games/<game>/ray/dqn/modules.py`: optional game-specific DQN module/network.
- `Games/<game>/ray/sac/modules.py`: optional game-specific SAC module/network.
- `Games/<game>/ray/env_wrapper.py`: game observation shaping, mirroring, and action masking shared by both algorithms.

The generated files should use the game's factory and spaces rather than hard-code Cellularena dimensions or action counts. Cellularena can then customize its own mapper, network, and action encoding without becoming the template for every future game. Game code must not import another game's wrapper, mapper, network, or action adapter.

## Ray wiring

The training entry point should register a factory before building the algorithm:

```python
from ray.tune.registry import register_env
from ray.rllib.env.wrappers.pettingzoo_env import ParallelPettingZooEnv


def env_creator(env_config):
    base_env = make_action_env(
        map_height=env_config.get("map_height", 8),
        obs_history_steps=env_config.get("obs_history_steps", 1),
    )
    return ParallelPettingZooEnv(RayCellularenaWrapper(base_env))


register_env("cellularena_ray", env_creator)
```

Use the registered name in the selected `DQNConfig` or `SACConfig`. The factory must construct a new environment for every Ray worker.

## Algorithm boundary

Rainbow DQN is the primary fit for Cellularena's discrete action representation. SAC must be validated against each generated game's action space; if the native space is unsupported by RLlib SAC, the scaffold should fail clearly or provide a documented SAC-specific adapter. Do not silently substitute another algorithm.

## Observation contract

The wrapper's `observation_space(agent)` must exactly describe the transformed value returned by `reset()` and `step()`.

Recommended eventual output:

```python
{
    "obs": transformed_observation,
    "action_mask": legal_action_mask,
}
```

The current `env.action_mask(agent)` method is not sufficient by itself for RLlib; the mask must be forwarded through the observation or an RLlib connector/module.

## Shared versus frozen policies

Shared-policy self-play maps both players to one policy ID. A trainable-versus-frozen match maps them separately:

```text
player_0 -> learner_policy
player_1 -> frozen_policy
```

Configure `policies_to_train=["learner_policy"]`. The frozen policy may be initialized from a checkpoint and must not be mapped to the trainable policy ID.

## Acceptance checks

- The registered environment can reset and step through a complete episode.
- Short stock Rainbow DQN and SAC runs complete without NaNs, space mismatches, or worker errors.
- Checkpoints for both algorithms are produced and can be restored.
- TensorBoard opens the Ray output directory and shows episode, loss, and evaluation metrics.
- With two policy IDs, learner weights change while frozen opponent weights remain unchanged.
- Mirroring is invariant: equivalent states seen by either player produce equivalent canonical observations.
- Action sampling never selects an action marked illegal by the mask.
