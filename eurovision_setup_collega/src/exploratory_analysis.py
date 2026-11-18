#!/usr/bin/env python3
"""Exploratory analysis of Eurovision final voting networks (2016–2026).

Run from the project root:
    py src/exploratory_analysis.py

Dependencies:
    pip install networkx matplotlib

Reads the annual matrices built by build_eurovision_data.py without altering them.
Rows represent voting countries; columns represent finalist countries.
An empty cell means an ineligible vote; zero means eligible but no points.
Only strictly positive scores become directed, weighted graph edges.
"""

from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
ALLOWED_POINTS = {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12}
POSITIVE_BALLOT = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MATRIX_DIR = PROJECT_ROOT / "processed_data" / "matrices"
RESULTS_DIR = PROJECT_ROOT / "results" / "exploratory"
FIGURES_DIR = PROJECT_ROOT / "figures" / "exploratory"


def write_csv(path: Path, headers: list[str], records: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(records)


def read_matrix(path: Path) -> tuple[nx.DiGraph, int, set[str], set[str]]:
    """Build a graph and count eligible voting pairs independently of its edges."""
    if not path.is_file():
        raise FileNotFoundError(f"Matrix not found: {path}")

    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        header = next(reader, None)
        if not header or header[0] != "country":
            raise ValueError(f"Invalid matrix header: {path.name}")
        countries = header[1:]
        if not countries or len(set(countries)) != len(countries):
            raise ValueError(f"Missing or duplicated column labels: {path.name}")

        graph = nx.DiGraph()
        graph.add_nodes_from(countries)
        voting_countries: set[str] = set()
        finalist_countries: set[str] = set()
        eligible_pairs = 0
        rows_seen: set[str] = set()

        for row in reader:
            if len(row) != len(header):
                raise ValueError(f"Incorrect row length in {path.name}: {row[:1]}")
            source = row[0]
            if source not in graph or source in rows_seen:
                raise ValueError(f"Unexpected or duplicated row label {source} in {path.name}")
            rows_seen.add(source)
            observed_scores = []
            for target, raw in zip(countries, row[1:]):
                raw = raw.strip()
                if raw == "":
                    continue  # Ineligible pair, not an observed score of zero.
                try:
                    score = int(raw)
                except ValueError as exc:
                    raise ValueError(f"Non-integer score {source}->{target}: {raw}") from exc
                if score not in ALLOWED_POINTS:
                    raise ValueError(f"Invalid score {source}->{target}={score} in {path.name}")
                if source == target:
                    raise ValueError(f"Self-vote in {path.name}: {source}")
                eligible_pairs += 1
                voting_countries.add(source)
                finalist_countries.add(target)
                observed_scores.append(score)
                if score > 0:
                    graph.add_edge(source, target, weight=score)

            if observed_scores and sorted(s for s in observed_scores if s > 0) != POSITIVE_BALLOT:
                raise ValueError(f"Invalid ballot for {source} in {path.name}")

    if rows_seen != set(countries):
        raise ValueError(f"Incomplete matrix rows in {path.name}")
    if graph.number_of_edges() != len(voting_countries) * 10:
        raise ValueError(f"Unexpected number of positive votes in {path.name}")
    return graph, eligible_pairs, voting_countries, finalist_countries


def summarize_network(year: int, layer: str, graph: nx.DiGraph,
                      eligible_pairs: int, voters: set[str], finalists: set[str]) -> tuple:
    """Report both conventional density and density over eligible directed pairs."""
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    weak = nx.number_weakly_connected_components(graph) if n else 0
    strong = nx.number_strongly_connected_components(graph) if n else 0
    return (
        year, layer, n, len(voters), len(finalists), m, eligible_pairs,
        round(nx.density(graph), 6),
        round(m / eligible_pairs, 6) if eligible_pairs else 0,
        weak, strong, sum(data["weight"] for _, _, data in graph.edges(data=True)),
    )


def per_country_stats(year: int, layer: str, graph: nx.DiGraph,
                      voters: set[str], finalists: set[str]) -> list[tuple]:
    return [
        (year, layer, country, int(country in voters), int(country in finalists),
         graph.in_degree(country), graph.out_degree(country),
         graph.in_degree(country, weight="weight"),
         graph.out_degree(country, weight="weight"))
        for country in sorted(graph.nodes())
    ]


def draw_networks(graphs: dict[tuple[int, str], nx.DiGraph]) -> None:
    """Use one layout for both layers; draw high-scoring edges only for legibility."""
    jury = graphs[2016, "jury"]
    public = graphs[2016, "public"]
    combined = nx.Graph()
    combined.add_nodes_from(jury.nodes())
    for graph in (jury, public):
        for source, target, data in graph.edges(data=True):
            weight = data["weight"]
            if combined.has_edge(source, target):
                combined[source][target]["weight"] += weight
            else:
                combined.add_edge(source, target, weight=weight)
    positions = nx.spring_layout(combined, weight="weight", seed=42, iterations=200)

    for layer, graph in (("jury", jury), ("public", public)):
        # Showing the strongest voting ties is a visualization filter, not a data filter.
        shown = [(u, v) for u, v, d in graph.edges(data=True) if d["weight"] >= 10]
        fig, ax = plt.subplots(figsize=(13, 10))
        nx.draw_networkx_nodes(graph, positions, node_size=480, node_color="#dcecf8",
                               edgecolors="#245a83", linewidths=1.2, ax=ax)
        nx.draw_networkx_labels(graph, positions, font_size=8, font_weight="bold", ax=ax)
        nx.draw_networkx_edges(graph, positions, edgelist=shown, width=1.1,
                               arrows=True, arrowsize=10, node_size=480,
                               alpha=0.35, edge_color="#457ea6", ax=ax)
        ax.set_title(f"Eurovision 2016 — {layer.title()} (only 10- and 12-point ties shown)")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / f"2016_{layer}_network.png", dpi=180)
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, (layer, graph) in zip(axes, (("jury", jury), ("public", public))):
        degrees = [degree for _, degree in graph.in_degree()]
        counts = Counter(degrees)
        ax.bar(sorted(counts), [counts[d] for d in sorted(counts)])
        ax.set_title(f"2016 — {layer.title()}")
        ax.set_xlabel("In-degree (number of voting countries)")
        ax.set_ylabel("Number of countries")
    fig.suptitle("Distribution of in-degree in the 2016 final")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "2016_in_degree_distribution.png", dpi=180)
    plt.close(fig)


