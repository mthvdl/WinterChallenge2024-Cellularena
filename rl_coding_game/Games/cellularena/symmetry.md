# Cellularena Symmetry Contract

This file is the canonical contract for player-relative transforms used by
map generation, replay conversion, self-play, inference, and observation
feature builders.

## Coordinate transform

The raw board uses `x` increasing left to right and `y` increasing top to
bottom. Player 1 is the left-right reflection of player 0:

```text
x' = width - 1 - x
y' = y
```

This is a reflection across the vertical axis. Do not reverse the `y` axis.

## Direction transform

Under the left-right reflection, directions map as follows:

```text
N -> N
E -> W
S -> S
W -> E
```

## Player-indexed data

When constructing a player-relative observation, swap player 0 and player 1
organ channels and storage rows after applying the spatial transform. Actions
remain expressed in the transformed player's local perspective. Raw engine
state and protocol replay coordinates remain unchanged.
