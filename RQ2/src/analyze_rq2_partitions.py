#!/usr/bin/env python3
"""RQ2 (step 3): do the detected communities correspond to regions and languages?

Run from the RQ2 directory:
    python src/analyze_rq2_partitions.py

The previous steps measured how many points travel inside a subregion. This
script answers the other half of the question: do the communities found by
Louvain coincide with the geographic and linguistic groups?

Three things are computed for every one of the 20 networks.

1. NMI and ARI between the Louvain partition and (a) UN M49 subregions,
   (b) the primary language family, (c) the Eurovision cultural block used as a
   sensitivity check. NMI is not corrected for chance, ARI is: they are reported
   together because they answer slightly different questions and disagree when
   the partitions have different numbers of groups.

2. A permutation benchmark. Region labels are shuffled across countries, the
   partition is kept fixed, and NMI/ARI are recomputed. This shows how much
   agreement is produced by the group sizes alone, which is the only honest
   term of comparison for NMI.

3. Stability of the partition itself. Louvain is rerun over many seeds and over
   three resolutions; the mean pairwise ARI between runs and the co-assignment
   matrix say whether a single run can be read as "the" community structure.
"""

from __future__ import annotations

import csv
import itertools
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from flags import flag_markers, flag_ticks  # noqa: E402  country flags in the figures

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
SEED = 42
N_PERM = 500
N_SEEDS = 100
N_PAIR_SAMPLES = 240  # 240 random pairs per network/resolution for practical runtime
RESOLUTIONS = (0.8, 1.0, 1.2)

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


def load_attributes(path: Path) -> dict[str, dict[str, object]]:
    attributes = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            groups = [g.strip() for g in row["language_groups"].split(";") if g.strip()]
            attributes[row["country"].strip()] = {
                "region": row["region"].strip(),
                "language": groups[0] if groups else "",  # primary family only (single-label NMI/ARI)
                "block": row["eurovision_block"].strip(),
            }
    return attributes


