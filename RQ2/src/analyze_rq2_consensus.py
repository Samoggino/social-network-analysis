#!/usr/bin/env python3
"""RQ2 (step 4): a consensus community structure instead of a single Louvain run.

Run from the RQ2 directory:
    python src/analyze_rq2_consensus.py

Step 3 showed that a single Louvain run is not a result: with roughly 25 nodes
in the network, the mean ARI between two seeds is about 0.5, so two runs out of
three give different partitions. Reporting "the" communities from one seed is
therefore not defensible.

This script replaces the single run with a consensus partition:

1. Louvain is run over many seeds at the default resolution; every run is one
   vote on whether two countries belong together.
2. The co-assignment matrix (share of runs placing two countries in the same
   community) is turned into a distance, 1 - co-assignment.
3. Countries are merged with average linkage until the modal number of
   communities across runs is reached. That partition is the consensus.

The consensus is then compared with the geographic, linguistic and cultural
partitions, with the same permutation benchmark used in step 3, and its
agreement with the individual runs is reported as a measure of how well it
represents them. Finally the two voting levels are compared with the exact
paired sign-flip test over the ten editions.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from analyze_rq2_partitions import (
    LAYERS,
    SEED,
    YEARS,
    agreement_from_table,
    attribute_labels,
    contingency,
    holm,
    benjamini_hochberg,
    load_attributes,
    load_matrix,
    louvain_labels,
    sign_flip_test,
    weighted_projection,
)

N_SEEDS = 200
N_PERM = 500

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "src" else SCRIPT_DIR
MATRIX_DIR = ROOT / "processed_data" / "matrices"
ATTR_PATH = ROOT / "processed_data" / "tables" / "country_attributes_rq2.csv"
RESULTS_DIR = ROOT / "results" / "rq2"
FIGURES_DIR = ROOT / "figures" / "rq2"

RNG = np.random.default_rng(SEED)


def save_csv(path: Path, columns: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(
            [
                [round(value, 10) if isinstance(value, float) else value for value in row]
                for row in rows
            ]
        )


def co_assignment_matrix(
    undirected: nx.Graph, nodes: list[str], n_seeds: int = N_SEEDS
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    """Share of runs placing each pair in the same community, plus the runs."""
    partitions = [
        louvain_labels(undirected, nodes, seed=seed) for seed in range(n_seeds)
    ]
    matrix = np.zeros((len(nodes), len(nodes)))
    for labels in partitions:
        matrix += labels[:, None] == labels[None, :]
    return matrix / n_seeds, np.array([len(np.unique(p)) for p in partitions]), partitions


def average_linkage(distance: np.ndarray, k: int) -> np.ndarray:
    """Agglomerative clustering with average linkage, stopped at k clusters."""
    n = distance.shape[0]
    clusters = [[i] for i in range(n)]

    while len(clusters) > k:
        best = None
        for a in range(len(clusters)):
            for b in range(a + 1, len(clusters)):
                value = float(distance[np.ix_(clusters[a], clusters[b])].mean())
                if best is None or value < best[0]:
                    best = (value, a, b)
        _, a, b = best
        clusters[a] = clusters[a] + clusters[b]
        del clusters[b]

    labels = np.zeros(n, dtype=int)
    for index, cluster in enumerate(clusters):
        labels[cluster] = index
    return labels


def consensus_labels(co_assignment: np.ndarray, k: int) -> np.ndarray:
    distance = 1.0 - co_assignment
    np.fill_diagonal(distance, 0.0)
    return average_linkage(distance, k)


def modal(values: np.ndarray) -> int:
    """Most frequent value, smallest one on ties."""
    unique, counts = np.unique(values, return_counts=True)
    return int(unique[np.argmax(counts)])


def plot_consensus(rows: list[dict]) -> None:
    index = {(row["year"], row["layer"], row["scope"]): row for row in rows}
    positions = np.arange(len(YEARS))
    colors = {"jury": "#246b91", "public": "#cf7135"}

    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8))

    for offset, layer in zip((-0.15, 0.15), LAYERS):
        values = [index[(y, layer, "all")]["ari_region"] for y in YEARS]
        axes[0].plot(
            positions + offset, values, marker="o", color=colors[layer],
            label=f"{layer.title()} consensus",
        )
        single = [index[(y, layer, "all")]["ari_region_single"] for y in YEARS]
        axes[0].plot(
            positions + offset, single, marker="o", linestyle=":", color=colors[layer],
            alpha=0.55, label=f"{layer.title()} single run",
        )

    null = [index[(y, "jury", "all")]["ari_region_null"] for y in YEARS]
    axes[0].plot(
        positions, null, color="#3b3b3b", linestyle="--", marker="D",
        markersize=4, linewidth=1.2, label="Permutation benchmark",
    )
    axes[0].set_xticks(positions, YEARS, rotation=45)
    axes[0].set_ylabel("ARI with UN M49 subregions")
    axes[0].set_title("Consensus vs single run vs chance")
    axes[0].grid(axis="y", alpha=0.2)
    axes[0].legend(frameon=False, fontsize=8)

    for offset, layer in zip((-0.15, 0.15), LAYERS):
        values = [index[(y, layer, "all")]["mean_ari_to_runs"] for y in YEARS]
        axes[1].plot(
            positions + offset, values, marker="o", color=colors[layer], label=layer.title()
        )

    axes[1].set_xticks(positions, YEARS, rotation=45)
    axes[1].set_ylim(0, 1)
    axes[1].set_ylabel("Mean ARI between consensus and the runs")
    axes[1].set_title("How well the consensus represents the ensemble")
    axes[1].grid(axis="y", alpha=0.2)
    axes[1].legend(frameon=False, fontsize=8)

    fig.suptitle("RQ2 - Consensus community structure")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "rq2_consensus.png", dpi=200)
    plt.close(fig)


def plot_consensus_map(
    year: int, layer: str, nodes: list[str], matrix: np.ndarray,
    labels: np.ndarray, attributes, ari: float,
) -> None:
    """Co-assignment matrix ordered by the consensus partition."""
    order = np.lexsort((np.array(nodes), labels))
    ordered = matrix[np.ix_(order, order)]
    names = [nodes[i] for i in order]
    regions = [attributes.get(nodes[i], {}).get("region", "") for i in order]

    unique_regions = []
    for region in regions:
        if region not in unique_regions:
            unique_regions.append(region)
    palette = plt.get_cmap("tab10")
    colour_of = {r: palette(i % 10) for i, r in enumerate(unique_regions)}

    fig, ax = plt.subplots(figsize=(9.5, 8.5))
    image = ax.imshow(ordered, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(names)), names, rotation=90, fontsize=7)
    ax.set_yticks(range(len(names)), names, fontsize=7)
    for tick, region in zip(ax.get_xticklabels(), regions):
        tick.set_color(colour_of[region])
    for tick, region in zip(ax.get_yticklabels(), regions):
        tick.set_color(colour_of[region])
    ax.set_title(
        f"Consensus co-assignment, {year} {layer} "
        f"({len(np.unique(labels))} communities, ARI vs subregions {ari:.2f})",
        fontsize=11,
    )
    handles = [
        plt.Line2D([], [], marker="s", linestyle="", color=colour_of[r], label=r or "unknown")
        for r in unique_regions
    ]
    ax.legend(
        handles=handles, frameon=False, fontsize=7, ncol=2,
        loc="upper center", bbox_to_anchor=(0.5, -0.16),
    )
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Share of runs in the same community")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f"rq2_consensus_map_{year}_{layer}.png", dpi=200)
    plt.close(fig)


def main() -> None:
    attributes = load_attributes(ATTR_PATH)

    rows: list[dict] = []
    tests: list[tuple] = []

    for year in YEARS:
        for layer in LAYERS:
            graph, voters, finalists = load_matrix(MATRIX_DIR / f"{year}_{layer}.csv")

            for scope in ("all", "finalists"):
                subgraph = graph if scope == "all" else graph.subgraph(finalists).copy()
                nodes = sorted(subgraph.nodes())
                undirected = weighted_projection(subgraph)

                co_assignment, sizes, partitions = co_assignment_matrix(undirected, nodes)
                k = modal(sizes)
                consensus = consensus_labels(co_assignment, k)

                single = louvain_labels(undirected, nodes)

                row: dict[str, object] = {
                    "year": year,
                    "layer": layer,
                    "scope": scope,
                    "nodes": len(nodes),
                    "consensus_k": k,
                    "mean_k": float(sizes.mean()),
                    "consensus_modularity": nx.community.modularity(
                        undirected,
                        [set(np.array(nodes)[consensus == c]) for c in np.unique(consensus)],
                        weight="weight",
                    ),
                }

                row["mean_ari_to_runs"] = float(np.mean([
                    agreement_from_table(contingency(consensus, p))[1]
                    for p in partitions
                ]))

                for key in ("region", "language", "block"):
                    truth = attribute_labels(nodes, attributes, key)
                    nmi, ari = agreement_from_table(contingency(consensus, truth))
                    nmi_single, ari_single = agreement_from_table(contingency(single, truth))

                    null_nmi = np.empty(N_PERM)
                    null_ari = np.empty(N_PERM)
                    for b in range(N_PERM):
                        shuffled = RNG.permutation(truth)
                        null_nmi[b], null_ari[b] = agreement_from_table(
                            contingency(consensus, shuffled)
                        )

                    row[f"nmi_{key}"] = nmi
                    row[f"ari_{key}"] = ari
                    row[f"nmi_{key}_null"] = float(null_nmi.mean())
                    row[f"ari_{key}_null"] = float(null_ari.mean())
                    row[f"ari_{key}_single"] = ari_single

                    for statistic, observed, null in (
                        ("nmi", nmi, null_nmi),
                        ("ari", ari, null_ari),
                    ):
                        p = (1 + int((null >= observed).sum())) / (1 + N_PERM)
                        tests.append((
                            year, layer, scope, key, statistic,
                            observed, float(null.mean()), p,
                        ))

                rows.append(row)

                if year == 2016:
                    plot_consensus_map(year, layer, nodes, co_assignment, consensus,
                                       attributes, row["ari_region"])

            print(f"{year}: {layer} consensus computed")

    columns = [
        "year", "layer", "scope", "nodes", "consensus_k", "mean_k",
        "consensus_modularity", "mean_ari_to_runs",
        "nmi_region", "nmi_region_null", "ari_region", "ari_region_null", "ari_region_single",
        "nmi_language", "nmi_language_null", "ari_language", "ari_language_null", "ari_language_single",
        "nmi_block", "nmi_block_null", "ari_block", "ari_block_null", "ari_block_single",
    ]
    save_csv(RESULTS_DIR / "rq2_consensus.csv", columns, [[r[c] for c in columns] for r in rows])
    save_csv(
        RESULTS_DIR / "rq2_consensus_tests.csv",
        ["year", "layer", "scope", "attribute", "statistic", "observed", "null_mean", "p_one_sided"],
        tests,
    )

    metrics = [
        ("ari_region", "ARI con le sottoregioni"),
        ("nmi_region", "NMI con le sottoregioni"),
        ("ari_language", "ARI con le famiglie linguistiche"),
        ("ari_block", "ARI con i blocchi culturali"),
        ("mean_ari_to_runs", "ARI medio tra consenso ed esecuzioni"),
    ]

    differences = []
    for scope in ("all", "finalists"):
        for key, label in metrics:
            jury = [r[key] for r in rows if r["layer"] == "jury" and r["scope"] == scope]
            public = [r[key] for r in rows if r["layer"] == "public" and r["scope"] == scope]
            observed, p = sign_flip_test(jury, public)
            differences.append((f"{label} ({scope})", observed, p))

    raw = [d[2] for d in differences]
    save_csv(
        RESULTS_DIR / "rq2_consensus_layer_diff.csv",
        ["metrica", "differenza_televoto_giurie", "p_esatto", "p_holm", "p_fdr"],
        [
            (label, observed, p, ph, pb)
            for (label, observed, p), ph, pb in zip(
                differences, holm(raw), benjamini_hochberg(raw)
            )
        ],
    )

    plot_consensus(rows)

    print(f"Results: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("Consensus community structure complete.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, nx.NetworkXException) as exc:
        raise SystemExit(f"RQ2 consensus analysis failed: {exc}") from exc
