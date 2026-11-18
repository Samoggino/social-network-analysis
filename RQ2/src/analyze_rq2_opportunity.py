#!/usr/bin/env python3
"""RQ2 (step 2): opportunity structure, margins and homophily tests.

Run from the RQ2 directory:
    python src/analyze_rq2_opportunity.py

This script does not replace analyze_rq2.py: it takes the same 20 matrices and
adds the three things the descriptive analysis was missing.

1. Opportunity correction. A country can only vote for the finalists that are
   in the contest, and some of them share its subregion. The expected share of
   same-region points under random selection is therefore not zero. For each
   voter v it equals |R_v| / |E_v|, where E_v are the eligible finalists and
   R_v those in the same subregion. Averaging over voters gives the benchmark
   against which the observed share is compared (excess ratio).

2. Extensive vs intensive margin. The extensive margin counts how often a
   same-region country enters the ten chosen ones; the intensive margin counts
   how many points it receives once chosen.

3. Null tests. Region and language labels are permuted across countries, which
   preserves the vote network and the size of every group, and the observed
   homophily is compared with the resulting distribution. The two voting levels
   are then compared with an exact paired sign-flip test over the ten years
   (2^10 = 1024 configurations), with Holm and Benjamini-Hochberg corrections.
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

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
SEED = 42
N_PERM = 1000

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
            attributes[row["country"].strip()] = {
                "region": row["region"].strip(),
                "language_groups": {g.strip() for g in row["language_groups"].split(";") if g.strip()},
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
            source = row[0]
            voters.append(source)
            for target, raw in zip(countries, row[1:]):
                if raw.strip() == "":
                    continue
                finalists.add(target)
                points = int(raw)
                if points:
                    graph.add_edge(source, target, weight=points)
    return graph, voters, finalists


def attr_key(kind: str) -> str:
    return "language_groups" if kind == "language" else kind


def same_attribute(a, b, kind: str) -> bool:
    if kind == "region":
        return bool(a) and a == b
    return bool(a & b)


def margin_stats(
    graph: nx.DiGraph,
    voters: list[str],
    finalists: set[str],
    attributes: dict[str, dict[str, object]],
    kind: str,
) -> dict[str, float]:
    """Extensive margin, intensive margin and the analytic benchmark."""
    obs_slots = 0.0
    exp_slots = 0.0
    points_total = 0.0
    points_same = 0.0
    chosen_same = 0
    chosen_other = 0
    points_chosen_same = 0.0
    points_chosen_other = 0.0

    for voter in voters:
        eligible = [t for t in finalists if t != voter]
        if not eligible:
            continue

        voter_value = attributes.get(voter, {}).get(attr_key(kind))
        same_set = {
            t for t in eligible
            if same_attribute(voter_value, attributes.get(t, {}).get(attr_key(kind)), kind)
        }

        chosen = {t: data["weight"] for _, t, data in graph.out_edges(voter, data=True)}

        obs_slots += sum(1 for t in chosen if t in same_set)
        exp_slots += len(same_set) / len(eligible)

        for target, points in chosen.items():
            points_total += points
            if target in same_set:
                points_same += points
                points_chosen_same += points
                chosen_same += 1
            else:
                points_chosen_other += points
                chosen_other += 1

    n_voters = len(voters)
    extensive_observed = obs_slots / (10 * n_voters)
    extensive_expected = exp_slots / n_voters

    return {
        "share_slots": extensive_observed,
        "share_slots_expected": extensive_expected,
        "slots_excess": (extensive_observed / extensive_expected) if extensive_expected else float("nan"),
        "share_points": points_same / points_total if points_total else float("nan"),
        "points_excess": (points_same / points_total / extensive_expected) if extensive_expected else float("nan"),
        "points_same_when_chosen": points_chosen_same / chosen_same if chosen_same else float("nan"),
        "points_other_when_chosen": points_chosen_other / chosen_other if chosen_other else float("nan"),
        "points_gap": (
            points_chosen_same / chosen_same - points_chosen_other / chosen_other
            if chosen_same and chosen_other else float("nan")
        ),
    }


def label_matrices(
    nodes: list[str],
    attributes: dict[str, dict[str, object]],
    kind: str,
) -> np.ndarray:
    """Region: one integer per node. Language: a 0/1 matrix node x group."""
    if kind == "region":
        values = sorted({attributes.get(n, {}).get("region", "") for n in nodes})
        index = {v: i for i, v in enumerate(values)}
        return np.array([index[attributes.get(n, {}).get("region", "")] for n in nodes])

    groups = sorted({g for n in nodes for g in attributes.get(n, {}).get("language_groups", set())})
    index = {g: i for i, g in enumerate(groups)}
    matrix = np.zeros((len(nodes), len(groups)), dtype=bool)
    for row, node in enumerate(nodes):
        for group in attributes.get(node, {}).get("language_groups", set()):
            matrix[row, index[group]] = True
    return matrix


def permutation_null(
    graph: nx.DiGraph,
    voters: list[str],
    finalists: set[str],
    attributes: dict[str, dict[str, object]],
    kind: str,
    n_perm: int = N_PERM,
) -> dict[str, np.ndarray]:
    """Permute region/language labels across countries and recompute homophily.

    Permuting labels preserves the vote network and the size of every group, so
    the null answers one question only: do votes follow the labels more than a
    random assignment of the same labels would?
    """
    nodes = sorted(graph.nodes())
    position = {node: i for i, node in enumerate(nodes)}
    n = len(nodes)

    labels = label_matrices(nodes, attributes, kind)
    eligible = np.zeros((n, n), dtype=bool)
    for voter in voters:
        i = position[voter]
        for target in finalists:
            if target != voter:
                eligible[i, position[target]] = True
    eligible_count = eligible.sum(axis=1)

    edges = [(position[s], position[t], d["weight"]) for s, t, d in graph.edges(data=True)]
    edge_i = np.array([e[0] for e in edges])
    edge_j = np.array([e[1] for e in edges])
    edge_w = np.array([e[2] for e in edges], dtype=float)

    points_null = np.empty(n_perm)
    slots_null = np.empty(n_perm)
    slots_expected = np.empty(n_perm)

    for b in range(n_perm):
        order = RNG.permutation(n)
        permuted = labels[order]

        if kind == "region":
            equal = permuted[edge_i] == permuted[edge_j]
            pair_matrix = permuted[:, None] == permuted[None, :]
        else:
            equal = (permuted[edge_i] & permuted[edge_j]).any(axis=1)
            pair_matrix = (permuted.astype(np.int8) @ permuted.astype(np.int8).T) > 0

        total = edge_w.sum()
        points_null[b] = edge_w[equal].sum() / total
        slots_null[b] = equal.sum() / (10 * len(voters))
        same_eligible = (pair_matrix & eligible).sum(axis=1)
        slots_expected[b] = float(np.mean(same_eligible / eligible_count))

    return {
        "points_null": points_null,
        "slots_null": slots_null,
        "slots_expected_null": slots_expected,
    }


def p_value(observed: float, null: np.ndarray) -> tuple[float, float, float]:
    """One-sided p (greater), z-score and null mean."""
    mean = float(null.mean())
    sd = float(null.std(ddof=1))
    p = (1 + int((null >= observed).sum())) / (1 + len(null))
    z = (observed - mean) / sd if sd else float("nan")
    return p, z, mean


def holm(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, index in enumerate(order):
        value = min(1.0, (m - rank) * pvalues[index])
        running = max(running, value)
        adjusted[index] = running
    return adjusted


def benjamini_hochberg(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i], reverse=True)
    adjusted = [0.0] * m
    running = 1.0
    for rank, index in enumerate(order):
        value = min(1.0, pvalues[index] * m / (m - rank))
        running = min(running, value)
        adjusted[index] = running
    return adjusted


def sign_flip_test(jury: list[float], public: list[float]) -> tuple[float, float]:
    """Exact paired test over the ten years: swap the two layers within a year."""
    differences = np.array(public) - np.array(jury)
    observed = float(differences.mean())
    k = len(differences)
    stats = []
    for signs in itertools.product((1, -1), repeat=k):
        stats.append(float(np.mean(differences * np.array(signs))))
    stats = np.array(stats)
    p = float((np.abs(stats) >= abs(observed) - 1e-12).mean())
    return observed, p


def plot_opportunity(summary: list[dict]) -> None:
    index = {(row["year"], row["layer"]): row for row in summary}

    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    positions = np.arange(len(YEARS))
    colors = {"jury": "#246b91", "public": "#cf7135"}

    for offset, layer in zip((-0.2, 0.2), LAYERS):
        observed = [index[(y, layer)]["share_slots_region"] for y in YEARS]
        axes[0].bar(
            positions + offset, observed, width=0.38,
            color=colors[layer], label=f"{layer.title()} observed",
        )

    expected = [index[(y, "jury")]["share_slots_expected_region"] for y in YEARS]
    axes[0].plot(
        positions, expected, color="#3b3b3b", marker="D", linestyle="--",
        linewidth=1.4, markersize=5, label="Expected under random choice",
    )
    axes[0].set_xticks(positions, YEARS, rotation=45)
    axes[0].set_ylabel("Share of the ten chosen countries")
    axes[0].set_title("Extensive margin: same subregion among the ten chosen")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(axis="y", alpha=0.2)

    for offset, layer in zip((-0.2, 0.2), LAYERS):
        same = [index[(y, layer)]["points_same_when_chosen_region"] for y in YEARS]
        other = [index[(y, layer)]["points_other_when_chosen_region"] for y in YEARS]
        axes[1].plot(
            positions + offset, same, marker="o", color=colors[layer],
            label=f"{layer.title()} - same subregion",
        )
        axes[1].plot(
            positions + offset, other, marker="o", linestyle="--", color=colors[layer],
            alpha=0.55, label=f"{layer.title()} - other subregions",
        )

    axes[1].set_xticks(positions, YEARS, rotation=45)
    axes[1].set_ylabel("Mean points, conditional on being chosen")
    axes[1].set_title("Intensive margin: points given once a country is chosen")
    axes[1].legend(frameon=False, fontsize=7, ncol=2)
    axes[1].grid(axis="y", alpha=0.2)

    fig.suptitle("RQ2 - Opportunity correction and the two margins")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "rq2_opportunity.png", dpi=200)
    plt.close(fig)


def main() -> None:
    attributes = load_attributes(ATTR_PATH)

    summary: list[dict] = []
    test_rows: list[tuple] = []

    for year in YEARS:
        for layer in LAYERS:
            graph, voters, finalists = load_matrix(MATRIX_DIR / f"{year}_{layer}.csv")

            row: dict[str, object] = {"year": year, "layer": layer}

            for kind in ("region", "language"):
                stats = margin_stats(graph, voters, finalists, attributes, kind)
                for key, value in stats.items():
                    row[f"{key}_{kind}"] = value

                null = permutation_null(graph, voters, finalists, attributes, kind)

                p_points, z_points, mean_points = p_value(row[f"share_points_{kind}"], null["points_null"])
                test_rows.append((
                    year, layer, kind, "share_points",
                    row[f"share_points_{kind}"], mean_points, z_points, p_points,
                ))

                p_slots, z_slots, mean_slots = p_value(row[f"share_slots_{kind}"], null["slots_null"])
                test_rows.append((
                    year, layer, kind, "share_slots",
                    row[f"share_slots_{kind}"], mean_slots, z_slots, p_slots,
                ))

            summary.append(row)
            print(f"{year}: {layer} opportunity structure analyzed")

    columns = ["year", "layer"]
    for kind in ("region", "language"):
        columns += [f"{key}_{kind}" for key in (
            "share_slots", "share_slots_expected", "slots_excess", "share_points",
            "points_excess", "points_same_when_chosen", "points_other_when_chosen", "points_gap",
        )]

    save_csv(
        RESULTS_DIR / "rq2_opportunity.csv",
        columns,
        [[row[c] for c in columns] for row in summary],
    )

    # Correct within each family of 20 tests (10 years x 2 layers).
    corrected = []
    families: dict[tuple[str, str], list[int]] = {}
    for index, row in enumerate(test_rows):
        families.setdefault((row[2], row[3]), []).append(index)

    adjusted = [0.0] * len(test_rows)
    adjusted_bh_tests = [0.0] * len(test_rows)
    for indices in families.values():
        values = [test_rows[i][7] for i in indices]
        for i, value in zip(indices, holm(values)):
            adjusted[i] = value
        for i, value in zip(indices, benjamini_hochberg(values)):
            adjusted_bh_tests[i] = value

    for row, ph, pb in zip(test_rows, adjusted, adjusted_bh_tests):
        corrected.append(tuple(row) + (ph, pb))

    save_csv(
        RESULTS_DIR / "rq2_homophily_tests.csv",
        [
            "year", "layer", "attribute", "statistic", "observed", "null_mean", "z",
            "p_one_sided", "p_holm", "p_fdr",
        ],
        corrected,
    )

    # Paired comparison between the two levels, year by year.
    metrics = [
        ("share_slots_region", "quota di scelte nella stessa sottoregione"),
        ("share_points_region", "quota di punti alla stessa sottoregione"),
        ("points_gap_region", "margine intensivo, sottoregione"),
        ("share_slots_language", "quota di scelte con lingua condivisa"),
        ("share_points_language", "quota di punti a lingua condivisa"),
        ("points_gap_language", "margine intensivo, lingua"),
    ]

    differences = []
    raw_p = []
    for key, label in metrics:
        jury = [row[key] for row in summary if row["layer"] == "jury"]
        public = [row[key] for row in summary if row["layer"] == "public"]
        observed, p = sign_flip_test(jury, public)
        differences.append((label, observed, p))
        raw_p.append(p)

    adjusted_holm = holm(raw_p)
    adjusted_bh = benjamini_hochberg(raw_p)

    save_csv(
        RESULTS_DIR / "rq2_layer_differences.csv",
        ["metrica", "differenza_televoto_giurie", "p_esatto", "p_holm", "p_fdr"],
        [
            (label, observed, p, ph, pb)
            for (label, observed, p), ph, pb in zip(differences, adjusted_holm, adjusted_bh)
        ],
    )

    plot_opportunity(summary)

    print(f"Results: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("Opportunity correction and homophily tests complete.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, nx.NetworkXException) as exc:
        raise SystemExit(f"RQ2 opportunity analysis failed: {exc}") from exc
