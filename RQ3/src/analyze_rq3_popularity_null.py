#!/usr/bin/env python3
"""RQ3 (addition): a popularity-preserving null for bridging, and entropy.

Run from the RQ3 directory, after analyze_rq3.py:
    python src/analyze_rq3_popularity_null.py

The null model used by analyze_rq3.py draws rule-compliant *uniform* ballots:
every voter picks ten eligible finalists at random. Against that null, "votes go
to the voter's own group" is compared with a world in which no country is
popular, which is not the world we observe. A country that always reaches the
final and always collects points from many voters would show a stable home
share even if geography played no role, and the mechanical component of the
prestige-participation correlation would be underestimated.

The null here keeps popularity fixed. For every finalist the number of voters
that gave it points and the multiset of points it received are preserved; only
the *identity* of those voters is redrawn uniformly among the ones that could
vote for it. Every finalist therefore keeps its in-degree and its in-strength,
and the concentration measures (Gini, top-3, HHI) are unchanged by construction:
this null tests the bridging measures only. Under it the question becomes the
right one: given who is popular, do the points come disproportionately from the
finalist's own group?

Three statistics are tested per network and per grouping: the mean home excess,
the mean participation ratio, and the Spearman correlation between prestige and
participation (the fourth result of RQ3). The last one is why the root README
listed this null as missing: under uniform ballots the mechanical part of that
correlation is only about 0.25, and with the observed popularity distribution it
may be larger.

Because the null has no popularity signal, the z-scores of the observed values
against it are also comparable across layers, which the uniform null does not
guarantee: the public layer has a wider null spread. The layer difference is
therefore also tested on the z-scores.

Entropy, named by the official RQ3 specification next to Gini and PageRank, is
added here: normalised Shannon entropy of the share of points received, with the
same uniform-ballot null. It is monotone in the Herfindahl index already
reported, so it adds no new information; it is computed so that the repository
covers the measures it claims to cover.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze_rq3 import (
    COLORS,
    DEFAULT_ATTRIBUTES,
    DEFAULT_COMMUNITIES,
    DEFAULT_MATRICES,
    FIGURES,
    GROUPS,
    LABELS,
    LAYERS,
    MIN_VOTERS,
    RESULTS,
    YEARS,
    benjamini_hochberg,
    bridging,
    group_matrix,
    holm,
    load_attributes,
    load_communities,
    mc_test,
    random_ballots,
    read_matrix,
    save_csv,
    sign_flip_test,
    spearman,
)

N_NULL = 1000      # popularity-preserving replicates per network
N_BALLOTS = 2000   # uniform-ballot samples for the entropy null
STATISTICS = ("home_excess", "participation_ratio", "spearman_prestige_participation")


def save(path: Path, columns: list[str], rows: list[list]) -> None:
    save_csv(path, columns, [[round(v, 10) if isinstance(v, float) else v for v in row] for row in rows])


def entropy(in_strength: np.ndarray) -> float:
    """Normalised Shannon entropy of the points received (1 = equal shares)."""
    share = in_strength / in_strength.sum()
    share = share[share > 0]
    if len(share) < 2:
        return float("nan")
    return float(-(share * np.log(share)).sum() / np.log(len(share)))


def popularity_null(
    W: np.ndarray, eligible: np.ndarray, G: np.ndarray, finalists: np.ndarray,
    prestige: np.ndarray, n_null: int, rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """Redraw, for each finalist, which eligible voters gave it its points.

    The weights a finalist received are a fixed multiset; the voters are a
    uniformly random subset of the eligible ones. In-degree, in-strength and the
    weight multiset are therefore identical to the observed network.
    """
    own = np.argmax(G, axis=1)
    in_degree = (W > 0).sum(axis=0)

    home, part = [], []
    kept, kept_enough = [], []
    for j in np.flatnonzero(finalists):
        voters = np.flatnonzero(eligible[:, j])
        if len(voters) == 0:
            continue
        received = W[voters, j]
        given = received > 0
        if not given.any():
            continue
        weights = received[given]
        n_given = len(weights)

        Gv = G[voters]
        voters_from = Gv.sum(axis=0)
        eligible_total = voters_from.sum()
        home_expected = voters_from[own[j]] / eligible_total
        part_expected = 1 - ((voters_from / eligible_total) ** 2).sum()

        # Random subset of the eligible voters, of the size that voted for j.
        cols = np.arange(n_null)
        order = np.argsort(rng.random((len(voters), n_null)), axis=0)[:n_given]
        assigned = np.zeros((len(voters), n_null))
        assigned[order, cols[None, :]] = weights[:, None]

        points_from = Gv.T @ assigned            # groups x replicates
        total = points_from.sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            home.append(points_from[own[j]] / total - home_expected)
            part.append((1 - ((points_from / total) ** 2).sum(axis=0)) / part_expected)
        kept.append(j)
        if in_degree[j] >= MIN_VOTERS:
            kept_enough.append(len(kept) - 1)

    home = np.array(home)   # finalists x replicates
    part = np.array(part)
    enough = np.array(kept_enough, dtype=int)

    def correlation(selection: np.ndarray) -> np.ndarray:
        return np.array([
            spearman(prestige[selection], part[selection, b]) for b in range(n_null)
        ])

    return {
        "home_excess": home.mean(axis=0),
        "participation_ratio": part.mean(axis=0),
        "spearman_prestige_participation": correlation(np.arange(len(kept))),
        "home_excess_min5": home[enough].mean(axis=0),
        "participation_ratio_min5": part[enough].mean(axis=0),
        "spearman_prestige_participation_min5": correlation(enough),
    }


def plot_null(rows: list[dict]) -> None:
    """Home excess against the popularity-preserving null, region grouping."""
    index = {
        (r["year"], r["layer"]): r
        for r in rows
        if r["group"] == "region" and r["statistic"] == "home_excess"
    }
    positions = np.arange(len(YEARS))

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.6), sharey=True)
    for ax, layer in zip(axes, LAYERS):
        subset = [index[(y, layer)] for y in YEARS]
        ax.fill_between(positions,
                        [r["null_q025"] for r in subset],
                        [r["null_q975"] for r in subset],
                        color="#999999", alpha=0.25, label="Popularity-preserving null, 95% range")
        ax.plot(positions, [r["null_mean"] for r in subset], color="#555555",
                linestyle="--", linewidth=1.2, label="Null mean")
        ax.plot(positions, [r["observed"] for r in subset], "o-", color=COLORS[layer],
                label=f"{LABELS[layer]} observed")
        ax.set_xticks(positions, YEARS, rotation=45)
        ax.set_title(f"{LABELS[layer]}: home excess on the subregion")
        ax.grid(axis="y", alpha=0.2)
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle("RQ3 - Home excess when popularity is held fixed")
    fig.tight_layout()
    fig.savefig(FIGURES / "rq3_popularity_null.png", dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="RQ3: popularity-preserving null and entropy")
    parser.add_argument("--matrices", type=Path, default=DEFAULT_MATRICES)
    parser.add_argument("--attributes", type=Path, default=DEFAULT_ATTRIBUTES)
    parser.add_argument("--communities", type=Path, default=DEFAULT_COMMUNITIES)
    parser.add_argument("--null-samples", type=int, default=N_NULL)
    parser.add_argument("--ballots", type=int, default=N_BALLOTS)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)

    attributes = load_attributes(args.attributes)
    communities = load_communities(args.communities)

    rows: list[dict] = []
    out: list[list] = []
    entropy_out: list[list] = []

    for year in YEARS:
        for layer in LAYERS:
            countries, W, eligible = read_matrix(args.matrices / f"{year}_{layer}.csv")
            finalists = eligible.any(axis=0)
            in_strength = W.sum(axis=0)
            prestige = in_strength / np.maximum(eligible.sum(axis=0), 1)

            partition = communities.get((year, layer), {})
            labels = {c: {**attributes[c], "community": partition[c][0]} for c in countries}

            observed_entropy = entropy(in_strength[finalists])
            ballots = random_ballots(eligible, args.ballots, rng)
            null_entropy = np.array([
                entropy(ballots[s].sum(axis=0)[finalists]) for s in range(args.ballots)
            ])
            test = mc_test(observed_entropy, null_entropy)
            entropy_out.append([year, layer, observed_entropy,
                                test[1], test[2], test[3], test[4],
                                test[5], test[6], test[7]])

            for key in GROUPS:
                G = group_matrix(countries, labels, key)
                bridge = bridging(W, eligible, G, finalists)
                null = popularity_null(W, eligible, G, finalists, prestige, args.null_samples, rng)

                observed = {
                    "home_excess": float(np.nanmean(bridge["home_excess"][finalists])),
                    "participation_ratio": float(np.nanmean(bridge["participation_ratio"][finalists])),
                    "spearman_prestige_participation": spearman(
                        prestige[finalists], bridge["participation_ratio"][finalists]
                    ),
                }
                keys = list(STATISTICS)
                if key == "region":
                    keys += [f"{s}_min5" for s in STATISTICS]

                for statistic in keys:
                    if statistic.endswith("_min5"):
                        base = statistic[:-5]
                        enough = (W > 0).sum(axis=0)[finalists] >= MIN_VOTERS
                        if base == "spearman_prestige_participation":
                            value = spearman(prestige[finalists][enough],
                                             bridge["participation_ratio"][finalists][enough])
                        else:
                            value = float(np.nanmean(bridge[base][finalists][enough]))
                    else:
                        value = observed[statistic]

                    result = mc_test(value, null[statistic])
                    rows.append({
                        "year": year, "layer": layer, "group": key, "statistic": statistic,
                        "observed": value, "null_mean": result[1], "null_sd": result[2],
                        "null_q025": result[3], "null_q975": result[4],
                        "p_high": result[5], "p_low": result[6], "p_two_sided": result[7],
                        "z": (value - result[1]) / result[2] if result[2] else float("nan"),
                    })
                    out.append([year, layer, key, statistic, value, result[1], result[2],
                                result[3], result[4], result[5], result[6], result[7],
                                (value - result[1]) / result[2] if result[2] else float("nan")])
            print(f"{year}: {layer} popularity null and entropy computed", flush=True)

    columns = ["year", "layer", "group", "statistic", "observed", "null_mean", "null_sd",
               "null_q025", "null_q975", "p_high", "p_low", "p_two_sided", "z"]
    save(RESULTS / "rq3_popularity_null.csv", columns, out)

    save(RESULTS / "rq3_entropy.csv",
         ["year", "layer", "entropy", "null_mean", "null_sd", "null_q025", "null_q975",
          "p_high", "p_low", "p_two_sided"], entropy_out)

    # Layer comparison on the z-scores: the null keeps popularity fixed, so the
    # two layers are compared on the same footing.
    diffs = []
    for key in GROUPS:
        keys = list(STATISTICS) + ([f"{s}_min5" for s in STATISTICS] if key == "region" else [])
        for statistic in keys:
            subset = [r for r in rows if r["group"] == key and r["statistic"] == statistic]
            jury = [r["z"] for r in subset if r["layer"] == "jury"]
            public = [r["z"] for r in subset if r["layer"] == "public"]
            observed, p = sign_flip_test(jury, public)
            diffs.append([f"{statistic}_{key}", float(np.mean(jury)), float(np.mean(public)),
                          observed, sum(pb > jb for jb, pb in zip(jury, public)), p])
    raw = [d[-1] for d in diffs]
    diffs = [d + [h, b] for d, h, b in zip(diffs, holm(raw), benjamini_hochberg(raw))]
    save(RESULTS / "rq3_popularity_null_layer_diff.csv",
         ["statistic", "mean_z_jury", "mean_z_public", "public_minus_jury",
          "years_public_higher", "p_exact", "p_holm", "p_fdr"], diffs)

    plot_null(rows)

    print(f"Results: {RESULTS}")
    print(f"Figures: {FIGURES}")
    print("Popularity-preserving null complete.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise SystemExit(f"RQ3 popularity null failed: {exc}") from exc
