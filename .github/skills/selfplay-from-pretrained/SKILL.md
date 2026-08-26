---
name: selfplay-from-pretrained
description: "Use when the user asks to start Ray self-play from an offline-trained or pretrained checkpoint."
---

# Self-Play From Pretrained

Bootstrapping self-play from an offline-trained checkpoint is deferred until
Ray-compatible offline input and checkpoint-transfer workflows are validated.

For ordinary local Ray self-play, use the `run-experiment` skill with the
trainable-versus-frozen policy options and a compatible Ray checkpoint.
Do not use the retired custom PPO/DQN or ACA commands.
