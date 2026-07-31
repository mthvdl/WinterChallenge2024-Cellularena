package com.codingame.game;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import com.codingame.game.grid.Protein;

public class ProteinSummary {

    Map<Protein, Integer> fromGrowth = new HashMap<>();
    Map<Protein, Integer> fromHarvest = new HashMap<>();
    Map<Protein, Integer> fromAbsorb = new HashMap<>();

    public void clear() {
        fromGrowth.clear();
        fromHarvest.clear();
        fromAbsorb.clear();
    }

    private void save(Map<Protein, Integer> report, Protein protein, int n) {
        report.compute(protein, (k, v) -> v == null ? n : v + n);
    }

    public void loseFromGrowth(Protein protein, int n) {
        save(fromGrowth, protein, n);
    }

    public void getFromHarvest(Protein protein, int n) {
        save(fromHarvest, protein, n);
    }

    public void getFromAbsorb(Protein protein, int n) {
        save(fromAbsorb, protein, n);
    }

    @Override
    public String toString() {
        String a = "consumed %s for growth";
        String b = "gained %s from absorption";
        String c = "gained %s from harvest";

        List<String> reports = new ArrayList<>();

        addToReports(reports, fromGrowth, a);
        addToReports(reports, fromAbsorb, b);
        addToReports(reports, fromHarvest, c);

        return reports.stream().map(str -> "- " + str).collect(Collectors.joining("\n"));
    }

    private void addToReports(List<String> reports, Map<Protein, Integer> report, String template) {
        List<String> parts = new ArrayList<>();
        for (Protein p : Protein.values()) {

            int n = report.getOrDefault(p, 0);
            if (n > 0) {
                parts.add("%d%s".formatted(n, p.toString()));
            }
        }
        String text = parts.stream().collect(Collectors.joining(", "));
        if (!text.isBlank()) {
            reports.add(
                template.formatted(text)
            );
        }
    }

}
