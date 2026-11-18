#!/usr/bin/env python3
"""RQ2 (step 6): does language matter once geography is held constant?

Run from the RQ2 directory:
    python src/analyze_rq2_language_within.py

The previous steps found a mild linguistic homophily: about 24% of the choices
go to a country sharing a language with the voter, against an expected 20% under
random choice. But language families are strongly clustered in space, so that
number may be nothing more than geography seen through a different label.

The test here removes the geographic channel by construction: for every voter,
only finalists from *other* subregions are kept as eligible, and only the
choices falling on those finalists are counted. The benchmark is then the share
of eligible countries that share a language, which is computed for every voter
and averaged. If language has an effect of its own, the observed share must
exceed that benchmark; if the effect is only geography, the two coincide.

The two voting levels are compared with the same exact paired sign-flip test
used in the other steps.
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
    YEARS,
    benjamini_hochberg,
    holm,
    load_matrix,
    sign_flip_test,
)

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
                "language_groups": {
                    group.strip()
                    for group in row["language_groups"].split(";")
                    if group.strip()
                },
            }
    return attributes


def cross_region_stats(
    graph: nx.DiGraph,
    voters: list[str],
    finalists: set[str],
    attributes: dict[str, dict[str, object]],
) -> dict[str, float]:
    """Language homophily restricted to pairs from different subregions."""
    chosen_same = 0
    chosen_other = 0
    points_same = 0
    points_other = 0
    slots_expected = 0.0
    voters_count = 0

    for voter in voters:
        voter_languages = attributes.get(voter, {}).get("language_groups", set())
        voter_region = attributes.get(voter, {}).get("region", "")

        eligible = [
            target for target in finalists
            if target != voter
            and attributes.get(target, {}).get("region", "") != voter_region
        ]
        if not eligible:
            continue

        voters_count += 1
        shared = {
            target for target in eligible
            if voter_languages & attributes.get(target, {}).get("language_groups", set())
        }
        slots_expected += len(shared) / len(eligible)

        for _, target, data in graph.out_edges(voter, data=True):
            if target not in eligible:
                continue
            if target in shared:
                chosen_same += 1
                points_same += data["weight"]
            else:
                chosen_other += 1
                points_other += data["weight"]

    expected = slots_expected / voters_count if voters_count else float("nan")
    slots_total = chosen_same + chosen_other

    return {
        "voters": voters_count,
        "share_slots": chosen_same / slots_total if slots_total else float("nan"),
        "share_slots_expected": expected,
        "slots_excess": (chosen_same / slots_total / expected) if slots_total and expected else float("nan"),
        "share_points": points_same / (points_same + points_other)
        if (points_same + points_other) else float("nan"),
        "points_excess": (points_same / (points_same + points_other) / expected)
        if (points_same + points_other) and expected else float("nan"),
        "points_same_when_chosen": points_same / chosen_same if chosen_same else float("nan"),
        "points_other_when_chosen": points_other / chosen_other if chosen_other else float("nan"),
        "points_gap": (points_same / chosen_same - points_other / chosen_other)
        if chosen_same and chosen_other else float("nan"),
    }


def plot_within(rows: list[dict]) -> None:
    index = {(row["year"], row["layer"]): row for row in rows}
    positions = np.arange(len(YEARS))
    colors = {"jury": "#246b91", "public": "#cf7135"}

    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8))

    for ax, key, title, ylabel in (
        (axes[0], "share_slots", "Extensive margin: choices", "Share of choices to a shared language"),
        (axes[1], "share_points", "Intensive weight: points", "Share of points to a shared language"),
    ):
        for offset, layer in zip((-0.15, 0.15), LAYERS):
            values = [index[(y, layer)][key] for y in YEARS]
            ax.plot(
                positions + offset, values, marker="o", color=colors[layer],
                label=f"{layer.title()} observed",
            )

        expected = [index[(y, "jury")]["share_slots_expected"] for y in YEARS]
        ax.plot(
            positions, expected, color="#3b3b3b", linestyle="--", marker="D",
            markersize=4, linewidth=1.2, label="Expected, same-region pairs excluded",
        )
        ax.set_xticks(positions, YEARS, rotation=45)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.2)
        ax.legend(frameon=False, fontsize=8)

    fig.suptitle("RQ2 - Language homophily with geography held constant")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "rq2_language_within.png", dpi=200)
    plt.close(fig)


def main() -> None:
    attributes = load_attributes(ATTR_PATH)

    summary: list[dict] = []

    for year in YEARS:
        for layer in LAYERS:
            graph, voters, finalists = load_matrix(MATRIX_DIR / f"{year}_{layer}.csv")
            stats = cross_region_stats(graph, voters, finalists, attributes)
            summary.append({"year": year, "layer": layer, **stats})
            print(f"{year}: {layer} cross-region language test computed")

    columns = [
        "year", "layer", "voters", "share_slots", "share_slots_expected", "slots_excess",
        "share_points", "points_excess", "points_same_when_chosen",
        "points_other_when_chosen", "points_gap",
    ]
    save_csv(
        RESULTS_DIR / "rq2_language_within.csv",
        columns,
        [[row[c] for c in columns] for row in summary],
    )

    metrics = [
        ("share_slots", "quota di scelte a lingua condivisa, fuori sottoregione"),
        ("share_points", "quota di punti a lingua condivisa, fuori sottoregione"),
        ("points_gap", "margine intensivo lingua, fuori sottoregione"),
    ]

    differences = []
    for key, label in metrics:
        jury = [row[key] for row in summary if row["layer"] == "jury"]
        public = [row[key] for row in summary if row["layer"] == "public"]
        observed, p = sign_flip_test(jury, public)
        differences.append((label, observed, p))

    raw = [d[2] for d in differences]
    save_csv(
        RESULTS_DIR / "rq2_language_within_layer_diff.csv",
        ["metrica", "differenza_televoto_giurie", "p_esatto", "p_holm", "p_fdr"],
        [
            (label, observed, p, ph, pb)
            for (label, observed, p), ph, pb in zip(
                differences, holm(raw), benjamini_hochberg(raw)
            )
        ],
    )

    plot_within(summary)

    print(f"Results: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("Cross-region language analysis complete.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, nx.NetworkXException) as exc:
        raise SystemExit(f"RQ2 cross-region language analysis failed: {exc}") from exc
