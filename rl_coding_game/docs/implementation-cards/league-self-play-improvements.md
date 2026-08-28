# League Self-Play Improvements

**Status:** Deferred
**Scope:** Improve the current checkpoint-based league pool without changing the default shared-policy training mode.

## Current baseline

The current system supports:

- Shared-policy self-play for a new experiment without a league pool.
- Frozen learner-versus-opponent training from historical checkpoints.
- Bounded immutable pool entries with source-policy metadata.
- Deterministic episode-level opponent selection.
- Aggregate evaluation across the selected opponent pool.

Keep this baseline simple until a longer training run demonstrates that league self-play is useful for Cellularena.

## Possible improvements

- [ ] Add per-opponent evaluation runs and metrics instead of reporting only an aggregate score.
- [ ] Store win-rate results between each learner and each pool entry in an evaluation matrix.
- [ ] Replace uniform or deterministic pool selection with prioritized fictitious self-play (PFSP), favoring opponents that are difficult but still beatable.
- [ ] Add Elo or TrueSkill ratings to pool metadata and use them to maintain behavioral diversity.
- [ ] Add one or more exploiter policies that search for weaknesses in the main learner without replacing the main league policy.
- [ ] Store normalized league snapshots containing only the selected policy weights, rather than copying the complete training checkpoint.
- [ ] Add checkpoint compatibility metadata for algorithm, observation contract, action space, and network version.
- [ ] Add a multi-generation integration test covering shared bootstrap, frozen training, promotion, discovery, and the next league run.
- [ ] Add retention rules that preserve strategically diverse checkpoints instead of keeping only the newest entries.

## Recommended order

1. Add per-opponent evaluation and a small evaluation matrix.
2. Use those results to implement PFSP sampling.
3. Add Elo or TrueSkill only if the matrix becomes difficult to manage.
4. Add exploiter policies after the main learner has a stable evaluation baseline.
5. Normalize league snapshots when checkpoint size or compatibility becomes a practical problem.

## Acceptance checks

- A disabled league pool leaves normal shared-policy experiments unaffected.
- A learner can train for multiple generations against historical opponents.
- Each pool entry is immutable and can be loaded independently.
- Evaluation identifies which opponents expose weaknesses in the learner.
- Opponent sampling increases training exposure to those weaknesses without collapsing diversity.
