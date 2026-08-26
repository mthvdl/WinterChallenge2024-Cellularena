---
name: delete-experiment
description: "Use when the user asks to delete, remove, clean up, purge, or reset a local Ray experiment folder."
---

# Delete Experiment

This workflow is local-only. Remote ACA experiment cleanup is retired.

## Confirm

Ask the user to confirm the exact local experiment path before deleting it.
Do not delete the reserved offline seed or unrelated experiments.

## Stop Training

From the repository root, inspect matching Ray processes:

```bash
pgrep -af 'Games\.<GAME>\.ray\.(dqn|sac)\.train' || true
```

Stop only the confirmed experiment process. Prefer a targeted process stop;
never use a broad kill pattern when other training runs are active.

## Delete

After confirmation and once training has stopped:

```bash
test -d <EXPERIMENT_DIR> && rm -rf -- <EXPERIMENT_DIR>
test ! -e <EXPERIMENT_DIR>
```

The path may be a game experiment directory under
`rl_coding_game/Games/<GAME>/experiments/` or a Ray result/checkpoint directory
explicitly supplied by the user.

## Verify

Confirm the directory is absent and that no matching Ray trainer remains:

```bash
test ! -e <EXPERIMENT_DIR>
pgrep -af 'Games\.<GAME>\.ray\.(dqn|sac)\.train' || true
```
