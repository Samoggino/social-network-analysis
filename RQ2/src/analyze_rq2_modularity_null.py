#!/usr/bin/env python3
"""RQ2 (step 5): is the modularity larger than a weight-shuffling null expects?

Run from the RQ2 directory:
    python src/analyze_rq2_modularity_null.py

Modularity is usually reported as a bare number, but its magnitude depends on
the density and on the degree sequence: two networks with the same number of
edges can have very different maximum modularity. The value alone therefore does
not say whether the communities are meaningful.

The natural null for a weighted network is to keep the binary structure and ask
whether the large weights are placed where they are by chance. That is the null
used here: the edge weights are permuted across the fixed topology, so the set
of possible votes is untouched, every edge keeps its existence, and only the
association between "this pair" and "these points" is destroyed. The observed
modularity is then compared with the modularity obtained by running the same
Louvain procedure on the permuted networks.

A degree-preserving rewiring of the topology is deliberately *not* used. The
undirected projection of a Eurovision final is almost complete (each finalist
receives points from most other countries, so the projection has density close
to 0.8); double edge swaps have almost no admissible moves and, in a test run,
failed to produce a single valid replicate on three of the forty networks. The
density is reported for every network for this reason.

This mirrors the logic used in RQ1, which also compares observed structure with
randomized networks rather than reading the raw statistic.
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
    benjamini_hochberg,
    holm,
    load_matrix,
    louvain_labels,
    sign_flip_test,
    weighted_projection,
)

N_NULL = 2000  # quick reproducible run; raise to >=1000 for publication-grade Monte Carlo

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "src" else SCRIPT_DIR
MATRIX_DIR = ROOT / "processed_data" / "matrices"
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


def modularity_of(undirected: nx.Graph, labels: np.ndarray, nodes: list[str]) -> float:
    communities = [set(np.array(nodes)[labels == c]) for c in np.unique(labels)]
    return nx.community.modularity(undirected, communities, weight="weight")


def shuffle_weights(undirected: nx.Graph) -> nx.Graph:
    """Keep the topology, permute the weights over the edges."""
    shuffled = undirected.copy()
    weights = [data["weight"] for _, _, data in undirected.edges(data=True)]
    RNG.shuffle(weights)
    for (source, target), weight in zip(shuffled.edges(), weights):
        shuffled[source][target]["weight"] = weight
    return shuffled


def main() -> None:
    rows: list[tuple] = []

    for year in YEARS:
        for layer in LAYERS:
            graph, voters, finalists = load_matrix(MATRIX_DIR / f"{year}_{layer}.csv")

            for scope in ("all", "finalists"):
                subgraph = graph if scope == "all" else graph.subgraph(finalists).copy()
                nodes = sorted(subgraph.nodes())
                undirected = weighted_projection(subgraph)
                density = nx.density(undirected)

                labels = louvain_labels(undirected, nodes)
                observed = modularity_of(undirected, labels, nodes)

                null = np.empty(N_NULL)
                for b in range(N_NULL):
                    sample = shuffle_weights(undirected)
                    null[b] = modularity_of(sample, louvain_labels(sample, nodes), nodes)

                mean = float(null.mean())
                sd = float(null.std(ddof=1))
                z = (observed - mean) / sd if sd else float("nan")
                p = (1 + int((null >= observed).sum())) / (1 + N_NULL)

                rows.append((
                    year, layer, scope, len(nodes), len(np.unique(labels)), density,
                    observed, mean, sd, observed - mean, z, p,
                ))

            print(f"{year}: {layer} modularity null computed")

    columns = [
        "year", "layer", "scope", "nodes", "communities", "density",
        "modularity", "null_mean", "null_sd", "excess", "z", "p_one_sided",
    ]
    save_csv(RESULTS_DIR / "rq2_modularity_null.csv", columns, rows)

    metrics = ["excess", "z"]
    differences = []
    for scope in ("all", "finalists"):
        for key in metrics:
            index = columns.index(key)
            jury = [r[index] for r in rows if r[1] == "jury" and r[2] == scope]
            public = [r[index] for r in rows if r[1] == "public" and r[2] == scope]
            observed, p = sign_flip_test(jury, public)
            differences.append((f"{key} ({scope})", observed, p))

    raw = [d[2] for d in differences]
    save_csv(
        RESULTS_DIR / "rq2_modularity_null_layer_diff.csv",
        ["metrica", "differenza_televoto_giurie", "p_esatto", "p_holm", "p_fdr"],
        [
            (label, observed, p, ph, pb)
            for (label, observed, p), ph, pb in zip(
                differences, holm(raw), benjamini_hochberg(raw)
            )
        ],
    )

    plot_modularity(rows)

    print(f"Results: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("Modularity null model complete.")


def plot_modularity(rows: list[tuple]) -> None:
    colors = {"jury": "#246b91", "public": "#cf7135"}
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), sharey=True)

    for ax, scope in zip(axes, ("all", "finalists")):
        positions = np.arange(len(YEARS))
        for offset, layer in zip((-0.2, 0.2), LAYERS):
            subset = [r for r in rows if r[1] == layer and r[2] == scope]
            observed = [r[6] for r in subset]
            mean = [r[7] for r in subset]
            sd = [r[8] for r in subset]
            ax.bar(positions + offset, observed, width=0.38, color=colors[layer],
                   label=f"{layer.title()} observed")
            ax.errorbar(
                positions + offset, mean, yerr=sd, fmt="o", color="#1b1b1b",
                markersize=3.5, capsize=2, linewidth=0.8, alpha=0.8,
            )

        ax.plot([], [], "o", color="#1b1b1b", markersize=3.5, label="Null mean ± sd")
        ax.set_xticks(positions, YEARS, rotation=45)
        ax.set_title("Full network" if scope == "all" else "Finalists only")
        ax.set_ylabel("Louvain modularity")
        ax.grid(axis="y", alpha=0.2)
        ax.legend(frameon=False, fontsize=8)

    fig.suptitle("RQ2 - Observed modularity against a weight-shuffling null")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "rq2_modularity_null.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, nx.NetworkXException) as exc:
        raise SystemExit(f"RQ2 modularity null failed: {exc}") from exc
