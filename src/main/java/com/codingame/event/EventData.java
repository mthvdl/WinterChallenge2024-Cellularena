package com.codingame.event;

import java.util.List;

import com.codingame.game.OrganType;
import com.codingame.game.grid.Coord;
import com.codingame.game.grid.Direction;

public class EventData {
    public static final int GROW = 0;
    public static final int SPORE = 1;
    public static final int ATTACK = 2;
    public static final int DEATH = 3;

    public static final int HARVEST = 5;
    public static final int ABSORB = 6;
    public static final int CRASH = 7;
    public static final int SPAWN_NUCLEUS = 8;
    

    public int type;
    public AnimationData animData;
    
    public Integer playerIdx, id;
    public Coord coord, target;
    public OrganType organType;
    public Direction direction;
    public List<Coord> growFrom;

    public EventData() {

    }

}
