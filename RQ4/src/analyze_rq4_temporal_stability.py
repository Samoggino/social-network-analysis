#!/usr/bin/env python3
"""RQ4 (step 2): is a voting pattern stable across editions?

Run from the RQ4 directory:
    python src/analyze_rq4_temporal_stability.py

The first RQ4 script compares the two layers within an edition. This one puts
the same layer next to itself in different editions and asks how much of the
dyadic pattern survives.

For every pair of editions with a given lag (1 to 9 editions) the two networks are
aligned on the countries present in both, and the comparison is computed on the
dyads that were eligible votes in both editions:

* Spearman and Pearson correlation of the points;
* Pearson correlation after removing voter and recipient effects, so that a
  country that is always popular does not by itself make the pattern look
  stable;
* Jaccard similarity of the two sets of scores.

The statistic reported for a lag is the mean over the edition pairs with that
lag. Its p-value comes from a null that permutes the country labels of one year
independently inside each pair and then averages in the same way, so the null
refers to the mean statistic and not to a single pair.

The lag-1 comparison between jury and public is tested with the exact paired
sign-flip test over the nine consecutive pairs of editions.

RQ1 already measures the persistence of individual reciprocal pairs and of
triadic configurations with a temporal null model. The unit here is different:
whole matrices, weighted, with voter and recipient effects removed. The two
analyses answer different questions and are meant to be read together.
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
    sign_flip_test,
    two_sided_p,
)

N_PERM = 500
MAX_LAG = len(YEARS) - 1
KEYS = ("spearman", "pearson", "residual_pearson", "jaccard")
COLOURS = {"jury": "#246b91", "public": "#cf7135"}


def aligned(year_a: int, year_b: int, layer: str):
    """Two networks of the same layer, restricted to the countries they share."""
    countries_a, W_a, E_a = load_year(year_a)[layer]
    countries_b, W_b, E_b = load_year(year_b)[layer]
    common = [c for c in countries_a if c in countries_b]
    ia = [countries_a.index(c) for c in common]
    ib = [countries_b.index(c) for c in common]
    return (
        W_a[np.ix_(ia, ia)], E_a[np.ix_(ia, ia)],
        W_b[np.ix_(ib, ib)], E_b[np.ix_(ib, ib)],
    )


def main() -> None:
    rng = np.random.default_rng(SEED)

    pair_rows: list[dict] = []
    lag_rows: list[list] = []
    summary: dict[tuple[str, int, str], dict] = {}
    heatmaps: dict[str, np.ndarray] = {}

    for layer in LAYERS:
        heat = np.full((len(YEARS), len(YEARS)), np.nan)
        for position in range(len(YEARS)):
            heat[position, position] = 1.0

        for lag in range(1, MAX_LAG + 1):
            observed_by_key = {key: [] for key in KEYS}
            null_by_key = {key: [] for key in KEYS}

            for start in range(len(YEARS) - lag):
                year_a, year_b = YEARS[start], YEARS[start + lag]
                W_a, E_a, W_b, E_b = aligned(year_a, year_b, layer)
                observed, null = qap(W_a, W_b, E_a & E_b, N_PERM, rng)
                for key in KEYS:
                    observed_by_key[key].append(observed[key])
                    null_by_key[key].append(null[key])
                pair_rows.append({
                    "layer": layer, "lag": lag, "year_a": year_a, "year_b": year_b,
                    "cells": int(observed["cells"]),
                    **{key: observed[key] for key in KEYS},
                })
                heat[YEARS.index(year_a), YEARS.index(year_b)] = observed["spearman"]
                heat[YEARS.index(year_b), YEARS.index(year_a)] = observed["spearman"]

            for key in KEYS:
                mean_observed = float(np.nanmean(observed_by_key[key]))
                mean_null = np.nanmean(np.vstack(null_by_key[key]), axis=0)
                p = high_p(mean_observed, mean_null) if key == "jaccard" else two_sided_p(mean_observed, mean_null)
                lag_rows.append([
                    layer, lag, key, len(observed_by_key[key]), mean_observed,
                    float(np.nanmean(mean_null)), float(np.nanquantile(mean_null, 0.025)),
                    float(np.nanquantile(mean_null, 0.975)), p,
                ])
                summary[layer, lag, key] = {
                    "mean": mean_observed, "p": p,
                    "low": float(np.nanquantile(mean_null, 0.025)),
                    "high": float(np.nanquantile(mean_null, 0.975)),
                }
            print(f"{layer}: lag {lag} computed", flush=True)

        heatmaps[layer] = heat

    save_csv(
        RESULTS_DIR / "rq4_temporal_stability.csv",
        ["layer", "lag", "statistic", "pairs", "mean", "null_mean", "null_q025", "null_q975", "p"],
        lag_rows,
    )
    save_csv(
        RESULTS_DIR / "rq4_temporal_pairs.csv",
        ["layer", "lag", "year_a", "year_b", "cells"] + list(KEYS),
        [[r[c] for c in ("layer", "lag", "year_a", "year_b", "cells") + KEYS] for r in pair_rows],
    )

    # Jury vs public, paired over the nine consecutive pairs of editions.
    differences = []
    for key in ("spearman", "residual_pearson", "jaccard"):
        jury, public = [], []
        for year_a, year_b in zip(YEARS, YEARS[1:]):
            for row in pair_rows:
                if (row["layer"] == "jury" and row["lag"] == 1
                        and row["year_a"] == year_a and row["year_b"] == year_b):
                    jury.append(row[key])
                if (row["layer"] == "public" and row["lag"] == 1
                        and row["year_a"] == year_a and row["year_b"] == year_b):
                    public.append(row[key])
        observed, p = sign_flip_test(jury, public)
        differences.append([key, float(np.mean(jury)), float(np.mean(public)), observed,
                            sum(pb > jb for jb, pb in zip(jury, public)), p])
    raw = [d[-1] for d in differences]
    from rq4_common import benjamini_hochberg, holm

    save_csv(
        RESULTS_DIR / "rq4_temporal_layer_diff.csv",
        ["statistic", "mean_jury", "mean_public", "public_minus_jury",
         "pairs_public_higher", "p_exact", "p_holm", "p_fdr"],
        [d + [h, b] for d, h, b in zip(differences, holm(raw), benjamini_hochberg(raw))],
    )

    plot_stability(summary, heatmaps)

    print(f"Results: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("Temporal stability complete.")


def plot_stability(summary: dict, heatmaps: dict) -> None:
    lags = np.arange(1, MAX_LAG + 1)
    fig = plt.figure(figsize=(16, 6.6))
    grid = fig.add_gridspec(2, 3, width_ratios=(1.25, 1, 1))

    panels = (
        (grid[0, 0], "spearman", "Spearman, all common dyads"),
        (grid[1, 0], "residual_pearson", "Pearson, voter and recipient effects removed"),
    )
    for position, (cell, key, title) in enumerate(panels):
        ax = fig.add_subplot(cell)
        for layer in LAYERS:
            ax.plot(lags, [summary[layer, lag, key]["mean"] for lag in lags],
                    "o-", color=COLOURS[layer], label=layer.title())
            ax.fill_between(
                lags,
                [summary[layer, lag, key]["low"] for lag in lags],
                [summary[layer, lag, key]["high"] for lag in lags],
                color=COLOURS[layer], alpha=0.12, label=f"QAP 95% range, {layer}",
            )
        ax.axhline(0, color="#666666", linewidth=0.8, linestyle=":")
        ax.set_xticks(lags)
        ax.set_ylabel("Mean correlation between editions")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
        ax.legend(frameon=False, fontsize=7)
        if position == 0:
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("Lag between editions")

    for column, layer in zip((1, 2), LAYERS):
        ax = fig.add_subplot(grid[:, column])
        image = ax.imshow(heatmaps[layer], cmap="Blues", vmin=0, vmax=0.6)
        ax.set_xticks(range(len(YEARS)), YEARS, rotation=90, fontsize=7)
        ax.set_yticks(range(len(YEARS)), YEARS, fontsize=7)
        ax.set_title(f"{layer.title()}: Spearman between editions")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle("RQ4 - Temporal stability of the voting pattern")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "rq4_temporal_stability.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise SystemExit(f"RQ4 temporal stability failed: {exc}") from exc