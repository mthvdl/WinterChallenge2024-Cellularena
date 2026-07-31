package com.codingame.game.grid;

import java.util.Optional;

import com.codingame.game.Organ;
import com.codingame.game.Player;

public class Tile {
    public static final Tile NO_TILE = new Tile(new Coord(-1, -1)) {
        @Override
        public boolean isValid() {
            return false;
        }
    };

    private Protein protein;
    private boolean obstacle; //XXX: it could just be a no-tile
    private Organ organ;
    private Coord coord;

    public Tile(Coord coord) {
        this.coord = coord;
    }

    public boolean isValid() {
        return true;
    }

    public void setObstacle() {
        obstacle = true;
        protein = null;
    }

    public Protein getProtein() {
        return protein;
    }

    public void setProtein(int idx) {
        obstacle = false;
        protein = Protein.fromIndex(idx);

    }

    public boolean isObstacle() {
        return obstacle;
    }

    public void placeOrgan(Organ organ) {
        this.organ = organ;
        obstacle = false;
        protein = null;
    }

    public Optional<Organ> getOrgan() {
        return Optional.ofNullable(organ);
    }

    public String getProteinString() {
        return protein == null ? "X" : protein.toString();
    }

    public void unsetObstacle() {
        obstacle = false;
    }

    public void clear() {
        this.organ = null;
        this.obstacle = false;
        this.protein = null;
    }

    public boolean hasOrgan() {
        return this.organ != null;
    }

    public boolean hasTentacle(Player owner, Coord facing) {
        return getOrgan().map(
            organ -> organ.getOwner() == owner
                && organ.isTentacle()
                && organ.getFacedCoord().equals(facing)
        ).orElse(false);
    }

    public boolean hasProtein() {
        return protein != null;
    }

}