def draw_yearly_comparison(graphs: dict[tuple[int, str], nx.DiGraph]) -> None:
    """Track the concentration of received points without relying on fixed voter counts."""
    fig, ax = plt.subplots(figsize=(10, 5))
    for layer in LAYERS:
        concentrations = []
        for year in YEARS:
            graph = graphs[year, layer]
            strengths = [value for _, value in graph.in_degree(weight="weight")]
            total = sum(strengths)
            # HHI is the sum of squared point shares received by countries.
            concentrations.append(sum((value / total) ** 2 for value in strengths))
        ax.plot(YEARS, concentrations, marker="o", label=layer.title())
    ax.set_xlabel("Edition")
    ax.set_ylabel("Herfindahl index of received point shares")
    ax.set_title("Concentration of points received (jury vs public)")
    ax.set_xticks(YEARS)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "annual_point_concentration.png", dpi=180)
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    node_statistics = []
    graphs = {}

    for year in YEARS:
        layer_data = {}
        for layer in LAYERS:
            graph, eligible, voters, finalists = read_matrix(MATRIX_DIR / f"{year}_{layer}.csv")
            graphs[year, layer] = graph
            layer_data[layer] = (voters, finalists, eligible)
            summaries.append(summarize_network(year, layer, graph, eligible, voters, finalists))
            node_statistics.extend(per_country_stats(year, layer, graph, voters, finalists))

        # Both voting layers should contain the same eligible pairs in a given edition.
        if layer_data["jury"] != layer_data["public"]:
            raise ValueError(f"Jury/public eligibility differs for {year}")

    write_csv(RESULTS_DIR / "network_summary.csv",
              ["year", "layer", "nodes", "voters", "finalists", "positive_edges",
               "eligible_pairs", "standard_density", "eligible_density",
               "weak_components", "strong_components", "total_positive_points"], summaries)
    write_csv(RESULTS_DIR / "country_metrics.csv",
              ["year", "layer", "country", "is_voter", "is_finalist",
               "in_degree", "out_degree", "in_strength", "out_strength"], node_statistics)
    draw_networks(graphs)
    draw_yearly_comparison(graphs)

    print(f"Matrices read: {len(graphs)}")
    print(f"Country-level observations: {len(node_statistics)}")
    print(f"Tables: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("Completed. Source matrices were not modified.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, csv.Error) as error:
        raise SystemExit(f"Exploratory analysis failed: {error}") from error
