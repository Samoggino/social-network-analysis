"""Compare stability across editions using a shared permutation history."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np

from rq4_common import (
    BATCH_SIZE, LAYERS, METRICS, NULL_FIELDS, PRIMARY, SEED, Comparison, Edition,
    adjust, figure_path, load_editions, null_summary, parser, permutation_orders,
    save_csv, statistics,
)

COLOURS = {"jury": "#246b91", "public": "#c56328"}


def observed_pairs(editions: dict[int, Edition], max_lag: int,
                   fixed_dyads: set[tuple[str, str]] | None = None) -> tuple[list[dict], dict]:
    years = list(editions)
    comparisons = {}
    records = []
    for lag in range(1, min(len(years), max_lag + 1)):
        for year_a, year_b in zip(years, years[lag:]):
            first, second = editions[year_a], editions[year_b]
            comparison = Comparison.align(first, second, fixed_dyads)
            comparisons[year_a, year_b] = comparison
            a_row, a_col = comparison.first
            b_row, b_col = comparison.second
            for layer, point_a, point_b in zip(LAYERS, first.points, second.points):
                records.append({
                    "layer": layer, "lag": lag, "year_a": year_a, "year_b": year_b,
                    "cells": len(a_row), "voters": len(np.unique(a_row)), "recipients": len(np.unique(a_col)),
                    **statistics(point_a[a_row, a_col], point_b[b_row, b_col], comparison.effects),
                })
    return records, comparisons


def temporal_batch(editions: dict[int, Edition], comparisons: dict,
                   size: int, rng: np.random.Generator) -> np.ndarray:
    # Each replicate has one country permutation per edition, shared by both
    # layers and by all pairs in which that edition occurs.
    orders = {year: permutation_orders(edition, size, rng) for year, edition in editions.items()}
    values = []
    for (year_a, year_b), comparison in comparisons.items():
        a_row, a_col = comparison.first
        b_row, b_col = comparison.second
        order_a, order_b = orders[year_a], orders[year_b]
        first = editions[year_a].points[:, order_a[:, a_row], order_a[:, a_col]]
        second = editions[year_b].points[:, order_b[:, b_row], order_b[:, b_col]]
        values.append(comparison.effects.correlation(first, second))
    all_values = np.stack(values)
    if not np.isfinite(all_values).all():
        raise ValueError("Undefined residual Pearson in a temporal permutation")
    return all_values.mean(axis=0)


def temporal_null(editions: dict[int, Edition], comparisons: dict,
                  count: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    batches = [temporal_batch(editions, comparisons, min(BATCH_SIZE, count - start), rng)
               for start in range(0, count, BATCH_SIZE)]
    return np.concatenate(batches, axis=1)


def lag_summary(records: list[dict]) -> list[dict]:
    summaries = []
    for layer in LAYERS:
        lags = sorted({record["lag"] for record in records})
        for lag in lags:
            selected = [record for record in records if record["layer"] == layer and record["lag"] == lag]
            for metric in METRICS:
                summaries.append({"layer": layer, "lag": lag, "statistic": metric, "pairs": len(selected),
                                  "mean": float(np.mean([row[metric] for row in selected]))})
    return summaries


def layer_differences(records: list[dict]) -> list[dict]:
    jury = [row for row in records if row["lag"] == 1 and row["layer"] == "jury"]
    public = [row for row in records if row["lag"] == 1 and row["layer"] == "public"]
    differences = []
    for metric in METRICS:
        a = np.array([row[metric] for row in jury])
        b = np.array([row[metric] for row in public])
        paired = np.isfinite(a) & np.isfinite(b)
        delta = b[paired] - a[paired]
        differences.append({
            "statistic": metric, "pairs": len(a), "valid_pairs": len(delta),
            "mean_jury": float(a[paired].mean()) if len(delta) else np.nan,
            "mean_public": float(b[paired].mean()) if len(delta) else np.nan,
            "public_minus_jury": float(delta.mean()) if len(delta) else np.nan,
            "pairs_public_higher": int((delta > 1e-12).sum()),
        })
    return differences


def always_eligible(editions: dict[int, Edition]) -> set[tuple[str, str]]:
    eligible_by_year = []
    for edition in editions.values():
        rows, cols = np.nonzero(edition.eligible)
        eligible_by_year.append({(edition.countries[i], edition.countries[j]) for i, j in zip(rows, cols)})
    return set.intersection(*eligible_by_year)


def without_edition(records: list[dict], year: int) -> list[dict]:
    return [row for row in records
            if row["lag"] == 1 and year not in (row["year_a"], row["year_b"])]


def robustness_rows(editions: dict[int, Edition], records: list[dict]) -> list[dict]:
    fixed_records, _ = observed_pairs(editions, 1, always_eligible(editions))
    baseline = {row["statistic"]: row["public_minus_jury"] for row in layer_differences(records)}
    scenarios = [("fixed_dyads", "", fixed_records)]
    scenarios.extend(("leave_one_edition_out", year, without_edition(records, year)) for year in editions)
    result = []
    for name, excluded, selected in scenarios:
        coverage = {f"{key}_{stat}": function(row[key] for row in selected)
                    for key in ("cells", "voters", "recipients")
                    for stat, function in (("min", min), ("max", max))}
        for row in layer_differences(selected):
            result.append({"scenario": name, "excluded_year": excluded, **coverage, **row,
                           "change_from_main": row["public_minus_jury"] - baseline[row["statistic"]]})
    return result


def plot(root: Path, years: list[int], summaries: list[dict], pairs: list[dict]) -> None:
    fig = plt.figure(figsize=(14, 6.2), layout="constrained")
    grid = fig.add_gridspec(2, 3, width_ratios=(1.4, 1, 1))
    lags = list(range(1, len(years)))
    for index, (metric, title) in enumerate((
            ("spearman", "Spearman on common dyads"),
            (PRIMARY, "Pearson after additive fixed effects"))):
        ax = fig.add_subplot(grid[index, 0])
        for layer in LAYERS:
            records = [r for r in summaries if r["layer"] == layer and r["statistic"] == metric]
            ax.plot(lags, [r["mean"] for r in records], "o-", label=layer.title(), color=COLOURS[layer])
            if metric == PRIMARY:
                r = records[0]
                offset = -0.12 if layer == "jury" else 0.12
                ax.vlines(1 + offset, r["null_q025"], r["null_q975"],
                          color=COLOURS[layer], linestyle="--", linewidth=3,
                          label=f"{layer.title()} null 95%")
        ax.axhline(0, color="0.65", linewidth=0.8)
        ax.set(title=title, ylabel="Mean correlation")
        ax.set_xticks(lags, [f"{lag}\n({len(years) - lag})" for lag in lags])
        ax.grid(axis="y", alpha=0.2)
        if metric == PRIMARY:
            ax.legend(fontsize=7, ncol=2, loc="center right", bbox_to_anchor=(1, 0.59))
        else:
            ax.legend(fontsize=7, ncol=2, loc="upper left")
        if index == 1:
            ax.set_xlabel("Lag in editions (number of pairs)")
    off_diagonal = [abs(row["spearman"]) for row in pairs]
    bound = max(0.1, np.ceil(max(off_diagonal) * 10) / 10)
    cmap = matplotlib.colormaps["RdBu"].with_extremes(bad="#ebebeb")
    for column, layer in enumerate(LAYERS, start=1):
        heat = np.full((len(years), len(years)), np.nan)
        for row in pairs:
            if row["layer"] == layer:
                i, j = years.index(row["year_a"]), years.index(row["year_b"])
                heat[i, j] = heat[j, i] = row["spearman"]
        ax = fig.add_subplot(grid[:, column])
        image = ax.imshow(heat, cmap=cmap, norm=TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound))
        ax.set_xticks(range(len(years)), years, rotation=90, fontsize=8)
        ax.set_yticks(range(len(years)), years, fontsize=8)
        ax.set_title(f"{layer.title()}: Spearman")
        fig.colorbar(image, ax=ax, fraction=0.05, pad=0.04)
    fig.suptitle("RQ4 | Stability between Grand Finals")
    fig.savefig(figure_path(root, "rq4_temporal_stability.png"), dpi=180)
    plt.close(fig)


def run(editions: dict[int, Edition], root: Path, count: int, seed: int) -> None:
    pairs, comparisons = observed_pairs(editions, len(editions) - 1)
    lag_one = {key: comparisons[key] for key in zip(editions, list(editions)[1:])}
    samples = temporal_null(editions, lag_one, count, seed)
    summaries = lag_summary(pairs)
    differences = layer_differences(pairs)
    primary_layers = [row for row in summaries if row["lag"] == 1 and row["statistic"] == PRIMARY]
    primary_gap = next(row for row in differences if row["statistic"] == PRIMARY)
    for row, distribution in zip(primary_layers, samples):
        row.update(null_summary(row["mean"], distribution))
    primary_gap.update(null_summary(primary_gap["public_minus_jury"], samples[1] - samples[0]))
    adjust([*primary_layers, primary_gap])
    difference_fields = ("statistic", "pairs", "valid_pairs", "mean_jury", "mean_public",
                         "public_minus_jury", "pairs_public_higher")
    save_csv(root, "rq4_temporal_pairs.csv",
             ("layer", "lag", "year_a", "year_b", "cells", "voters", "recipients", *METRICS), pairs)
    save_csv(root, "rq4_temporal_stability.csv",
             ("layer", "lag", "statistic", "pairs", "mean", *NULL_FIELDS), summaries)
    save_csv(root, "rq4_temporal_layer_diff.csv", (*difference_fields, *NULL_FIELDS), differences)
    save_csv(root, "rq4_robustness.csv",
             ("scenario", "excluded_year", "cells_min", "cells_max", "voters_min", "voters_max",
              "recipients_min", "recipients_max", *difference_fields, "change_from_main"),
             robustness_rows(editions, pairs))
    plot(root, list(editions), summaries, pairs)


def main() -> None:
    cli = parser(__doc__, SEED + 1)
    args = cli.parse_args()
    if args.permutations < 1:
        cli.error("--permutations must be positive")
    run(load_editions(args.matrices), args.output_dir, args.permutations, args.seed)


if __name__ == "__main__":
    main()