def load_matrix(path: Path) -> tuple[nx.DiGraph, list[str], set[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        countries = header[1:]
        graph = nx.DiGraph()
        graph.add_nodes_from(countries)
        voters = []
        finalists: set[str] = set()
        for row in reader:
            voters.append(row[0])
            for target, raw in zip(countries, row[1:]):
                if raw.strip() == "":
                    continue
                finalists.add(target)
                points = int(raw)
                if points:
                    graph.add_edge(row[0], target, weight=points)
    return graph, voters, finalists


def weighted_projection(graph: nx.DiGraph) -> nx.Graph:
    undirected = nx.Graph()
    undirected.add_nodes_from(graph.nodes())
    for source, target, data in graph.edges(data=True):
        weight = data["weight"]
        if undirected.has_edge(source, target):
            undirected[source][target]["weight"] += weight
        else:
            undirected.add_edge(source, target, weight=weight)
    return undirected


# --------------------------------------------------------------------------
# Agreement between two partitions
# --------------------------------------------------------------------------


def contingency(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    rows, row_index = np.unique(first, return_inverse=True)
    cols, col_index = np.unique(second, return_inverse=True)
    table = np.zeros((len(rows), len(cols)), dtype=float)
    np.add.at(table, (row_index, col_index), 1.0)
    return table


def agreement_from_table(table: np.ndarray) -> tuple[float, float]:
    """Return (NMI, ARI) from a contingency table, without recomputing it."""
    n = table.sum()
    if n < 2:
        return float("nan"), float("nan")

    def pairs(x: np.ndarray) -> float:
        return float((x * (x - 1) / 2).sum())

    index = pairs(table)
    rows = pairs(table.sum(axis=1))
    cols = pairs(table.sum(axis=0))
    expected = rows * cols / (n * (n - 1) / 2)
    maximum = (rows + cols) / 2
    if maximum == expected:
        ari = 1.0 if index == expected else 0.0
    else:
        ari = (index - expected) / (maximum - expected)

    joint = table / n
    pa = joint.sum(axis=1, keepdims=True)
    pb = joint.sum(axis=0, keepdims=True)
    product = pa @ pb
    mask = joint > 0
    mutual = float((joint[mask] * np.log(joint[mask] / product[mask])).sum())

    p_a = pa[pa > 0].ravel()
    p_b = pb[pb > 0].ravel()
    entropy_a = float(-(p_a * np.log(p_a)).sum())
    entropy_b = float(-(p_b * np.log(p_b)).sum())
    denominator = (entropy_a + entropy_b) / 2
    nmi = 1.0 if denominator == 0 else mutual / denominator

    return nmi, ari


def adjusted_rand(first: np.ndarray, second: np.ndarray) -> float:
    return agreement_from_table(contingency(first, second))[1]


def normalized_mutual_information(first: np.ndarray, second: np.ndarray) -> float:
    return agreement_from_table(contingency(first, second))[0]



def sign_flip_test(jury: list[float], public: list[float]) -> tuple[float, float]:
    """Exact paired test over the ten years: swap the two layers within a year."""
    differences = np.array(public) - np.array(jury)
    observed = float(differences.mean())
    stats = [
        float(np.mean(differences * np.array(signs)))
        for signs in itertools.product((1, -1), repeat=len(differences))
    ]
    p = float((np.abs(np.array(stats)) >= abs(observed) - 1e-12).mean())
    return observed, p


def holm(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[index]))
        adjusted[index] = running
    return adjusted


def benjamini_hochberg(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i], reverse=True)
    adjusted = [0.0] * m
    running = 1.0
    for rank, index in enumerate(order):
        running = min(running, min(1.0, pvalues[index] * m / (m - rank)))
        adjusted[index] = running
    return adjusted


# --------------------------------------------------------------------------
# Louvain partitions
# --------------------------------------------------------------------------


def louvain_labels(
    undirected: nx.Graph,
    nodes: list[str],
    seed: int = SEED,
    resolution: float = 1.0,
) -> np.ndarray:
    communities = nx.community.louvain_communities(
        undirected, weight="weight", seed=seed, resolution=resolution
    )
    position = {node: i for i, node in enumerate(nodes)}
    labels = np.zeros(len(nodes), dtype=int)
    for index, community in enumerate(communities):
        for node in community:
            labels[position[node]] = index
    return labels


def attribute_labels(nodes: list[str], attributes, key: str) -> np.ndarray:
    values = [attributes.get(node, {}).get(key, "") for node in nodes]
    _, index = np.unique(values, return_inverse=True)
    return index


# --------------------------------------------------------------------------
# Stability
# --------------------------------------------------------------------------


def stability(
    undirected: nx.Graph,
    nodes: list[str],
    resolution: float,
) -> tuple[float, np.ndarray, float, float]:
    partitions = [
        louvain_labels(undirected, nodes, seed=seed, resolution=resolution)
        for seed in range(N_SEEDS)
    ]

    co_assignment = np.zeros((len(nodes), len(nodes)))
    sizes = []
    for labels in partitions:
        co_assignment += labels[:, None] == labels[None, :]
        sizes.append(len(np.unique(labels)))
    co_assignment /= N_SEEDS

    indices = RNG.integers(0, N_SEEDS, size=(N_PAIR_SAMPLES, 2))
    values = [
        adjusted_rand(partitions[i], partitions[j])
        for i, j in indices if i != j
    ]

    return float(np.mean(values)), co_assignment, float(np.mean(sizes)), float(np.std(sizes))


def plot_agreement(rows: list[dict]) -> None:
    index = {(row["year"], row["layer"], row["scope"]): row for row in rows}
    positions = np.arange(len(YEARS))
    colors = {"jury": "#246b91", "public": "#cf7135"}

    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8))

    for ax, key, title in (
        (axes[0], "nmi_region", "NMI with UN M49 subregions"),
        (axes[1], "ari_region", "ARI with UN M49 subregions"),
    ):
        for offset, layer in zip((-0.15, 0.15), LAYERS):
            values = [index[(year, layer, "all")][key] for year in YEARS]
            ax.plot(positions + offset, values, marker="o", color=colors[layer], label=layer.title())

        null = [index[(year, "jury", "all")][key + "_null"] for year in YEARS]
        ax.plot(
            positions, null, color="#3b3b3b", linestyle="--", marker="D",
            markersize=4, linewidth=1.2, label="Permutation benchmark",
        )

        ax.set_xticks(positions, YEARS, rotation=45)
        ax.set_title(title)
        ax.set_ylabel("Agreement with the geographic partition")
        ax.grid(axis="y", alpha=0.2)
        ax.legend(frameon=False, fontsize=8)

    fig.suptitle("RQ2 - Do Louvain communities match geography?")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "rq2_partition_agreement.png", dpi=200)
    plt.close(fig)


def plot_stability(
    year: int, layer: str, nodes: list[str], matrix: np.ndarray, ari: float,
    reference: np.ndarray,
) -> None:
    """Order the matrix by the reference partition so blocks become visible."""
    order = np.lexsort((np.array(nodes), reference))
    matrix = matrix[np.ix_(order, order)]
    labels = [nodes[i] for i in order]

    fig, ax = plt.subplots(figsize=(9, 8))
    image = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=90, fontsize=6)
    ax.set_yticks(range(len(labels)), labels, fontsize=6)
    flag_ticks(ax, labels, "x", height_pt=5.5)
    flag_ticks(ax, labels, "y", height_pt=5.5)
    ax.set_title(
        f"Co-assignment over {N_SEEDS} Louvain seeds - {year} {layer} "
        f"(mean pairwise ARI {ari:.2f})",
        fontsize=11,
    )
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Share of runs in the same community")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f"rq2_stability_{year}_{layer}.png", dpi=200)
    plt.close(fig)


