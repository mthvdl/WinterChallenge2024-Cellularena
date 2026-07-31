package com.codingame.game;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import com.codingame.event.EventData;
import com.codingame.game.grid.Coord;
import com.codingame.game.grid.Direction;
import com.codingame.game.grid.Protein;
import com.codingame.game.grid.Tile;

public class Serializer {
    public static final String MAIN_SEPARATOR = "\n";

    static public <T> String serialize(List<T> list) {
        return list.stream().map(String::valueOf).collect(Collectors.joining(" "));
    }

    static public String serialize(int[] intArray) {
        return Arrays.stream(intArray).mapToObj(String::valueOf).collect(Collectors.joining(" "));
    }

    static public String serialize(boolean[] boolArray) {
        List<String> strs = new ArrayList<>(boolArray.length);
        for (boolean b : boolArray) {
            strs.add(b ? "1" : "0");
        }
        return strs.stream().collect(Collectors.joining(" "));
    }

    static public String join(Object... args) {
        return Stream.of(args)
            .map(String::valueOf)
            .collect(Collectors.joining(" "));
    }

    private static String serializeStorage(Player p) {
        return join(
            p.storage.get(Protein.A),
            p.storage.get(Protein.B),
            p.storage.get(Protein.C),
            p.storage.get(Protein.D)
        );
    }

    public static String serializeGlobalData(Game game) {
        List<Object> lines = new ArrayList<>();

        lines.add(join(game.grid.width, game.grid.height));
        for (Coord coord : game.grid.getCoords()) {
            Tile t = game.grid.get(coord);
            lines.add(join(t.isObstacle() ? 1 : 0, t.getProteinString()));
        }

        for (Player p : game.players) {
            lines.add(p.organs.size());
            for (Organ o : p.organs) {
                lines.add(
                    join(
                        o.id,
                        o.pos.getX(),
                        o.pos.getY(),
                        o.getType().name(),
                        o.direction.alias,
                        o.parent == null ? 0 : o.parent.id
                    )
                );
            }

        }

        return lines.stream()
            .map(String::valueOf)
            .collect(Collectors.joining(MAIN_SEPARATOR));
    }

    public static String serializeFrameData(Game game) {
        List<Object> lines = new ArrayList<>();

        for (Player p : game.players) {
            lines.add(serializeStorage(p));
            lines.add(p.messages.size());
            p.messages.forEach((id, m) -> {
                lines.add(join(id, m));
            });
        }

        lines.add(game.getViewerEvents().size());
        game.getViewerEvents().stream()
            .flatMap(
                e -> Stream.of(
                    e.type,
                    e.animData.start,
                    e.animData.end,
                    e.playerIdx == null ? "" : e.playerIdx,
                    e.id == null ? "" : e.id,
                    e.organType == null ? "" : e.organType,
                    e.direction == null ? "" : e.direction,
                    serializeEventCoords(e)
                )
            )
            .forEach(lines::add);

        return lines.stream()
            .map(String::valueOf)
            .collect(Collectors.joining(MAIN_SEPARATOR));
    }

    public static String serializeEventCoords(EventData e) {
        return Stream.concat(
            Stream.of(e.coord, e.target).filter(c -> !Objects.isNull(c)),
            Optional.ofNullable(e.growFrom).map(gf -> gf.stream()).orElse(Stream.empty())
        ).map(
            coord -> coord.toIntString()
        ).collect(
            Collectors.joining("_")
        );
    }

    public static List<String> serializeGlobalInfoFor(Player player, Game game) {
        List<Object> lines = new ArrayList<>();
        lines.add(join(game.grid.width, game.grid.height));
        return lines.stream()
            .map(String::valueOf)
            .collect(Collectors.toList());
    }

    public static List<String> serializeFrameInfoFor(Player player, Game game) {
        List<Object> lines = new ArrayList<>();
        for (Coord coord : game.grid.getCoords()) {
            Tile t = game.grid.get(coord);
            Optional<Organ> o = t.getOrgan();

            String type;
            if (t.isObstacle()) {
                type = "WALL";
            } else if (t.hasProtein()) {
                type = t.getProteinString();
            } else if (o.isPresent()) {
                type = o.get().getType().name();
            } else {
                continue;
            }
            lines.add(
                join(
                    coord.toIntString(),
                    type,
                    o.map(Organ::getOwner).map(p -> p == player ? "1" : "0").orElse("-1"),
                    o.map(Organ::getId).orElse(0),
                    o.map(Organ::getDirection).map(Direction::toString).orElse("X"),
                    o.map(Organ::getParentId).orElse(0),
                    o.map(Organ::getRootId).orElse(0)
                )
            );
        }
        lines.add(0, lines.size());

        lines.add(serializeStorage(player));
        for (Player p : game.players) {
            if (p != player) {
                lines.add(serializeStorage(p));
            }
        }

        lines.add(player.getExpectedOutputLines());

        return lines.stream()
            .map(String::valueOf)
            .collect(Collectors.toList());
    }

}
