"""Validation, fixed effects and conditional permutation tests for RQ4."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
METRICS = ("spearman", "pearson", "residual_pearson", "jaccard")
PRIMARY = "residual_pearson"
BALLOT = (1, 2, 3, 4, 5, 6, 7, 8, 10, 12)
N_PERM = 9999
SEED = 42
BATCH_SIZE = 160
ROOT = Path(__file__).resolve().parents[1]
MATRIX_DIR = ROOT.parent / "RQ1" / "processed_data" / "matrices"


def parser(description: str, seed: int) -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=description)
    cli.add_argument("--matrices", type=Path, default=MATRIX_DIR)
    cli.add_argument("--output-dir", type=Path, default=ROOT)
    cli.add_argument("--permutations", type=int, default=N_PERM)
    cli.add_argument("--seed", type=int, default=seed)
    return cli


def read_matrix(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header, *records = csv.reader(handle)
    countries = tuple(header[1:])
    if (header[0] != "country" or not countries or
            len(set(countries)) != len(countries) or
            [row[0] for row in records] != list(countries) or
            any(len(row) != len(header) for row in records)):
        raise ValueError(f"Invalid matrix coordinates in {path}")
    eligibility = np.array([[bool(value.strip()) for value in row[1:]] for row in records])
    points = np.array([[float(value) if value.strip() else 0 for value in row[1:]]
                       for row in records])
    if "WLD" in countries or not np.all(np.isin(points, (0, *BALLOT))):
        raise ValueError(f"Unexpected source or scores in {path}")
    if any(tuple(sorted(row[row > 0])) != BALLOT for row in points):
        raise ValueError(f"Invalid national ballot in {path}")
    return countries, points, eligibility


@dataclass(frozen=True)
class Edition:
    countries: tuple[str, ...]
    points: np.ndarray
    eligible: np.ndarray
    finalists: np.ndarray


def load_editions(directory: Path) -> dict[int, Edition]:
    editions = {}
    for year in YEARS:
        countries, jury, eligible = read_matrix(directory / f"{year}_jury.csv")
        public_countries, public, public_eligible = read_matrix(directory / f"{year}_public.csv")
        if countries != public_countries or not np.array_equal(eligible, public_eligible):
            raise ValueError(f"{year}: layers do not share the same countries and eligibility")
        finalists = eligible.any(axis=0)
        expected = finalists[None, :] & ~np.eye(len(countries), dtype=bool)
        if not np.array_equal(expected, eligible):
            raise ValueError(f"{year}: eligibility cannot be preserved by the planned role blocks")
        editions[year] = Edition(countries, np.stack((jury, public)), eligible, finalists)
    return editions


def permutation_orders(edition: Edition, size: int, rng: np.random.Generator) -> np.ndarray:
    """Generate and verify mask-preserving permutations of the full edition."""
    identity = np.arange(len(edition.countries))
    orders = np.tile(identity, (size, 1))
    for role in (False, True):
        group = identity[edition.finalists == role]
        for order in orders:
            order[group] = rng.permutation(group)
    if not np.all(np.sort(orders, axis=1) == identity):
        raise RuntimeError("A country permutation is not bijective")
    moved = edition.eligible[orders[:, :, None], orders[:, None, :]]
    if not np.all(moved == edition.eligible):
        raise RuntimeError("A country permutation changed eligibility")
    return orders


@dataclass(frozen=True)
class FixedEffects:
    basis: np.ndarray

    @classmethod
    def fit(cls, voters: np.ndarray, recipients: np.ndarray) -> FixedEffects:
        if len(voters) == 0:
            return cls(np.empty((0, 0)))
        _, row = np.unique(voters, return_inverse=True)
        _, col = np.unique(recipients, return_inverse=True)
        design = np.column_stack((np.eye(row.max() + 1)[row], np.eye(col.max() + 1)[col]))
        # The intercept is already in the span of the two indicator sets.
        u, singular, _ = np.linalg.svd(design, full_matrices=False)
        tolerance = singular[0] * max(design.shape) * np.finfo(float).eps
        return cls(u[:, singular > tolerance])

    def residuals(self, values: np.ndarray) -> np.ndarray:
        return values - (values @ self.basis) @ self.basis.T

    def correlation(self, first: np.ndarray, second: np.ndarray) -> np.ndarray:
        """Compute residual inner products without reconstructing every residual."""
        a = first @ self.basis
        b = second @ self.basis
        var_a = np.sum(first * first, axis=-1) - np.sum(a * a, axis=-1)
        var_b = np.sum(second * second, axis=-1) - np.sum(b * b, axis=-1)
        numerator = np.sum(first * second, axis=-1) - np.sum(a * b, axis=-1)
        valid = (var_a > 1e-8) & (var_b > 1e-8) & (first.shape[-1] >= 3)
        denominator = np.sqrt(np.maximum(var_a, 0) * np.maximum(var_b, 0))
        return np.divide(numerator, denominator, out=np.full_like(numerator, np.nan), where=valid)


@dataclass(frozen=True)
class Comparison:
    first: tuple[np.ndarray, np.ndarray]
    second: tuple[np.ndarray, np.ndarray]
    effects: FixedEffects

    @classmethod
    def align(cls, first: Edition, second: Edition,
              fixed_dyads: set[tuple[str, str]] | None = None) -> Comparison:
        lookup = {country: i for i, country in enumerate(second.countries)}
        ia = np.array([i for i, c in enumerate(first.countries) if c in lookup], dtype=int)
        ib = np.array([lookup[first.countries[i]] for i in ia], dtype=int)
        mask = first.eligible[np.ix_(ia, ia)] & second.eligible[np.ix_(ib, ib)]
        if fixed_dyads is not None:
            names = [first.countries[i] for i in ia]
            fixed = np.array([[(a, b) in fixed_dyads for b in names] for a in names], dtype=bool)
            mask &= fixed.reshape(mask.shape)
        row, col = np.nonzero(mask)
        return cls((ia[row], ia[col]), (ib[row], ib[col]), FixedEffects.fit(row, col))


def ranks(values: np.ndarray) -> np.ndarray:
    _, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    ends = counts.cumsum()
    return ((2 * ends - counts + 1) / 2)[inverse]


def pearson(first: np.ndarray, second: np.ndarray) -> float:
    if len(first) < 3 or first.std() == 0 or second.std() == 0:
        return float("nan")
    return float(np.corrcoef(first, second)[0, 1])


def spearman(first: np.ndarray, second: np.ndarray) -> float:
    return pearson(ranks(first), ranks(second))


def statistics(first: np.ndarray, second: np.ndarray, effects: FixedEffects) -> dict[str, float]:
    both = (first > 0) & (second > 0)
    union = (first > 0) | (second > 0)
    return {
        "spearman": spearman(first, second),
        "pearson": pearson(first, second),
        PRIMARY: float(effects.correlation(first, second)),
        "jaccard": float(both.sum() / union.sum()) if union.any() else float("nan"),
        "spearman_both_positive": spearman(first[both], second[both]),
    }


def null_summary(observed: float, samples: np.ndarray) -> dict:
    """The equal-tail two-sided Monte Carlo p-value includes the observed draw."""
    if not np.isfinite(observed) or not np.isfinite(samples).all() or len(samples) == 0:
        raise ValueError("Non-finite primary statistic in the observed or permuted data")
    lower = (1 + np.count_nonzero(samples <= observed + 1e-12)) / (len(samples) + 1)
    upper = (1 + np.count_nonzero(samples >= observed - 1e-12)) / (len(samples) + 1)
    q025, q975 = np.quantile(samples, [0.025, 0.975])
    return {"null_mean": float(samples.mean()), "null_q025": float(q025),
            "null_q975": float(q975), "p_raw": min(1.0, 2 * min(lower, upper)),
            "permutations": len(samples)}


def holm(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    cumulative, result = 0.0, [0.0] * len(values)
    for rank, (index, p_value) in enumerate(ordered):
        cumulative = max(cumulative, min(1.0, (len(values) - rank) * p_value))
        result[index] = cumulative
    return result


def adjust(records: list[dict]) -> None:
    for record, p_holm in zip(records, holm([record["p_raw"] for record in records])):
        record["p_holm"] = p_holm


NULL_FIELDS = ("null_mean", "null_q025", "null_q975", "p_raw", "p_holm", "permutations")


def save_csv(root: Path, filename: str, fields: tuple[str, ...], records: list[dict]) -> None:
    path = root / "results" / "rq4" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for record in records:
            row = []
            for field in fields:
                value = record.get(field, "")
                if isinstance(value, (float, np.floating)):
                    value = round(float(value), 10) if np.isfinite(value) else ""
                row.append(value)
            writer.writerow(row)


def figure_path(root: Path, filename: str) -> Path:
    path = root / "figures" / "rq4" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