def main() -> None:
    attributes = load_attributes(ATTR_PATH)

    agreement: list[dict] = []
    tests: list[tuple] = []
    stability_rows: list[tuple] = []

    for year in YEARS:
        for layer in LAYERS:
            graph, voters, finalists = load_matrix(MATRIX_DIR / f"{year}_{layer}.csv")

            for scope in ("all", "finalists"):
                subgraph = graph if scope == "all" else graph.subgraph(finalists).copy()
                nodes = sorted(subgraph.nodes())
                undirected = weighted_projection(subgraph)

                labels = louvain_labels(undirected, nodes)

                row: dict[str, object] = {
                    "year": year,
                    "layer": layer,
                    "scope": scope,
                    "nodes": len(nodes),
                    "communities": len(np.unique(labels)),
                    "modularity": nx.community.modularity(
                        undirected,
                        [set(np.array(nodes)[labels == c]) for c in np.unique(labels)],
                        weight="weight",
                    ),
                }

                for key in ("region", "language", "block"):
                    truth = attribute_labels(nodes, attributes, key)
                    nmi = normalized_mutual_information(labels, truth)
                    ari = adjusted_rand(labels, truth)

                    null_nmi = np.empty(N_PERM)
                    null_ari = np.empty(N_PERM)
                    for b in range(N_PERM):
                        shuffled = RNG.permutation(truth)
                        null_nmi[b], null_ari[b] = agreement_from_table(contingency(labels, shuffled))

                    row[f"nmi_{key}"] = nmi
                    row[f"ari_{key}"] = ari
                    row[f"nmi_{key}_null"] = float(null_nmi.mean())
                    row[f"ari_{key}_null"] = float(null_ari.mean())

                    p_nmi = (1 + int((null_nmi >= nmi).sum())) / (1 + N_PERM)
                    p_ari = (1 + int((null_ari >= ari).sum())) / (1 + N_PERM)
                    tests.append((year, layer, scope, key, "nmi", nmi, float(null_nmi.mean()), p_nmi))
                    tests.append((year, layer, scope, key, "ari", ari, float(null_ari.mean()), p_ari))

                agreement.append(row)

                for resolution in RESOLUTIONS:
                    mean_ari, co_assignment, mean_size, sd_size = stability(
                        undirected, nodes, resolution
                    )
                    stability_rows.append((
                        year, layer, scope, resolution, mean_ari, mean_size, sd_size
                    ))

                    if year == 2016 and resolution == 1.0:
                        plot_stability(2016, f"{layer}_{scope}", nodes, co_assignment, mean_ari, labels)

            print(f"{year}: {layer} partitions analyzed")

    columns = [
        "year", "layer", "scope", "nodes", "communities", "modularity",
        "nmi_region", "nmi_region_null", "ari_region", "ari_region_null",
        "nmi_language", "nmi_language_null", "ari_language", "ari_language_null",
        "nmi_block", "nmi_block_null", "ari_block", "ari_block_null",
    ]
    save_csv(RESULTS_DIR / "rq2_partitions.csv", columns, [[r[c] for c in columns] for r in agreement])
    save_csv(
        RESULTS_DIR / "rq2_partition_tests.csv",
        ["year", "layer", "scope", "attribute", "statistic", "observed", "null_mean", "p_one_sided"],
        tests,
    )
    save_csv(
        RESULTS_DIR / "rq2_stability.csv",
        ["year", "layer", "scope", "resolution", "mean_pairwise_ari", "mean_communities", "sd_communities"],
        stability_rows,
    )

    # Paired comparison between the two levels, year by year.
    metrics = [
        ("nmi_region", "NMI con le sottoregioni"),
        ("ari_region", "ARI con le sottoregioni"),
        ("nmi_language", "NMI con le famiglie linguistiche"),
        ("ari_language", "ARI con le famiglie linguistiche"),
        ("nmi_block", "NMI con i blocchi culturali"),
        ("ari_block", "ARI con i blocchi culturali"),
    ]

    differences = []
    for scope in ("all", "finalists"):
        for key, label in metrics:
            jury = [row[key] for row in agreement if row["layer"] == "jury" and row["scope"] == scope]
            public = [row[key] for row in agreement if row["layer"] == "public" and row["scope"] == scope]
            observed, p = sign_flip_test(jury, public)
            differences.append((f"{label} ({scope})", observed, p))

    adjusted_holm = holm([d[2] for d in differences])
    adjusted_bh = benjamini_hochberg([d[2] for d in differences])

    save_csv(
        RESULTS_DIR / "rq2_partition_layer_diff.csv",
        ["metrica", "differenza_televoto_giurie", "p_esatto", "p_holm", "p_fdr"],
        [
            (label, observed, p, ph, pb)
            for (label, observed, p), ph, pb in zip(differences, adjusted_holm, adjusted_bh)
        ],
    )

    plot_agreement(agreement)

    print(f"Results: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("Partition agreement and stability complete.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, nx.NetworkXException) as exc:
        raise SystemExit(f"RQ2 partition analysis failed: {exc}") from exc
