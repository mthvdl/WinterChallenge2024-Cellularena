# SAC/DQN Remaining Issues

Reviewed 2026-08-28. Issues are ordered by the sequence in which they should be addressed. Handle one issue at a time: explain the proposed change and wait for approval before editing. Shared behavior should remain consistent between SAC and DQN unless scope is explicitly narrowed.

## Confirmed Bugs

### 5. Resumed training may omit the final checkpoint

`Core.ray_training.train()` compares the absolute iteration number with the number of additional requested iterations. For example, a run resumed at iteration 300 for 20 iterations ends at 320, but 320 is not equal to 20. If the last iteration is outside the checkpoint interval, its final state is not saved.

Intended fix: calculate `final_iteration = start_iteration + iterations`, save at that iteration, and add resumed-loop regression coverage.

### 8. SAC training replays use different environment settings

The training replay callback hard-codes `map_height=8` and omits the resolved width, wall density, protein density, history, reward-shaping, and seed settings. Generated replays may therefore be unrelated to the training distribution.

Intended fix: construct the replay environment from the resolved run settings, use a deterministic replay seed, and label it with the actual experiment name.

### 11. SAC silently ignores `obs_history_steps > 1`

The environment stacks historical grid frames, but the SAC paper feature encoder keeps only the final 17 grid channels. Changing `obs_history_steps` therefore has no effect on SAC input while consuming extra environment work.

Intended fix: initially reject history values other than 1 for SAC, unless temporal SAC support is explicitly requested.

### 15. Replay failures can be reported as successful saves

The recorder catches all exceptions and returns the checkpoint path. The standalone replay command then prints `Replay saved` even when no replay file was created.

Intended fix: return `None` or raise a dedicated replay exception. Training may log and continue; standalone replay generation should exit unsuccessfully.

## League And Evaluation Gaps

### 6. League promotion and sampling are quality-blind

Every checkpoint is promoted and all opponent slots are sampled uniformly. There are no per-opponent games, wins, draws, losses, qualification thresholds, or regression checks. Weak snapshots can displace useful opponents without detection.

Intended fix: add per-opponent outcome metrics first, then configurable promotion criteria and uniform or performance-weighted sampling.

### 9. Resume depends on checkpoint naming and manually matching configuration

SAC derives the starting iteration from a `checkpoint_N` directory name. Renaming the directory breaks parsing, and the caller must manually provide a compatible environment, network, and opponent configuration.

Intended fix: read iteration and saved configuration from checkpoint metadata where available, then validate module IDs and compatibility before restoring.

### 10. Evaluation never swaps player sides

The learner always plays player 0 and the opponent always plays player 1. Perspective normalization reduces observation bias but cannot reveal engine-side or first-player asymmetry.

Intended fix: evaluate paired games on identical seeds with sides swapped and report aggregate and per-side results.

### 12. Training replays evaluate only `opponent_000`

Replay generation always selects the first opponent slot, so it provides no visibility into the rest of the league.

Intended fix: rotate replay opponents or use the league sampler, and include opponent slot and source checkpoint metadata.

## SAC Configuration Risks

### 7. Default target entropy ignores legal-action count

The default target entropy is based on all 4,033 actions, while most states expose far fewer legal actions. This can make the target unattainable and drive excessive entropy-temperature growth. The current local configuration explicitly uses `1.84`, but the generic default remains affected.

Intended fix: use a mask-aware target derived from legal-action counts with a configurable multiplier, while retaining an explicit fixed-target option.

### 13. Configuration lacks semantic range validation

Configuration merging accepts invalid map dimensions, ratios, pool sizes, history values, intervals, and evaluation units. Oversized maps are especially dangerous because observations and action indexing use fixed `12x24` maxima.

Intended fix: validate all semantic ranges before Ray starts and return actionable errors.

### 14. Configured protein density differs from the normal generator distribution

The active configuration uses `protein_ratio: 0.4`, while randomized generation normally caps the ratio at `0.15`. This may be an intentional high-protein curriculum rather than a bug, but it creates a training/deployment distribution difference.

Intended action: document the curriculum explicitly or align the value with the target distribution. Do not change it without approval.

## Deferred Cleanup

- Integrate or remove `IterativeActionRuntime` after runtime/export paths are finalized.
- Remove the empty `CellularenaSACWrapper` if no specialization is planned.
- Replace remaining hard-coded action count `4033` values with `N_ACTIONS`.
- Consider actor-only league snapshots to reduce disk usage.

## Important Constraint

Single-inference iterative root actions are implemented for model-driven replay/runtime inference. The SAC learner was intentionally left unchanged, so RLlib training still uses its scalar-action approximation.
