#!/usr/bin/env python3
"""RQ2: communities and homophily in Eurovision final votes.

Run from the RQ2 directory:
    python src/analyze_rq2.py

Requires networkx and matplotlib. Reads the 20 annual matrices produced by
build_eurovision_data.py and the country attribute table. Does not modify any
input data.

For each network the script:
  * detects communities with Louvain on the undirected, weighted projection
    (the weight of a pair is the sum of the two directed weights);
  * computes modularity and the number of communities;
  * computes geographic assortativity on the positive-edge network;
  * computes the share of points sent to the same UN M49 subregion and the
    share sent to countries sharing at least one language group;
  * repeats the whole analysis on the finalist-only subnetwork.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
SEED = 42

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "src" else SCRIPT_DIR

MATRIX_DIR = ROOT / "processed_data" / "matrices"
ATTR_PATH = ROOT / "processed_data" / "tables" / "country_attributes_rq2.csv"
RESULTS_DIR = ROOT / "results" / "rq2"
FIGURES_DIR = ROOT / "figures" / "rq2"


def save_csv(path: Path, columns: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def load_attributes(path: Path) -> dict[str, dict[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(f"Attribute table not found: {path}")

    attributes: dict[str, dict[str, object]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            code = row["country"].strip()
            groups = [g.strip() for g in row["language_groups"].split(";") if g.strip()]
            attributes[code] = {
                "region": row["region"].strip(),
                "language_groups": set(groups),
            }
    return attributes


def load_matrix(path: Path) -> tuple[nx.DiGraph, set[str], set[str]]:
    """Blank cells mark impossible votes; positive points become directed edges."""
    if not path.is_file():
        raise FileNotFoundError(f"Matrix not found: {path}")

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)

        if not header or header[0] != "country":
            raise ValueError(f"Unexpected header in {path.name}")

        countries = header[1:]
        graph = nx.DiGraph()
        graph.add_nodes_from(countries)

        voters: set[str] = set()
        finalists: set[str] = set()

        for row in reader:
            if len(row) != len(header):
                raise ValueError(f"Invalid row width in {path.name}")

            source = row[0]
            voters.add(source)

            for target, raw in zip(countries, row[1:]):
                if raw.strip() == "":
                    continue
                finalists.add(target)
                points = int(raw)
                if points:
                    graph.add_edge(source, target, weight=points)

    return graph, voters, finalists


def weighted_projection(graph: nx.DiGraph) -> nx.Graph:
    """Undirected projection whose weight is the sum of the two directions."""
    undirected = nx.Graph()
    undirected.add_nodes_from(graph.nodes())
    for source, target, data in graph.edges(data=True):
        weight = data["weight"]
        if undirected.has_edge(source, target):
            undirected[source][target]["weight"] += weight
        else:
            undirected.add_edge(source, target, weight=weight)
    return undirected


def point_shares(
    graph: nx.DiGraph,
    attributes: dict[str, dict[str, object]],
    voters: set[str],
) -> tuple[float, float]:
    """Share of awarded points to same subregion / shared language."""
    total = 0
    same_region = 0
    same_language = 0

    for source, target, data in graph.edges(data=True):
        points = data["weight"]
        total += points

        source_attr = attributes.get(source, {})
        target_attr = attributes.get(target, {})

        if source_attr.get("region") and source_attr["region"] == target_attr.get("region"):
            same_region += points

        shared = source_attr.get("language_groups", set()) & target_attr.get("language_groups", set())
        if shared:
            same_language += points

    if not total:
        return float("nan"), float("nan")

    return same_region / total, same_language / total


def analyze_subset(
    graph: nx.DiGraph,
    attributes: dict[str, dict[str, object]],
    scope: str,
) -> tuple[tuple, list[tuple]]:
    undirected = weighted_projection(graph)
    communities = [set(c) for c in nx.community.louvain_communities(undirected, weight="weight", seed=SEED)]
    modularity = nx.community.modularity(undirected, communities, weight="weight")

    assignment = {}
    for index, community in enumerate(communities):
        for node in community:
            assignment[node] = index

    try:
        assortativity = nx.attribute_assortativity_coefficient(graph, "region")
    except (nx.NetworkXError, ZeroDivisionError):
        assortativity = float("nan")

    region_share, language_share = point_shares(graph, attributes, set(graph.nodes()))

    summary = (
        scope,
        graph.number_of_nodes(),
        graph.number_of_edges(),
        len(communities),
        modularity,
        assortativity,
        region_share,
        language_share,
    )

    membership = [
        (scope, node, assignment[node], attributes.get(node, {}).get("region", ""))
        for node in sorted(graph.nodes())
    ]

    return summary, membership


def analyse_network(
    year: int,
    layer: str,
    graph: nx.DiGraph,
    attributes: dict[str, dict[str, object]],
    finalists: set[str],
) -> tuple[tuple, list[tuple], list[tuple]]:
    full_graph = graph.copy()
    nx.set_node_attributes(full_graph, {n: attributes.get(n, {}).get("region", "") for n in full_graph}, "region")

    finalist_graph = graph.subgraph(finalists).copy()
    nx.set_node_attributes(
        finalist_graph,
        {n: attributes.get(n, {}).get("region", "") for n in finalist_graph},
        "region",
    )

    full_summary, full_membership = analyze_subset(full_graph, attributes, "all")
    fin_summary, fin_membership = analyze_subset(finalist_graph, attributes, "finalists")

    summary = (year, layer) + full_summary[1:] + fin_summary[1:]
    rows = [(year, layer) + m for m in full_membership + fin_membership]

    return summary, rows


def plot_2016(index: dict[tuple[int, str], tuple]) -> None:
    """Side-by-side view of the 2016 jury and televote communities.

    Both panels share the same node positions, so the colours can be compared.
    """
    palette = ["#246b91", "#cf7135", "#4d8f5a", "#a8453a", "#7a5fa8", "#b59a2f"]
    graphs = {}

    for layer in LAYERS:
        graph, _, _ = load_matrix(MATRIX_DIR / f"2016_{layer}.csv")
        graphs[layer] = weighted_projection(graph)

    layout_graph = nx.compose(graphs["jury"], graphs["public"])
    position = nx.spring_layout(layout_graph, seed=SEED, weight="weight", k=0.75, iterations=200)

    fig, axes = plt.subplots(1, 2, figsize=(16, 7.5))

    for ax, layer in zip(axes, LAYERS):
        undirected = graphs[layer]
        communities = [
            set(c)
            for c in nx.community.louvain_communities(undirected, weight="weight", seed=SEED)
        ]

        nx.draw_networkx_edges(
            undirected, position, ax=ax, alpha=0.07, width=0.6, edge_color="#44586b",
        )

        for index_, community in enumerate(communities):
            nx.draw_networkx_nodes(
                undirected, position,
                nodelist=sorted(community),
                node_color=palette[index_ % len(palette)],
                node_size=900, linewidths=0.8, edgecolors="white", ax=ax,
            )

        nx.draw_networkx_labels(undirected, position, font_size=7, font_color="white", ax=ax)

        summary = index[(2016, layer)]
        ax.set_title(
            f"{layer.title()} - {len(communities)} communities, "
            f"modularity {summary[5]:.3f}, same region {summary[7]:.1%}",
            fontsize=12,
        )
        ax.axis("off")

    fig.suptitle(
        "RQ2 - Communities in the 2016 final (all voting countries, shared layout)",
        fontsize=13,
    )
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "2016_community_comparison.png", dpi=200)
    plt.close(fig)


def main() -> None:
    attributes = load_attributes(ATTR_PATH)

    summaries: list[tuple] = []
    memberships: list[tuple] = []

    for year in YEARS:
        for layer in LAYERS:
            graph, voters, finalists = load_matrix(MATRIX_DIR / f"{year}_{layer}.csv")
            summary, rows = analyse_network(year, layer, graph, attributes, finalists)
            summaries.append(summary)
            memberships.extend(rows)
            print(f"{year}: {layer} communities analyzed")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    save_csv(
        RESULTS_DIR / "rq2_summary.csv",
        [
            "year", "layer",
            "nodes_all", "edges_all", "communities_all", "modularity_all",
            "region_assortativity_all", "same_region_share_all", "shared_language_share_all",
            "nodes_finalists", "edges_finalists", "communities_finalists",
            "modularity_finalists", "region_assortativity_finalists",
            "same_region_share_finalists", "shared_language_share_finalists",
        ],
        summaries,
    )

    save_csv(
        RESULTS_DIR / "community_memberships.csv",
        ["year", "layer", "scope", "country", "community", "region"],
        memberships,
    )

    index = {(row[0], row[1]): row for row in summaries}
    plot_2016(index)

    print(f"Results: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("Exploratory analysis only; significance testing is pending.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, nx.NetworkXException) as exc:
        raise SystemExit(f"RQ2 analysis failed: {exc}") from exc
