#!/usr/bin/env python3
"""Rebuild the 20 annual Eurovision voting matrices from the EurovisionAPI data.

Usage:
    python src/build_eurovision_data.py [path/to/dataset-main/data/senior]

The output format is the one expected by analyze_rq1.py / analyze_rq2.py:

    country,<code>,<code>,...
    <code>,<points or blank>,...

Blank cells mark impossible votes (self-vote or non-finalist recipient).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = (("jury", "jury"), ("public", "public"))
BALLOT = {1, 2, 3, 4, 5, 6, 7, 8, 10, 12}
EXCLUDED_VOTERS = {"WLD"}
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "src" else SCRIPT_DIR
OUT_DIR = ROOT / "processed_data" / "matrices"

# First argument: path to the extracted EurovisionAPI "senior" folder.
# Default: <repo>/dataset-main/data/senior
RAW_DIR = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else ROOT / "dataset-main" / "data" / "senior"


def load_codes(year_dir: Path) -> dict[int, str]:
    codes = {}
    for path in sorted((year_dir / "contestants").glob("*/contestant.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        codes[data["id"]] = data["country"]
    return codes


def build_year(year: int) -> tuple[list[str], dict[str, dict[str, int]], set[str]]:
    year_dir = RAW_DIR / str(year)
    final = json.loads((year_dir / "rounds" / "final.json").read_text(encoding="utf-8"))
    codes = load_codes(year_dir)

    performances = final.get("performances") or []
    if not performances:
        raise ValueError(f"{year}: no performances in final.json")

    finalists = {codes[p["contestantId"]] for p in performances}

    votes: dict[str, dict[str, int]] = {layer: {} for layer, _ in LAYERS}
    for performance in performances:
        target = codes[performance["contestantId"]]
        for score in performance.get("scores") or []:
            layer = score["name"]
            if layer not in votes:
                continue
            for voter, points in (score.get("votes") or {}).items():
                if voter in EXCLUDED_VOTERS:
                    continue
                votes[layer].setdefault(voter, {})[target] = int(points)

    voters = set()
    for layer, _ in LAYERS:
        voters |= set(votes[layer])
    voters -= EXCLUDED_VOTERS

    missing = finalists - voters
    if missing:
        raise ValueError(f"{year}: finalists without a ballot: {sorted(missing)}")

    return sorted(voters), votes, finalists


def write_matrix(path: Path, countries: list[str], votes: dict[str, dict[str, int]], finalists: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["country"] + countries)
        for source in countries:
            row = [source]
            for target in countries:
                if target not in finalists or target == source:
                    row.append("")
                else:
                    row.append(str(votes.get(source, {}).get(target, 0)))
            writer.writerow(row)


def validate(year: int, countries: list[str], votes: dict[str, dict[str, int]], finalists: set[str]) -> None:
    for source in countries:
        row = votes.get(source, {})
        positive = [row[t] for t in finalists if t != source and row.get(t, 0) > 0]
        zeros = [t for t in finalists if t != source and row.get(t, 0) == 0]
        if len(positive) != 10:
            raise ValueError(f"{year} {source}: {len(positive)} positive votes")
        if set(positive) - BALLOT or sorted(positive) != sorted(BALLOT):
            raise ValueError(f"{year} {source}: ballot {sorted(positive)}")
        if sum(positive) != 58:
            raise ValueError(f"{year} {source}: total {sum(positive)}")
        # every finalist must have a recorded value (0 included) or be absent
        for target in finalists:
            if target == source:
                continue
            if target not in row:
                raise ValueError(f"{year} {source}->{target}: missing cell")


def main() -> None:
    total_voters = 0
    total_opportunities = 0
    for year in YEARS:
        countries, votes, finalists = build_year(year)
        for layer, key in LAYERS:
            validate(year, countries, votes[key], finalists)
            write_matrix(OUT_DIR / f"{year}_{layer}.csv", countries, votes[key], finalists)
        total_voters += len(countries)
        total_opportunities += 2 * (len(countries) * len(finalists) - len(finalists))
        print(f"{year}: {len(countries)} voters, {len(finalists)} finalists, matrices written")
    print(f"Voters summed over years: {total_voters}")
    print(f"Opportunities (both layers): {total_opportunities}")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise SystemExit(f"Build failed: {exc}") from exc
