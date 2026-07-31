package com.codingame.game;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.codingame.game.action.Action;
import com.codingame.game.grid.Protein;
import com.codingame.gameengine.core.AbstractMultiplayerPlayer;

public class Player extends AbstractMultiplayerPlayer {

    String message;
    List<Action> actions;

    Map<Protein, Integer> storage;
    List<Organ> organs;
    List<Organ> roots;
    Set<Integer> actedOrganismRootIds;
    ProteinSummary proteinSummary;

    Map<Integer, String> messages;
    List<String> unassignedMessages;

    public Player() {
        storage = new HashMap<>();
        organs = new ArrayList<>();
        actions = new ArrayList<>();
        roots = new ArrayList<>();
        unassignedMessages = new ArrayList<>();
        messages = new HashMap<>();
        actedOrganismRootIds = new HashSet<>();

        for (int i = 0; i < Game.PROTEIN_COUNT; ++i) {
            storage.put(Protein.fromIndex(i), 0);
        }

        proteinSummary = new ProteinSummary();
    }

    @Override
    public int getExpectedOutputLines() {
        return roots.size();
    }

    public void reset() {
        this.message = null;
        this.actions.clear();
        actedOrganismRootIds.clear();
        proteinSummary.clear();
        unassignedMessages.clear();
        messages.clear();
    }

    public void setMessage(String message) {
        this.message = message;

    }

    public void addAction(Action action) {
        actions.add(action);
    }

    public void addOrgan(Organ organ) {
        if (organ.getType() == OrganType.ROOT) {
            roots.add(organ);
        }
        organs.add(organ);
    }

    public void absorb(Protein protein) {
        if (protein == null) {
            return;
        }
        storage.compute(protein, (k, v) -> v + Game.PROTEIN_PER_ABSORB);
        proteinSummary.getFromAbsorb(protein, Game.PROTEIN_PER_ABSORB);
    }

    public void harvestProtein(Protein protein) {
        storage.put(protein, storage.get(protein) + 1);
        proteinSummary.getFromHarvest(protein, 1);

    }

    public void payProtein(Protein protein, int cost) {
        storage.put(protein, storage.get(protein) - cost);
        proteinSummary.loseFromGrowth(protein, cost);
    }

    public void removeOrgan(Organ organ) {
        organs.remove(organ);
        if (organ.getType() == OrganType.ROOT) {
            roots.remove(organ);
        }
    }

    public boolean hasAlreadyActed(int rootId) {
        return actedOrganismRootIds.contains(rootId);
    }

    public void setActed(int rootId) {
        actedOrganismRootIds.add(rootId);
    }

    public int getProteinTotal() {
        int total = 0;
        for (Protein protein : storage.keySet()) {
            total += storage.get(protein);
        }
        return total;
    }

    public String getProteinSummary() {
        String report = proteinSummary.toString();
        if (report.isBlank()) {
            return "";
        }
        return getNicknameToken() + ":\n" + proteinSummary.toString();
    }

    public void assignMessage(int rootId, String trimmed) {
        messages.put(rootId, trimmed);
    }

    public void addMessage(String trimmed) {
        unassignedMessages.add(trimmed);

    }

    public void assignMessages() {
        LinkedList<Organ> roots = new LinkedList<>(this.roots);
        roots.removeIf(r -> messages.containsKey(r.getId()));
        for (String m : unassignedMessages) {
            if (roots.isEmpty()) {
                return;
            }
            Organ root = roots.pop();
            messages.put(root.getId(), m);
        }

    }

}
