#!/usr/bin/env python3
"""RQ4 (step 1): do juries and televoting express the same structure in a year?

Run from the RQ4 directory:
    python src/analyze_rq4_layer_similarity.py

For each edition the two layers are compared on the dyads that are eligible
votes in both networks: the same voter could vote for the same recipient, and
the question is whether jury and public agree on that exchange.

Four quantities are reported:

* Spearman correlation of the points over all common dyads. It has to be read
  with care, because roughly half of the eligible cells are zeros in both
  layers, and agreement on zeros inflates it.
* Pearson correlation of the same points, for comparison.
* Pearson correlation after removing voter and recipient level effects. This is
  the strictest of the three: what remains is the part of the exchange that is
  not explained by how generous the voter is or by how popular the recipient
  is, i.e. the alignment of the actual pairings. If the layers only agreed on
  which countries are popular, this correlation would be near zero while the
  raw one stayed high.
* Jaccard similarity of the two sets of scores, which ignores the size of the
  scores and asks only whether the same pairs exchanged points at all.

All p-values are QAP: the country labels of one layer are permuted, rows and
columns together, 1000 times, and the statistic is recomputed on the cells that
remain eligible in both networks.

A fifth quantity is computed but kept secondary: the Spearman correlation
restricted to the dyads where both layers gave points. It answers "when both
agree that there is an exchange, do they agree on its size?", on a much smaller
and non-random subset.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rq4_common import (
    FIGURES_DIR,
    LAYERS,
    RESULTS_DIR,
    SEED,
    YEARS,
    high_p,
    load_year,
    qap,
    save_csv,
    two_sided_p,
)

N_PERM = 1000
COLOURS = {"jury": "#246b91", "public": "#cf7135"}


def plot(rows: list[dict], dyads: dict) -> None:
    positions = np.arange(len(YEARS))
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.9))

    for key, colour, label in (
        ("spearman", "#246b91", "Spearman, all common dyads"),
        ("residual_pearson", "#cf7135", "Pearson, voter and recipient effects removed"),
    ):
        axes[0].plot(positions, [r[key] for r in rows], "o-", color=colour, label=label)
    axes[0].fill_between(
        positions,
        [r["spearman_null_q025"] for r in rows],
        [r["spearman_null_q975"] for r in rows],
        color="#246b91", alpha=0.15, label="QAP 95% range, Spearman",
    )
    axes[0].fill_between(
        positions,
        [r["residual_pearson_null_q025"] for r in rows],
        [r["residual_pearson_null_q975"] for r in rows],
        color="#cf7135", alpha=0.15, label="QAP 95% range, residual Pearson",
    )
    axes[0].axhline(0, color="#666666", linewidth=0.8, linestyle=":")
    axes[0].set_xticks(positions, YEARS, rotation=45)
    axes[0].set_ylim(-0.15, 0.65)
    axes[0].set_ylabel("Correlation between the layers")
    axes[0].set_title("Agreement on the same dyads")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(axis="y", alpha=0.2)

    axes[1].plot(positions, [r["jaccard"] for r in rows], "o-", color="#6b8e23", label="Jaccard of positive dyads")
    axes[1].fill_between(
        positions,
        [r["jaccard_null_q025"] for r in rows],
        [r["jaccard_null_q975"] for r in rows],
        color="#999999", alpha=0.25, label="QAP 95% range",
    )
    axes[1].set_xticks(positions, YEARS, rotation=45)
    axes[1].set_ylim(0, 0.6)
    axes[1].set_ylabel("Jaccard")
    axes[1].set_title("Do the same pairs exchange points?")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].grid(axis="y", alpha=0.2)

    year, jury, public = dyads["year"], dyads["jury"], dyads["public"]
    grid = np.zeros((13, 13))
    for a, b in zip(jury.astype(int), public.astype(int)):
        grid[a, b] += 1
    image = axes[2].imshow(np.log10(grid + 1), cmap="Greys", origin="lower")
    axes[2].plot([0, 12], [0, 12], color="#cf7135", linestyle="--", linewidth=1)
    axes[2].set_xticks(range(0, 13, 2))
    axes[2].set_yticks(range(0, 13, 2))
    axes[2].set_xlabel("Jury points")
    axes[2].set_ylabel("Public points")
    axes[2].set_title(f"Every common dyad, {year} (log counts)")
    fig.colorbar(image, ax=axes[2], fraction=0.046, pad=0.04)

    fig.suptitle("RQ4 - Jury and public voting on the same dyads")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "rq4_layer_similarity.png", dpi=200)
    plt.close(fig)


def main() -> None:
    rng = np.random.default_rng(SEED)

    rows: list[dict] = []
    dyads: dict = {}

    for year in YEARS:
        matrices = load_year(year)
        jury_countries, jury_W, jury_E = matrices["jury"]
        public_countries, public_W, public_E = matrices["public"]
        if jury_countries != public_countries:
            raise ValueError(f"{year}: the two layers list different countries")
        mask = jury_E & public_E
        if not np.array_equal(jury_E, public_E):
            print(f"{year}: eligibility differs between layers, {int(mask.sum())} common cells")

        observed, null = qap(jury_W, public_W, mask, N_PERM, rng)

        row = {"year": year, "cells": int(observed["cells"]),
               "both_positive": int(observed["both_positive"])}
        for key in ("spearman", "pearson", "residual_pearson", "jaccard", "spearman_both_positive"):
            row[key] = observed[key]
            row[f"{key}_null_mean"] = float(np.nanmean(null[key]))
            row[f"{key}_null_q025"] = float(np.nanquantile(null[key], 0.025))
            row[f"{key}_null_q975"] = float(np.nanquantile(null[key], 0.975))
            row[f"{key}_p"] = (
                high_p(observed[key], null[key]) if key == "jaccard"
                else two_sided_p(observed[key], null[key])
            )
        rows.append(row)

        if year == YEARS[-1]:
            dyads = {
                "year": year,
                "jury": jury_W[mask],
                "public": public_W[mask],
            }
        print(f"{year}: {int(mask.sum())} common dyads, Spearman {observed['spearman']:.3f}", flush=True)

    columns = ["year", "cells", "both_positive"]
    for key in ("spearman", "pearson", "residual_pearson", "jaccard", "spearman_both_positive"):
        columns += [key, f"{key}_null_mean", f"{key}_null_q025", f"{key}_null_q975", f"{key}_p"]
    save_csv(RESULTS_DIR / "rq4_layer_similarity.csv", columns, [[r[c] for c in columns] for r in rows])

    plot(rows, dyads)

    print(f"Results: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("Layer similarity complete.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise SystemExit(f"RQ4 layer similarity failed: {exc}") from exc