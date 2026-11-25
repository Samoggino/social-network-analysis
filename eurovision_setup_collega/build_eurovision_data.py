#!/usr/bin/env python3
"""Generate Eurovision voting tables and annual adjacency matrices.

Run from any directory:
    py build_eurovision_data.py

Input: EurovisionAPI/dataset JSON files, 2016–2026 (excluding 2020).
Output: processed_data/tables/ and processed_data/matrices/.
Requires Python 3.10+; no external dependencies.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
POINT_VALUES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12}
BALLOT_POINTS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "processed_data"


def find_dataset() -> Path:
    """Support both direct and nested GitHub ZIP extraction paths."""
    for candidate in (
        BASE_DIR / "dataset-main",
        BASE_DIR / "dataset-main" / "dataset-main",
        BASE_DIR / "dataset",
        BASE_DIR,
    ):
        if (candidate / "data" / "senior").is_dir():
            return candidate
    raise FileNotFoundError("Dataset not found beside the script (expected data/senior/).")


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def save_csv(path: Path, columns: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


def read_year(dataset: Path, year: int) -> tuple[set[str], dict]:
    """Return finalists and scores indexed by (layer, voter, finalist)."""
    directory = dataset / "data" / "senior" / str(year)
    contestants = {}
    for file in sorted((directory / "contestants").glob("*/contestant.json")):
        info = load_json(file)
        if info["id"] in contestants:
            raise ValueError(f"{year}: duplicate contestant ID {info['id']}")
        contestants[info["id"]] = info["country"]

    if not contestants:
        raise ValueError(f"{year}: no contestant metadata found")

    finalists = set()
    votes = {}
    final = load_json(directory / "rounds" / "final.json")
    for performance in final["performances"]:
        target = contestants[performance["contestantId"]]
        if target in finalists:
            raise ValueError(f"{year}: duplicate finalist {target}")
        finalists.add(target)
        seen_layers = set()
        for score in performance["scores"]:
            layer = score.get("name", "").lower()
            if layer == "tele":
                layer = "public"
            if layer not in LAYERS:
                continue
            if layer in seen_layers:
                raise ValueError(f"{year}: duplicate {layer} result for {target}")
            seen_layers.add(layer)
            ballot = score["votes"]
            if sum(ballot.values()) != score["points"]:
                raise ValueError(f"{year}/{layer}/{target}: inconsistent score total")
            for source, points in ballot.items():
                if type(points) is not int or points not in POINT_VALUES:
                    raise ValueError(f"{year}/{layer}/{source}->{target}: invalid points")
                if source == target:
                    raise ValueError(f"{year}: self vote by {source}")
                key = (layer, source, target)
                if key in votes:
                    raise ValueError(f"{year}: duplicate vote {key}")
                votes[key] = points
        if seen_layers != set(LAYERS):
            raise ValueError(f"{year}: jury/public results missing for {target}")
    return finalists, votes


def validate_ballots(year: int, finalists: set[str], votes: dict) -> set[str]:
    """Check completeness and Eurovision's 1–8, 10, 12 voting scale."""
    voters = {
        layer: {source for l, source, _ in votes if l == layer and source != "WLD"}
        for layer in LAYERS
    }
    if voters["jury"] != voters["public"]:
        raise ValueError(f"{year}: jury and public voter sets differ")

    for layer in LAYERS:
        for source in voters[layer]:
            targets = {target for l, s, target in votes if l == layer and s == source}
            if targets != finalists - {source}:
                raise ValueError(f"{year}/{layer}/{source}: incomplete or unexpected targets")
            positive = sorted(votes[layer, source, target]
                              for target in targets if votes[layer, source, target] > 0)
            if positive != BALLOT_POINTS:
                raise ValueError(f"{year}/{layer}/{source}: invalid ballot distribution")
    return voters["jury"]


def main() -> None:
    dataset = find_dataset()
    master_rows = []
    voting_years = defaultdict(set)
    finalist_years = defaultdict(set)

    for year in YEARS:
        finalists, votes = read_year(dataset, year)
        voters = validate_ballots(year, finalists, votes)
        for country in voters:
            voting_years[country].add(year)
        for country in finalists:
            finalist_years[country].add(year)

        countries = sorted(voters | finalists)
        for layer in LAYERS:
            matrix_rows = []
            for source in countries:
                row = [source]
                for target in countries:
                    # Empty = structurally ineligible; 0 = eligible but no points.
                    if source in voters and target in finalists and source != target:
                        points = votes[layer, source, target]
                        row.append(points)
                        master_rows.append((year, layer, source, target, points))
                    else:
                        row.append("")
                matrix_rows.append(tuple(row))
            save_csv(
                OUTPUT_DIR / "matrices" / f"{year}_{layer}.csv",
                ["country", *countries], matrix_rows,
            )

    countries = sorted(set(voting_years) | set(finalist_years))
    nodes_rows = [
        (
            country,
            len(voting_years[country]),
            len(finalist_years[country]),
            ";".join(map(str, sorted(voting_years[country]))),
            ";".join(map(str, sorted(finalist_years[country]))),
        )
        for country in countries
    ]
    save_csv(
        OUTPUT_DIR / "tables" / "votes_master.csv",
        ["year", "layer", "source", "target", "points"], master_rows,
    )
    save_csv(
        OUTPUT_DIR / "tables" / "nodes.csv",
        ["country", "years_voting", "years_finalist", "voting_years", "finalist_years"],
        nodes_rows,
    )
    print(f"Dataset: {dataset}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Annual matrices: {len(YEARS) * len(LAYERS)}")
    print(f"Eligible national votes: {len(master_rows)}")
    print(f"Countries: {len(countries)}")
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, KeyError, ValueError, TypeError, OSError) as exc:
        raise SystemExit(f"Data generation failed: {exc}") from exc
