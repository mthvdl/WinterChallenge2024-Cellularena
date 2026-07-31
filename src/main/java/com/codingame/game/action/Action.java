package com.codingame.game.action;

import com.codingame.game.OrganType;
import com.codingame.game.grid.Coord;
import com.codingame.game.grid.Direction;

public class Action {
    final ActionType type;
    Coord from;
    Integer id;
    Coord to;
    OrganType organType;
    Direction direction;
    private String message;

    public Action(ActionType type) {
        this.type = type;
    }

    public ActionType getType() {
        return type;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public void setCoord(Coord coord) {
        this.to = coord;
    }

    public Coord getTarget() {
        return to;
    }

    public OrganType getOrganType() {
        return organType;
    }

    public Integer getFromId() {
        return id;
    }

    public void setFromId(int id) {
        this.id = id;
    }

    public Direction getDirection() {
        return direction;
    }

}