---
name: run-experiment
description: "Use when the user asks to start, resume, or launch local Ray RLlib Rainbow DQN or SAC training for a game."
---

# Run Experiment

Use the local Ray RLlib entry point for self-play training. Remote ACA
training and the legacy custom PPO/DQN trainers are retired.

## Choose an Algorithm

Ask which algorithm the user wants if it was not specified:

- Rainbow DQN for discrete action spaces
- SAC for continuous action spaces, or a game-provided SAC action adapter

## Collect Inputs

- Game (default: `cellularena`)
- Algorithm (`dqn` or `sac`)
- Iterations (default: `1` for a smoke run)
- Rollout workers (default: `0`; use `1` after the local smoke test)
- Optional JSON/YAML config override file
- Optional frozen opponent and checkpoint path
- Optional checkpoint output directory

## Run Locally

Run from `rl_coding_game` with the project conda environment:

```bash
conda run -n cellularena python -m Games.<GAME>.ray.<ALGORITHM>.train \
    --iterations <ITERATIONS> \
    --num-env-runners <NUM_ENV_RUNNERS> \
    --config <CONFIG.json-or-yaml> \
    --checkpoint-dir <CHECKPOINT_DIR>
```

For Cellularena, the concrete smoke commands are:

```bash
conda run -n cellularena python -m Games.cellularena.ray.dqn.train \
    --iterations 1 --num-env-runners 0

conda run -n cellularena python -m Games.cellularena.ray.sac.train \
    --iterations 1 --num-env-runners 0
```

Use `--frozen-opponent --opponent-checkpoint <PATH>` when loading an opponent
policy from a compatible Ray checkpoint.

## Config Overrides

Configuration files contain a `run` section and one algorithm section:

```yaml
run:
  map_height: 8
  num_env_runners: 1
dqn:
  train_batch_size: 64
  replay_capacity: 20000
```

Use `sac` instead of `dqn` for SAC-specific settings. Explicit CLI flags take
precedence over values in the config file.

## Validation

Before a longer run, confirm the entry point parses and run one iteration with
`--num-env-runners 0`. Then repeat with one worker. Check that the result has a
training iteration and sampled environment steps, and that the checkpoint path
is printed when `--checkpoint-dir` is supplied.
