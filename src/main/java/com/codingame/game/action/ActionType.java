package com.codingame.game.action;

import java.util.function.BiConsumer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.codingame.game.OrganType;
import com.codingame.game.grid.Coord;
import com.codingame.game.grid.Direction;

public enum ActionType {

    GROWTH(
        "^(GROW(?:TH)?) (?<fromId>-?\\d+) (?<targetX>-?\\d+) (?<targetY>-?\\d+) (?<type>\\w+)(?: (?<direction>N|E|W|S|n|e|w|s))?(?: (?<message>.*))?",
        (match, action) -> {
            action.id = Integer.valueOf(match.group("fromId"));
            action.setCoord(
                new Coord(Integer.valueOf(match.group("targetX")), Integer.valueOf(match.group("targetY")))
            );

            //hack
            String typeGroup = match.group("type");
            if (typeGroup.equalsIgnoreCase("nucleus")) {
                typeGroup = "root";
            }

            try {
                action.organType = OrganType.valueOf(match.group("type"));
            } catch (IllegalArgumentException e) {
                throw new RuntimeException("<type> must be a valid organ type. Recieved: " + match.group("type"));
            }
            String dir = match.group("direction");
            action.direction = dir == null ? Direction.NORTH : Direction.fromAlias(dir.toUpperCase());
            action.setMessage(match.group("message"));
        }
    ),
    SPORE(
        "^(SPORE?) (?<fromId>-?\\d+) (?<targetX>-?\\d+) (?<targetY>-?\\d+)(?: (?<message>.*))?",
        (match, action) -> {
            action.id = Integer.valueOf(match.group("fromId"));
            action.setCoord(
                new Coord(Integer.valueOf(match.group("targetX")), Integer.valueOf(match.group("targetY")))
            );

            action.organType = OrganType.ROOT;
            action.direction = Direction.NORTH;
            action.setMessage(match.group("message"));
        }
    ),
    WAIT(
        "^WAIT(?: (?<message>.*))?",
        (match, action) -> {
            action.setMessage(match.group("message"));
        }
    );

    private Pattern pattern;
    private BiConsumer<Matcher, Action> consumer;

    private static void doNothing(Matcher m, Action a) {
    }

    ActionType(String pattern, BiConsumer<Matcher, Action> consumer) {
        this.pattern = Pattern.compile(pattern);
        this.consumer = consumer;
    }

    public Pattern getPattern() {
        return pattern;
    }

    public BiConsumer<Matcher, Action> getConsumer() {
        return consumer;
    }

}
