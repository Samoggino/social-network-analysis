#!/usr/bin/env python3
"""Add a ready-made Gephi look to the GEXF files written by build_graph.py.

For every input file it writes ``<name>_styled.gexf`` with GEXF "viz" data,
which Gephi applies on import (no manual setup needed):

* position: force-directed layout (networkx spring layout, weighted, fixed seed);
* node colour: Louvain community on the directed weighted graph (fixed seed),
  also stored as the ``modularity_class`` attribute; never-finalist countries
  (``role = voter_only``) are drawn in grey;
* node size: proportional to the square root of ``in_weight`` (points received);
* edge colour: the colour of the voting country; edge thickness: ``weight``.

Requires networkx (``pip install networkx``).

Usage::

    python3 scripts/style_gexf.py output/per-year/2025_public.gexf
    python3 scripts/style_gexf.py output/per-year/*.gexf
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import networkx as nx

SEED = 42
# Colour-blind friendly qualitative palette (Okabe-Ito + Tableau extensions).
PALETTE = [
    (0, 114, 178), (230, 159, 0), (0, 158, 115), (204, 121, 167),
    (86, 180, 233), (213, 94, 0), (240, 228, 66), (148, 103, 189),
    (140, 86, 75), (23, 190, 207), (188, 189, 34), (127, 127, 127),
]
GREY = (190, 190, 190)


def style(graph: nx.DiGraph) -> nx.DiGraph:
    weights = {(u, v): float(d.get("weight", 1.0)) for u, v, d in graph.edges(data=True)}
    max_w = max(weights.values(), default=1.0) or 1.0

    # Louvain on the directed weighted graph (directed modularity).
    communities = nx.community.louvain_communities(graph, weight="weight", seed=SEED)
    communities = sorted(communities, key=lambda c: (-len(c), sorted(c)))
    community_of = {node: i for i, members in enumerate(communities) for node in members}

    # Layout on the symmetrised graph: attraction grows with the points exchanged.
    undirected = nx.Graph()
    undirected.add_nodes_from(graph)
    for (u, v), w in weights.items():
        prev = undirected.get_edge_data(u, v, {"weight": 0.0})["weight"]
        undirected.add_edge(u, v, weight=prev + w / max_w)
    k = 2.5 / math.sqrt(max(graph.number_of_nodes(), 1))
    pos = nx.spring_layout(undirected, weight="weight", k=k, iterations=500, seed=SEED, scale=1000)

    max_in = max((float(d.get("in_weight", 0)) for _, d in graph.nodes(data=True)), default=1.0) or 1.0
    for node, data in graph.nodes(data=True):
        cls = community_of[node]
        rgb = GREY if data.get("role") == "voter_only" else PALETTE[cls % len(PALETTE)]
        data["modularity_class"] = cls
        data["viz"] = {
            "position": {"x": float(pos[node][0]), "y": float(pos[node][1]), "z": 0.0},
            "size": 8.0 + 42.0 * math.sqrt(float(data.get("in_weight", 0)) / max_in),
            "color": {"r": rgb[0], "g": rgb[1], "b": rgb[2], "a": 1.0},
        }
    for u, v, data in graph.edges(data=True):
        rgb = graph.nodes[u]["viz"]["color"]
        data["viz"] = {
            "thickness": 0.5 + 7.5 * weights[u, v] / max_w,
            "color": {"r": rgb["r"], "g": rgb["g"], "b": rgb["b"], "a": 0.6},
        }

    q = nx.community.modularity(graph, communities, weight="weight")
    graph.graph["styled"] = f"{len(communities)} Louvain communities, modularity {q:.3f}"
    return graph


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path, help="GEXF files from build_graph.py")
    args = parser.parse_args(argv)

    for path in args.files:
        if path.stem.endswith("_styled"):
            continue
        graph = nx.read_gexf(path)
        if not graph.is_directed() or graph.number_of_edges() == 0:
            print(f"skip {path}: empty or undirected graph", file=sys.stderr)
            continue
        graph.graph.pop("mode", None)
        styled = style(graph)
        out = path.with_name(path.stem + "_styled.gexf")
        nx.write_gexf(styled, out, version="1.2draft")
        print(f"{out}: {styled.graph['styled']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
