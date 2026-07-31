package com.codingame.game;

import com.codingame.game.action.Action;

public record Growth(
    Player player,
    Action action,
    boolean isSpore
) {
}
