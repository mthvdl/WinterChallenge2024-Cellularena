package com.codingame.game;

import java.util.ArrayList;
import java.util.List;

import com.codingame.game.grid.Coord;
import com.codingame.game.grid.Direction;

public class Organ {
    static int ENTITY_COUNT = 0;

    int id;
    OrganType type;
    Player owner;
    Organ parent;
    List<Organ> children;
    Direction direction;
    Coord pos;
    int rootId;

    public Organ(Player owner, OrganType type, Direction direction) {
        this.owner = owner;
        this.type = type;
        this.direction = direction;
        this.parent = null;
        this.id = ++ENTITY_COUNT;
        this.children = new ArrayList<>();
        this.rootId = this.id;
    }

    public Player getOwner() {
        return owner;
    }

    public void setPos(Coord pos) {
        this.pos = pos;
    }

    public boolean isHarvester() {
        return getType() == OrganType.HARVESTER;
    }

    public Coord getFacedCoord() {
        return pos.add(direction.coord);
    }

    public boolean isTentacle() {
        return getType() == OrganType.TENTACLE;
    }

    public void setParent(Organ parent) {
        this.parent = parent;
        if (parent.getType() == OrganType.ROOT) {
            this.rootId = parent.id;
        } else {
            this.rootId = parent.getRootId();
        }
    }

    public boolean isNucleus() {
        return getType() == OrganType.ROOT;
    }

    public OrganType getType() {
        return type;
    }

    public int getId() {
        return id;
    }

    public Coord getPos() {
        return pos;
    }

    public Direction getDirection() {
        return direction;
    }

    public int getParentId() {
        if (parent == null) {
            return 0;
        }
        return parent.id;

    }

    public boolean isSporer() {
        return type == OrganType.SPORER;
    }

    public boolean isRoot() {
        return type == OrganType.ROOT;
    }

    public int getRootId() {
        return rootId;
    }
}