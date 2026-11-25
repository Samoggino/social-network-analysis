"""Within-edition agreement between national jury and televote networks."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rq4_common import (
    BATCH_SIZE, METRICS, NULL_FIELDS, PRIMARY, SEED, Comparison, Edition, adjust,
    figure_path, load_editions, null_summary, parser, permutation_orders, save_csv,
    statistics,
)


def agreement(edition: Edition, count: int, rng: np.random.Generator) -> tuple[dict, np.ndarray]:
    comparison = Comparison.align(edition, edition)
    row, col = comparison.first
    jury = edition.points[0, row, col]
    public = edition.points[1, row, col]
    observed = {"cells": len(row), "both_positive": int(((jury > 0) & (public > 0)).sum()),
                **statistics(jury, public, comparison.effects)}
    samples = np.empty(count)
    for start in range(0, count, BATCH_SIZE):
        end = min(start + BATCH_SIZE, count)
        orders = permutation_orders(edition, end - start, rng)
        shuffled = edition.points[1, orders[:, row], orders[:, col]]
        samples[start:end] = comparison.effects.correlation(jury, shuffled)
    return {**observed, **null_summary(observed[PRIMARY], samples)}, np.stack((jury, public))


def plot(root: Path, records: list[dict], last_points: np.ndarray) -> None:
    x = np.arange(len(records))
    years = [record["year"] for record in records]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), layout="constrained")
    ax = axes[0]
    ax.fill_between(x, [r["null_q025"] for r in records], [r["null_q975"] for r in records],
                    color="#cf7135", alpha=0.18, label="Central 95% of the null")
    ax.plot(x, [r[PRIMARY] for r in records], "o-", color="#a84e1d", label="Fixed-effect residual Pearson")
    ax.axhline(0, color="0.65", linewidth=0.8)
    ax.set(title="Agreement after additive fixed effects", ylabel="Correlation")
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.plot(x, [r["spearman"] for r in records], "o-", color="#246b91", label="Spearman, all common dyads")
    ax.plot(x, [r["jaccard"] for r in records], "s-", color="#56771c", label="Jaccard, positive dyads")
    ax.set(title="Descriptive agreement", ylabel="Similarity")
    ax.legend(fontsize=8)
    for ax in axes[:2]:
        ax.set_xticks(x, years, rotation=45)
        ax.grid(axis="y", alpha=0.2)

    jury, public = last_points.astype(int)
    counts = np.zeros((13, 13), dtype=int)
    np.add.at(counts, (public, jury), 1)
    ax = axes[2]
    heat = ax.imshow(np.log10(counts + 1), origin="lower", cmap="Greys")
    ax.plot([0, 12], [0, 12], "--", color="#cf7135", linewidth=1)
    ax.set(xticks=range(0, 13, 2), yticks=range(0, 13, 2), xlabel="Jury points",
           ylabel="Televote points", title=f"Common dyads in {years[-1]}")
    fig.colorbar(heat, ax=ax, label="log10(count + 1)", fraction=0.05, pad=0.04)
    fig.suptitle("RQ4 | Jury and televote within the same Grand Final")
    fig.savefig(figure_path(root, "rq4_layer_similarity.png"), dpi=180)
    plt.close(fig)


def run(editions: dict[int, Edition], root: Path, count: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    records = []
    for year, edition in editions.items():
        record, points = agreement(edition, count, rng)
        records.append({"year": year, **record})
    adjust(records)
    save_csv(root, "rq4_layer_similarity.csv",
             ("year", "cells", "both_positive", *METRICS, "spearman_both_positive", *NULL_FIELDS),
             records)
    plot(root, records, points)


def main() -> None:
    cli = parser(__doc__, SEED)
    args = cli.parse_args()
    if args.permutations < 1:
        cli.error("--permutations must be positive")
    run(load_editions(args.matrices), args.output_dir, args.permutations, args.seed)


if __name__ == "__main__":
    main()
