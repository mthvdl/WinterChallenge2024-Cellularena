# Verify game rules and semantics before reasoning about them

Never assume how a game, environment, or system behaves. Read the authoritative
source first, then reason.

## Always read the rules before making claims
- Before asserting anything about game mechanics, episode end conditions,
  rewards, scoring, or state transitions, read the actual rules
  (`Games/<GAME>/rules.md`) and the engine code that implements them.
- Do not infer behavior from framework conventions (RLlib / Gymnasium /
  PettingZoo defaults) and present it as fact about this game. The game's own
  rules take precedence over generic ML/RL conventions.
- If a claim cannot be grounded in a file I have read or a command I have run,
  state it as an open question, not a fact.

## Specific lesson: termination vs. truncation
- In Cellularena the game **ends at turn 100 by rule**
  ("Le jeu se termine quand il détecte qu'aucun progrès ne peut plus être fait
  ou après 100 tours."). The 100-turn limit is a genuine terminal condition,
  **not** an artificial truncation imposed by the training harness.
- Therefore reaching the turn limit is correctly reported as
  `terminated = True`, `truncated = False`, and the learner must **not**
  bootstrap `gamma * Q(s')` on that final step. The current `env.py` behavior
  (`terminations = {done}`, `truncations = {False}`) is correct — do not
  "fix" it to use truncation.
- Only treat an episode end as truncation when the environment cut the episode
  short before a rule-defined end (which does not happen here).

## Specific lesson: sparse reward and the replay buffer
- With sparse rewards, intermediate transitions stored in the replay buffer
  legitimately have `reward = 0.0`. This is correct and expected; the buffer
  stores raw transitions `(s, a, r, s')`, not pre-backtracked values.
- Backward propagation of the terminal reward happens at **learning time** via
  the Bellman target `r + gamma * (1 - done) * Q(s', a')`, not by storing
  nonzero rewards in the buffer. A buffer of zero intermediate rewards is not a
  bug.
