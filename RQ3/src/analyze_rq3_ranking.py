#!/usr/bin/env python3
"""RQ3 (addition): a ranked table of prestige, and a check on the unused measures.

Run from the RQ3 directory, after analyze_rq3.py:
    python src/analyze_rq3_ranking.py

The research question asks *which* countries receive consensus. The answers were
in the prose of the README and in `rq3_country_aggregate.csv`, which is sorted by
combined prestige but carries no rank and no minimum-exposure rule. Read without
a filter, the ranking is misleading: a country that reached one final and
collected many points per voter sits at the top of the jury list, above countries
that reached ten finals.

This script writes `rq3_country_ranking.csv` with an explicit rank per layer and
a `stable` flag for countries that reached at least MIN_FINALS finals, on which
the ranks that should be read are the `*_stable` ones. It also reports the rank
correlation between the two layers.

The second part closes two measures that `analyze_rq3.py` computes, stores in
`rq3_country_year.csv` and never uses: betweenness on the finalists-only network
and the hub score of the voters. The correlations show whether they add anything
to the in-strength, which is the measure the report actually uses.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from analyze_rq3 import (
    DEFAULT_MATRICES,
    LAYERS,
    RESULTS,
    YEARS,
    centralities,
    read_matrix,
    save_csv,
    spearman,
)

MIN_FINALS = 4


def read_aggregate(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found: run src/analyze_rq3.py first"
        )
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            {
                "country": row["country"],
                "finals": int(row["finals"]),
                "jury": float(row["points_per_opportunity_jury"]),
                "public": float(row["points_per_opportunity_public"]),
            }
            for row in csv.DictReader(handle)
        ]


def add_ranks(rows: list[dict], layer: str) -> None:
    """Competition ranking (1, 2, 2, 4), ties broken by country name."""
    order = sorted(rows, key=lambda r: (-r[layer], r["country"]))
    rank = 0
    previous = None
    for position, row in enumerate(order, start=1):
        if row[layer] != previous:
            rank = position
            previous = row[layer]
        row[f"rank_{layer}"] = rank


def main() -> None:
    parser = argparse.ArgumentParser(description="RQ3: prestige ranking and measure check")
    parser.add_argument("--matrices", type=Path, default=DEFAULT_MATRICES)
    parser.add_argument("--aggregate", type=Path, default=RESULTS / "rq3_country_aggregate.csv")
    parser.add_argument("--min-finals", type=int, default=MIN_FINALS)
    args = parser.parse_args()

    rows = read_aggregate(args.aggregate)
    for layer in LAYERS:
        add_ranks(rows, layer)

    stable = [r for r in rows if r["finals"] >= args.min_finals]

    # Ranks inside the stable subset, which is what the report should quote.
    for layer in LAYERS:
        order = sorted(stable, key=lambda r: (-r[layer], r["country"]))
        for position, row in enumerate(order, start=1):
            row[f"rank_{layer}_stable"] = position
    for layer in LAYERS:
        for row in rows:
            row.setdefault(f"rank_{layer}_stable", "")

    columns = [
        "country", "finals",
        "points_per_opportunity_jury", "rank_jury", "rank_jury_stable",
        "points_per_opportunity_public", "rank_public", "rank_public_stable",
        "stable",
    ]
    out = []
    for row in sorted(rows, key=lambda r: (r["rank_jury"], r["country"])):
        out.append([
            row["country"], row["finals"],
            row["jury"], row[f"rank_jury"], row[f"rank_jury_stable"],
            row["public"], row[f"rank_public"], row[f"rank_public_stable"],
            int(row["finals"] >= args.min_finals),
        ])
    save_csv(RESULTS / "rq3_country_ranking.csv", columns, out)

    full_rho = spearman([r["jury"] for r in rows], [r["public"] for r in rows])
    stable_rho = spearman([r["jury"] for r in stable], [r["public"] for r in stable])
    save_csv(
        RESULTS / "rq3_ranking_agreement.csv",
        ["scope", "min_finals", "countries", "spearman_jury_public"],
        [
            ["all finalists", 0, len(rows), round(full_rho, 10)],
            ["stable finalists", args.min_finals, len(stable), round(stable_rho, 10)],
        ],
    )

    # Do betweenness and the hub score add anything to the in-strength?
    redundancy = []
    for year in YEARS:
        for layer in LAYERS:
            countries, W, eligible = read_matrix(args.matrices / f"{year}_{layer}.csv")
            finalists = eligible.any(axis=0)
            voters = eligible.any(axis=1)
            in_strength = W.sum(axis=0)
            out_strength = W.sum(axis=1)

            # Betweenness and hub are recomputed with the same functions used in
            # analyze_rq3.py, so that this script does not depend on the other
            # output files being current.
            cent = centralities(W, countries, finalists)
            finalist_names = [c for c, f in zip(countries, finalists) if f]
            rho_between = spearman(
                [cent["betweenness"][c] for c in finalist_names],
                list(in_strength[finalists]),
            )
            # Hub: the recursive score of voting for the finalists that receive
            # consensus. Compare it with the plain mean in-strength of the ten
            # countries the voter chose.
            chosen = W[voters] > 0
            mean_chosen = chosen @ in_strength / chosen.sum(axis=1)
            rho_hub = spearman([cent["hub"][c] for c, v in zip(countries, voters) if v], mean_chosen)
            redundancy.append([year, layer, len(finalist_names), rho_between, rho_hub])

    save_csv(
        RESULTS / "rq3_measure_redundancy.csv",
        ["year", "layer", "finalists", "spearman_betweenness_in_strength",
         "spearman_hub_recipient_strength"],
        [[r[0], r[1], r[2], round(r[3], 10), round(r[4], 10)] for r in redundancy],
    )

    print(f"Ranking written to {RESULTS / 'rq3_country_ranking.csv'}")
    print(f"Spearman jury-public ranking: {full_rho:.3f} (all), {stable_rho:.3f} (>= {args.min_finals} finals)")
    print(f"Betweenness vs in-strength: {np.mean([r[3] for r in redundancy]):.3f}")
    print(f"Hub vs recipient strength:   {np.mean([r[4] for r in redundancy]):.3f}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise SystemExit(f"RQ3 ranking failed: {exc}") from exc
