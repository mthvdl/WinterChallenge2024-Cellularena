---
name: offline-training
description: "Use when the user asks about offline pretraining or seeding a Ray replay store from expert games."
---

# Offline Training

Offline pretraining is deferred during the Ray migration. The current supported
workflow is local online Ray RLlib training through the `run-experiment` skill.

Do not invoke the retired custom replay-buffer or trainer commands. Resume this
skill only after a Ray-compatible offline input pipeline is implemented and
validated.
