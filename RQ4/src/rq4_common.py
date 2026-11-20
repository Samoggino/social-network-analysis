#!/usr/bin/env python3
"""Shared machinery for RQ4: layer similarity and temporal stability.

Import only. The two analysis scripts are

    analyze_rq4_layer_similarity.py   jury vs public, within the same edition
    analyze_rq4_temporal_stability.py the same layer across editions

Everything here works on the annual matrices of RQ1, which have the same
countries, the same eligible cells and the same ballots in both layers:
W[i, j] = points from voter i to finalist j, an empty cell is an impossible
vote, 0 is an eligible vote without points.

Two design choices are worth stating because they drive every number.

Common dyads. A pair (i, j) enters a comparison only if it is an eligible vote
in *both* networks being compared. In the Eurovision matrices the eligibility
mask happens to be identical between jury and public of the same edition, but
the code checks it rather than assuming it.

QAP. The correlation between two networks that share their nodes is not a
sample of independent dyads: rows and columns are the same countries, so the
effective sample size is much smaller than the number of cells. P-values are
therefore computed by permuting the country labels of one network (rows and
columns together) and recomputing the statistic on the cells that remain
eligible in both. The observed statistic is computed in the same way, on the
intersection of the two masks, so that observed and permuted values are
comparable. This is the quadratic assignment procedure named in the project
proposal.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
SEED = 42

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "src" else SCRIPT_DIR
MATRIX_DIR = ROOT.parent / "RQ1" / "processed_data" / "matrices"
RESULTS_DIR = ROOT / "results" / "rq4"
FIGURES_DIR = ROOT / "figures" / "rq4"


def save_csv(path: Path, columns: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(
            [[round(v, 10) if isinstance(v, float) else v for v in row] for row in rows]
        )


def read_matrix(path: Path) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Return countries, points W and eligibility mask E, with ballot checks."""
    if not path.is_file():
        raise FileNotFoundError(f"Matrix not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if rows[0][0] != "country":
        raise ValueError(f"Unexpected header in {path.name}")
    countries = rows[0][1:]
    if [row[0] for row in rows[1:]] != countries:
        raise ValueError(f"Row and column labels differ in {path.name}")
    n = len(countries)
    W = np.zeros((n, n))
    E = np.zeros((n, n), dtype=bool)
    for i, row in enumerate(rows[1:]):
        for j, raw in enumerate(row[1:]):
            if raw.strip() == "":
                continue
            E[i, j] = True
            W[i, j] = float(raw)
    return countries, W, E


def ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks, ties included."""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    _, inverse, counts = np.unique(values[order], return_inverse=True, return_counts=True)
    ends = np.cumsum(counts)
    average = (ends - counts + 1 + ends) / 2.0
    out = np.empty(len(values))
    out[order] = average[inverse]
    return out


def spearman(first: np.ndarray, second: np.ndarray) -> float:
    first, second = np.asarray(first, float), np.asarray(second, float)
    if len(first) < 3 or first.std() == 0 or second.std() == 0:
        return float("nan")
    return float(np.corrcoef(ranks(first), ranks(second))[0, 1])


def pearson(first: np.ndarray, second: np.ndarray) -> float:
    first, second = np.asarray(first, float), np.asarray(second, float)
    if len(first) < 3 or first.std() == 0 or second.std() == 0:
        return float("nan")
    return float(np.corrcoef(first, second)[0, 1])


def jaccard(first: np.ndarray, second: np.ndarray) -> float:
    union = (first | second).sum()
    return float((first & second).sum() / union) if union else float("nan")


def residualise(W: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Remove voter and recipient level effects, on the cells of the mask.

    The residual of a cell is its points minus the mean of its voter, minus the
    mean of its recipient, plus the grand mean, all computed on the masked
    cells. What is left is the part of the exchange that is not explained by how
    generous the voter is or by how popular the recipient is, which is exactly
    the confound of a raw dyadic correlation between the two layers.
    """
    rows = mask.sum(axis=1)
    cols = mask.sum(axis=0)
    data = np.where(mask, W, 0.0)
    grand = data[mask].mean()
    row_mean = np.divide(data.sum(axis=1), rows, out=np.full(len(rows), grand), where=rows > 0)
    col_mean = np.divide(data.sum(axis=0), cols, out=np.full(len(cols), grand), where=cols > 0)
    return W - row_mean[:, None] - col_mean[None, :] + grand


def statistics(first: np.ndarray, second: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    """The four quantities compared in RQ4, always on the same cells."""
    a, b = first[mask], second[mask]
    both = mask & (first > 0) & (second > 0)
    return {
        "spearman": spearman(a, b),
        "pearson": pearson(a, b),
        "residual_pearson": pearson(residualise(first, mask)[mask], residualise(second, mask)[mask]),
        "jaccard": jaccard((first > 0) & mask, (second > 0) & mask),
        "spearman_both_positive": spearman(first[both], second[both]),
        "cells": float(mask.sum()),
        "both_positive": float(both.sum()),
    }


def qap(
    first: np.ndarray, second: np.ndarray, mask: np.ndarray,
    n_perm: int, rng: np.random.Generator,
) -> tuple[dict[str, float], dict[str, np.ndarray]]:
    """Observed statistics and their permutation distributions.

    The labels of the second network are permuted, rows and columns together.
    The statistic is recomputed on the cells that stay eligible in both, so a
    permutation changes the dyad set as well as the pairing, which is the
    correct null for networks with structural zeros.
    """
    keys = ("spearman", "pearson", "residual_pearson", "jaccard", "spearman_both_positive")
    observed = statistics(first, second, mask)
    null = {key: np.full(n_perm, np.nan) for key in keys}
    n = len(mask)

    for b in range(n_perm):
        order = rng.permutation(n)
        permuted = second[np.ix_(order, order)]
        permuted_mask = mask[np.ix_(order, order)]
        common = mask & permuted_mask
        if common.sum() < 10:
            continue
        sample = statistics(first, permuted, common)
        for key in keys:
            null[key][b] = sample[key]

    return observed, null


def two_sided_p(observed: float, null: np.ndarray) -> float:
    null = null[np.isfinite(null)]
    if len(null) == 0 or not np.isfinite(observed):
        return float("nan")
    centre = null.mean()
    return float((1 + (np.abs(null - centre) >= abs(observed - centre) - 1e-12).sum()) / (len(null) + 1))


def high_p(observed: float, null: np.ndarray) -> float:
    null = null[np.isfinite(null)]
    if len(null) == 0 or not np.isfinite(observed):
        return float("nan")
    return float((1 + (null >= observed).sum()) / (len(null) + 1))


def sign_flip_test(jury: list[float], public: list[float]) -> tuple[float, float]:
    """Exact paired test over the editions: swap the two layers within a year."""
    import itertools

    d = np.asarray(public, float) - np.asarray(jury, float)
    observed = float(d.mean())
    stats = np.array([
        np.mean(d * np.array(s)) for s in itertools.product((1, -1), repeat=len(d))
    ])
    return observed, float((np.abs(stats) >= abs(observed) - 1e-12).mean())


def holm(pvalues: list[float]) -> list[float]:
    order = np.argsort(pvalues)
    out, running = [0.0] * len(pvalues), 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(pvalues) - rank) * pvalues[index]))
        out[index] = running
    return out


def benjamini_hochberg(pvalues: list[float]) -> list[float]:
    order = np.argsort(pvalues)[::-1]
    out, running = [0.0] * len(pvalues), 1.0
    for rank, index in enumerate(order):
        running = min(running, min(1.0, pvalues[index] * len(pvalues) / (len(pvalues) - rank)))
        out[index] = running
    return out


def load_year(year: int) -> dict[str, tuple[list[str], np.ndarray, np.ndarray]]:
    return {
        layer: read_matrix(MATRIX_DIR / f"{year}_{layer}.csv") for layer in LAYERS
    }