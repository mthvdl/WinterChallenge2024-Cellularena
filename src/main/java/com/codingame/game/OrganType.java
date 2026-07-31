package com.codingame.game;

public enum OrganType {
    ROOT(new int[] { 1, 1, 1, 1 }),
    BASIC(new int[] { 1, 0, 0, 0 }),
    TENTACLE(new int[] { 0, 1, 1, 0 }),
    HARVESTER(new int[] { 0, 0, 1, 1 }),
    SPORER(new int[] { 0, 1, 0, 1 });

    private int[] cost;

    private OrganType(int[] cost) {
        this.cost = cost;
    }

    public int[] getCost() {
        return cost;
    }

    public int getIndex() {
        return this.ordinal();
    }
}
