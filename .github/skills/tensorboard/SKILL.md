---
name: tensorboard
description: "Use when the user wants to view local TensorBoard metrics from a Ray RLlib experiment."
---

# TensorBoard

Ray training writes TensorBoard-compatible event files under the algorithm's
Ray result directory. Remote ACA synchronization is retired with the remote
training workflow.

## Local Experiment

Ask for the result directory if it is not known, then run:

```bash
conda run -n cellularena tensorboard \
    --logdir <RAY_RESULT_DIR> \
    --port 6006
```

For a result tree containing multiple runs, pass the parent directory to
compare them. Open `http://localhost:6006` after TensorBoard starts.

## Checks

- Confirm the directory contains `events.out.tfevents.*` files.
- Use a separate port if `6006` is already occupied.
- Ray reports episode, rollout, and learner metrics as they become available.
