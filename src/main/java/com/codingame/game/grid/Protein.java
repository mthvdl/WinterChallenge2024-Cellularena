package com.codingame.game.grid;

public enum Protein {
    A, B, C, D;

    public static Protein fromIndex(int idx) {
        return values()[idx];
    }

    public int getIndex() {
        return this.ordinal();
    }
}
