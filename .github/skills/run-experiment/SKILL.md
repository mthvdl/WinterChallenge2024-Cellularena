---
name: run-experiment
description: "Use when the user asks to start, resume, or launch local Ray RLlib Rainbow DQN or SAC training for a game."
---

# Run Experiment

Use the local Ray RLlib entry point for self-play training. Remote ACA
training and the legacy custom PPO/DQN trainers are retired. Cellularena DQN
and SAC use the RLlib new stack with separate evaluation workers and masked
discrete actions.

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
- Optional experiment name

Before launching any run, look for a real game config at
`rl_coding_game/Games/<GAME>/experiments/<ALGORITHM>/config.yaml`. If it does not exist,
create it by copying the nearby `config.yaml.example`, then use the created
`config.yaml` as the runtime config. Do not run directly from the example file.
Review the copied values before launching and make any required game-specific
adjustments. Explicit CLI flags take precedence over values in the config.

Before launching, display the effective settings that will be used. Include
the game, algorithm, config path, experiment name, iteration count, number of
environment runners, GPU count, evaluation settings, and every algorithm
parameter. For each value, identify whether it came from the YAML/JSON file,
an explicit CLI flag, or the algorithm's framework default. Do not report only
the contents of the config file: values omitted from the file must be shown
with their resolved RLlib defaults. For Cellularena, verify the resolved SAC
settings with the same `build_config(overrides=load_overrides(...))` path used
by the trainer, and print the resolved DQN settings from its `build_config`
path before starting Ray.

Before starting the trainer, perform safe-start checks for both an existing Ray
Dashboard and an existing process for the same game and algorithm. If the Ray
Dashboard is already listening on `127.0.0.1:8265`, report the owning process
and do not start Ray on another port. If a matching trainer is running, report
its PID and do not launch another experiment. Never kill existing processes
automatically. For Cellularena, use:

```bash
ss -ltnp '( sport = :8265 )'
pgrep -af 'python -m Games\.cellularena\.ray\.<ALGORITHM>\.train'
```

Continue only when port `8265` is free and no matching trainer is running.

## Run Locally

Run from `rl_coding_game` with the project conda environment:

```bash
conda run -n cellularena python -m Games.<GAME>.ray.<ALGORITHM>.train \
    --iterations <ITERATIONS> \
    --num-env-runners <NUM_ENV_RUNNERS> \
    --config <CONFIG.json-or-yaml> \
  --experiment-name <EXPERIMENT_NAME>
```

When the real config is missing, create it first and pass that path explicitly:

```bash
cp rl_coding_game/Games/<GAME>/experiments/<ALGORITHM>/config.yaml.example \
   rl_coding_game/Games/<GAME>/experiments/<ALGORITHM>/config.yaml
conda run -n cellularena python -m Games.<GAME>.ray.<ALGORITHM>.train \
  --config Games/<GAME>/experiments/<ALGORITHM>/config.yaml \
  --experiment-name <EXPERIMENT_NAME>
```

For Cellularena, the concrete smoke commands, after creating the runtime
config when needed, are:

```bash
conda run -n cellularena python -m Games.cellularena.ray.dqn.train \
  --iterations 1 --num-env-runners 0 \
  --config Games/cellularena/experiments/dqn/config.yaml

conda run -n cellularena python -m Games.cellularena.ray.sac.train \
  --iterations 1 --num-env-runners 0 \
  --config Games/cellularena/experiments/sac/config.yaml
```

Use `--frozen-opponent --opponent-checkpoint <PATH>` when loading an opponent
policy from a compatible Ray checkpoint.

## Config Overrides

Configuration files contain a `run` section, a `league_pool` section, and one
algorithm section:

```yaml
run:
  map_height: 8
  iterations: 20
  checkpoint_interval: 5
  replay_interval: 5
  num_env_runners: 1
league_pool:
  enabled: false
  max_size: 8
dqn:
  train_batch_size: 64
  replay_capacity: 20000
```

Use `sac` instead of `dqn` for SAC-specific settings. Explicit CLI flags take
precedence over values in the config file.

Set `run.iterations` in the config to control the training length. An explicit
`--iterations` flag overrides the config value.

Set `run.checkpoint_interval` and `run.replay_interval` to positive iteration
counts to control periodic artifact creation. `0` disables periodic replay and
keeps the final checkpoint save. Checkpoints and replays are written under the
derived experiment directories.

At each checkpoint interval, the learner checkpoint is promoted into the
experiment's bounded `league_pool` (controlled by `league_pool.max_size`, only
when `league_pool.enabled` is `true`). A frozen-opponent run without explicit
`--opponent-checkpoint` values discovers the newest checkpoints from previous
experiments of the same algorithm and loads them as separate frozen opponent
policies. A first league run therefore requires one learner run to seed the
pool.

For Cellularena, the checked-in examples are CPU profiles: an 8x16 map, one
environment runner, no GPU, batch size 32, and a low discrete-SAC entropy
target suitable for the masked 4033-action policy. Copy it to `config.yaml`
and adjust it after reviewing the game-specific action mask and available CPU
resources. Runtime artifacts are always placed under
`Games/<GAME>/experiments/<ALGORITHM>/<EXPERIMENT_NAME>/` in `checkpoints`,
`league_pool`, and `replays`; paths are not configuration settings.

## Validation

Before a longer run, confirm the entry point parses and run one iteration with
`--num-env-runners 0`. Then repeat with one worker. Check that the result has a
training iteration and sampled environment steps, and that the checkpoint path
is written below the experiment's `checkpoints` directory.
