#!/usr/bin/env python3
"""Write the GEXF files rendered by RenderReportGraphs.java for the report.

Two figures, each with a jury and a public panel built with the same rule:

* ``strong_<layer>``: aggregated 2016-2026 network, dichotomised. Edge A -> B
  is kept if A could vote for B in at least 3 finals and gave it on average at
  least 6 points per opportunity (zeros included). Node size = mean points
  received per opportunity. Edges inside the same UN subregion take the colour
  of the subregion, edges across subregions are light grey (RQ2/RQ3 homophily).
* ``reciprocal_<layer>``: undirected network of the pairs reciprocal in at
  least 75% of the finals in which both were eligible (>= 3 finals), from
  RQ1/results/rq1/rq1_temporal_pairs.csv (RQ1 temporal persistence).

Node colour = UN M49 subregion (RQ2 attribute table). Standard library only.

Usage: python3 scripts/gephi/make_report_graphs.py [out_dir]
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output" / "gephi" / "report"

MIN_OPPORTUNITIES = 3
MIN_POINTS_PER_OPPORTUNITY = 6.0
MIN_RECIPROCITY = 0.75

# Okabe-Ito, colour-blind safe; order = legend order.
REGION_COLOURS = {
    "Northern Europe": (0, 114, 178),
    "Western Europe": (230, 159, 0),
    "Southern Europe": (0, 158, 115),
    "Eastern Europe": (204, 121, 167),
    "Western Asia": (213, 94, 0),
    "Australia and New Zealand": (86, 180, 233),
}
CROSS_EDGE = (200, 200, 200)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_gexf(path: Path, nodes: dict, edges: list, directed: bool) -> None:
    rng = random.Random(42)  # initial positions: ForceAtlas2 is deterministic from here
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gexf xmlns="http://gexf.net/1.3" xmlns:viz="http://gexf.net/1.3/viz" version="1.3">',
        f'<graph defaultedgetype="{"directed" if directed else "undirected"}">',
        '<attributes class="node"><attribute id="region" title="region" type="string"/><attribute id="vsize" title="vsize" type="float"/></attributes>',
        "<nodes>",
    ]
    for code in sorted(nodes):
        n = nodes[code]
        r, g, b = REGION_COLOURS[n["region"]]
        lines += [
            f'<node id="{code}" label="{code}"><attvalues><attvalue for="region" value="{escape(n["region"])}"/><attvalue for="vsize" value="{n["size"]:.2f}"/></attvalues>',
            f'<viz:color r="{r}" g="{g}" b="{b}"/><viz:size value="{n["size"]:.2f}"/>',
            f'<viz:position x="{rng.uniform(-500, 500):.1f}" y="{rng.uniform(-500, 500):.1f}" z="0"/></node>',
        ]
    lines.append("</nodes><edges>")
    for i, (s, t, w, (r, g, b)) in enumerate(edges):
        lines.append(f'<edge id="{i}" source="{s}" target="{t}" weight="{w:.4f}"><viz:color r="{r}" g="{g}" b="{b}"/></edge>')
    lines.append("</edges></graph></gexf>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def edge_colour(region: dict[str, str], a: str, b: str) -> tuple[int, int, int]:
    return REGION_COLOURS[region[a]] if region[a] == region[b] else CROSS_EDGE


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    region = {a["country"]: a["region"] for a in read_csv(ROOT / "RQ2/processed_data/tables/country_attributes_rq2.csv")}
    pairs = read_csv(ROOT / "RQ1/results/rq1/rq1_temporal_pairs.csv")

    for layer in ("jury", "public"):
        # --- strong ties (aggregated, dichotomised) ---
        agg = ROOT / "output" / f"2016-2026_{layer}"
        node_rows = read_csv(agg.with_name(agg.name + "_nodes.csv"))
        nodes = {}
        for n in node_rows:
            opp = int(n["opportunities_in"])
            ppo = float(n["in_weight"]) / opp if opp else 0.0
            nodes[n["Id"]] = {"region": region[n["Id"]], "size": 16.0 + 11.0 * ppo}
        edges = []
        for e in read_csv(agg.with_name(agg.name + "_edges.csv")):
            ppo = float(e["per_opportunity"])
            if int(e["opportunities"]) >= MIN_OPPORTUNITIES and ppo >= MIN_POINTS_PER_OPPORTUNITY:
                edges.append((e["Source"], e["Target"], ppo, edge_colour(region, e["Source"], e["Target"])))
        linked = {s for s, _, _, _ in edges} | {t for _, t, _, _ in edges}
        nodes = {c: v for c, v in nodes.items() if c in linked}  # isolates carry no information here
        same = sum(region[s] == region[t] for s, t, _, _ in edges)
        write_gexf(OUT / f"strong_{layer}.gexf", nodes, edges, directed=True)
        print(f"strong_{layer}: {len(nodes)} nodes, {len(edges)} edges, {same} within subregion ({same / len(edges):.0%})")

        # --- persistent reciprocal pairs ---
        kept = [
            p for p in pairs
            if p["layer"] == layer
            and int(p["opportunity_years"]) >= MIN_OPPORTUNITIES
            and float(p["reciprocity_frequency"]) >= MIN_RECIPROCITY
        ]
        members = {p["country_a"] for p in kept} | {p["country_b"] for p in kept}
        degree = {c: sum(c in (p["country_a"], p["country_b"]) for p in kept) for c in members}
        nodes = {c: {"region": region[c], "size": 13.0 + 2.5 * degree[c]} for c in members}
        edges = [
            (p["country_a"], p["country_b"], 1.0 + 4.0 * float(p["high_reciprocity_frequency"]),
             edge_colour(region, p["country_a"], p["country_b"]))
            for p in kept
        ]
        same = sum(region[s] == region[t] for s, t, _, _ in edges)
        write_gexf(OUT / f"reciprocal_{layer}.gexf", nodes, edges, directed=False)
        print(f"reciprocal_{layer}: {len(nodes)} nodes, {len(edges)} pairs, {same} within subregion")
    return 0


if __name__ == "__main__":
    sys.exit(main())
