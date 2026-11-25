"""Historical features, community detection and ranking metrics for RQ5."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import networkx as nx
import numpy as np

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
TEST_YEARS = (2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
BALLOT = (1, 2, 3, 4, 5, 6, 7, 8, 10, 12)
HIGH = 8
TOP_K = 3
SMOOTH = 5.0
L2 = 1.0
COMMUNITY_SEEDS = range(10)
CONSENSUS_SEEDS = 200
TIE_SEED = 42
MIN_HISTORY = 2
MAX_ITER = 100
STEP_TOL = 1e-8
GRADIENT_TOL = 1e-7

ROOT = Path(__file__).resolve().parents[1]
MATRIX_DIR = ROOT.parent / "RQ1" / "processed_data" / "matrices"
ATTRIBUTES = ROOT.parent / "RQ2" / "processed_data" / "tables" / "country_attributes_rq2.csv"
RQ2_SRC = ROOT.parent / "RQ2" / "src"

FEATURES = ("pop", "tie", "tie_points", "recip", "same_region", "shared_language",
            "same_community", "cohesion")
MODELS = {"M0a": FEATURES[:1], "M0b": FEATURES[:4], "M1": FEATURES[:6], "M2": FEATURES}
BASELINE = "History"
CONSENSUS_MODEL = "M2_consensus"
MODEL_ORDER = (BASELINE, *MODELS)


def save_csv(root: Path, filename: str, fields: tuple[str, ...], records: list[dict]) -> None:
    path = root / "results" / "rq5" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({key: round(float(value), 10) if isinstance(value, (float, np.floating))
                             else value for key, value in record.items()})


def read_matrix(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header, *records = csv.reader(handle)
    countries = tuple(header[1:])
    if (header[0] != "country" or not countries or len(set(countries)) != len(countries)
            or "WLD" in countries or any(len(row) != len(header) for row in records)
            or [row[0] for row in records] != list(countries)):
        raise ValueError(f"Invalid country coordinates in {path}")
    eligible = np.array([[bool(value.strip()) for value in row[1:]] for row in records])
    finalists = eligible.any(axis=0)
    if not np.array_equal(eligible, finalists[None, :] & ~np.eye(len(countries), dtype=bool)):
        raise ValueError(f"Invalid eligibility in {path}")
    votes = np.array([[float(value) if value.strip() else 0.0 for value in row[1:]] for row in records])
    for country, ballot in zip(countries, votes):
        if not np.all(np.isin(ballot, (0, *BALLOT))) or tuple(sorted(ballot[ballot > 0])) != BALLOT:
            raise ValueError(f"Invalid ballot for {country} in {path}")
    return countries, votes, eligible


def load_attributes(path: Path) -> dict:
    attributes = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            country, region = row["country"], row["region"].strip()
            languages = frozenset(part.strip() for part in row["language_groups"].split(";") if part.strip())
            if country in attributes or not region or not languages:
                raise ValueError(f"Duplicate or incomplete attributes for {country}")
            attributes[country] = (region, languages)
    return attributes


class History:
    """Votes and graph observed strictly before one edition, in one voting layer."""

    def __init__(self, matrices: dict, layer: str, before: int, attributes: dict):
        self.years = tuple(sorted(y for y, kind in matrices if kind == layer and y < before))
        if not self.years:
            raise ValueError(f"No history for {layer} before {before}")
        names = sorted({country for year in self.years for country in matrices[year, layer][0]})
        self.index = {country: position for position, country in enumerate(names)}
        self.attributes = attributes
        self.opportunities = np.zeros((len(names), len(names)))
        high, points = np.zeros_like(self.opportunities), np.zeros_like(self.opportunities)
        graph = nx.Graph()
        graph.add_nodes_from(names)
        for year in self.years:
            countries, votes, eligible = matrices[year, layer]
            positions = np.array([self.index[country] for country in countries])
            row, col = np.nonzero(eligible)
            values = votes[row, col]
            ii, jj = positions[row], positions[col]
            np.add.at(self.opportunities, (ii, jj), 1)
            np.add.at(high, (ii, jj), values >= HIGH)
            np.add.at(points, (ii, jj), values)
            for i, j, value in zip(row, col, values):
                if value > 0:
                    a, b = countries[i], countries[j]
                    edge = graph.get_edge_data(a, b, {"weight": 0.0})
                    graph.add_edge(a, b, weight=edge["weight"] + float(value))
        self.high = high
        self.p0 = float(high.sum() / self.opportunities.sum())
        self.mean_points = float(points.sum() / self.opportunities.sum())
        self.base_rate = (SMOOTH * self.p0) / SMOOTH
        self.base_points = (SMOOTH * self.mean_points) / SMOOTH
        self.pop = (high.sum(axis=0) + SMOOTH * self.p0) / (self.opportunities.sum(axis=0) + SMOOTH)
        self.tie = (high + SMOOTH * self.p0) / (self.opportunities + SMOOTH)
        self.tie_points = (points + SMOOTH * self.mean_points) / (self.opportunities + SMOOTH)
        self.graph = graph
        self.partitions = {}
        self.set_partition("best", self.best_partition())

    def best_partition(self) -> list[set[str]]:
        candidates = (nx.community.louvain_communities(self.graph, weight="weight", seed=seed)
                      for seed in COMMUNITY_SEEDS)
        return max(candidates, key=lambda groups: nx.community.modularity(self.graph, groups, weight="weight"))

    def set_partition(self, method: str, groups: list[set[str]]) -> None:
        labels, cohesion = {}, {}
        for label, group in enumerate(sorted(groups, key=lambda members: min(members))):
            for country in group:
                labels[country] = label
            positions = [self.index[country] for country in sorted(group)]
            internal = np.ix_(positions, positions)
            value = (self.high[internal].sum() + SMOOTH * self.p0) / (
                self.opportunities[internal].sum() + SMOOTH)
            cohesion[label] = float(value - self.p0)
        self.partitions[method] = (labels, cohesion, len(groups),
                                   nx.community.modularity(self.graph, groups, weight="weight"))

    def learn_consensus(self, method) -> None:
        nodes = list(self.index)
        groups = method(self.graph, nodes)
        self.set_partition("consensus", groups)

    def has_history(self, voter: str, recipient: str) -> bool:
        i, j = self.index.get(voter), self.index.get(recipient)
        return i is not None and j is not None and bool(self.opportunities[i, j] > 0)

    def features(self, voter: str, recipient: str, method: str = "best") -> tuple:
        i, j = self.index.get(voter), self.index.get(recipient)
        region_i, languages_i = self.attributes[voter]
        region_j, languages_j = self.attributes[recipient]
        labels, cohesion, _, _ = self.partitions[method]
        joint = i is not None and j is not None
        same = joint and labels[voter] == labels[recipient]
        return (self.pop[j] if j is not None else self.base_rate,
                self.tie[i, j] if joint else self.base_rate,
                (self.tie_points[i, j] if joint else self.base_points) / 12.0,
                self.tie[j, i] if joint else self.base_rate,
                float(region_i == region_j), float(bool(languages_i & languages_j)),
                float(same), cohesion[labels[voter]] if same else 0.0)


def design(history: History, countries: tuple, eligibility: np.ndarray, method: str) -> np.ndarray:
    return np.array([history.features(countries[i], countries[j], method)
                     for i, j in zip(*np.nonzero(eligibility))])


def standardise(X: np.ndarray):
    mean, scale = X.mean(axis=0), X.std(axis=0)
    scale[scale == 0] = 1
    return (X - mean) / scale, mean, scale


def probabilities(linear: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(linear, -35, 35)))


def fit_logistic(X: np.ndarray, y: np.ndarray):
    """L2-regularised logistic regression, with explicit convergence checks."""
    if not np.isfinite(X).all() or not np.isfinite(y).all() or set(np.unique(y)) != {0, 1}:
        raise ValueError("Invalid logistic design or targets")
    matrix = np.column_stack((np.ones(len(X)), X))
    penalty = L2 * np.r_[0.0, np.ones(X.shape[1])]
    coef = np.zeros(matrix.shape[1])
    gradient_inf = float("inf")
    for iteration in range(1, MAX_ITER + 1):
        p = probabilities(matrix @ coef)
        gradient = matrix.T @ (p - y) + penalty * coef
        weight = np.clip(p * (1 - p), 1e-8, None)
        hessian = (matrix * weight[:, None]).T @ matrix + np.diag(penalty)
        step = np.linalg.solve(hessian, gradient)
        coef -= step
        if not np.isfinite(coef).all():
            raise ValueError("Non-finite logistic coefficients")
        next_p = probabilities(matrix @ coef)
        gradient_inf = float(np.max(np.abs(matrix.T @ (next_p - y) + penalty * coef)))
        if np.max(np.abs(step)) < STEP_TOL and gradient_inf <= GRADIENT_TOL:
            return coef, {"iterations": iteration, "converged": 1, "gradient_inf": gradient_inf}
    raise ValueError(f"Logistic regression did not converge in {MAX_ITER} iterations (gradient {gradient_inf})")


def rank_scores(candidates: tuple[str, ...], values: np.ndarray, year: int, voter: str,
                secondary: np.ndarray | None = None):
    """Return the revised and legacy ranking, with a tie flag at the cutoff."""
    # Byte-sorted SHA-256 keys are stable across Python processes and file order.
    priority = [hashlib.sha256(f"{TIE_SEED}:{year}:{voter}:{country}".encode()).digest()
                for country in candidates]
    second = np.zeros(len(values)) if secondary is None else secondary
    order = sorted(range(len(values)), key=lambda i: (-values[i], -second[i], priority[i], candidates[i]))
    legacy = np.argsort(-values, kind="mergesort")
    boundary = len(order) > TOP_K and all(
        scores[order[TOP_K - 1]] == scores[order[TOP_K]] for scores in (values, second))
    return (tuple(candidates[i] for i in order), tuple(candidates[i] for i in legacy), boundary)


def ranking_metrics(true: set, ranked: tuple, k: int = TOP_K) -> tuple[float, float, float]:
    top = ranked[:k]
    hit = len(set(top) & true) / k
    dcg = sum(1 / np.log2(position + 2) for position, item in enumerate(top) if item in true)
    idcg = sum(1 / np.log2(position + 2) for position in range(min(k, len(true))))
    reciprocal = next((1 / (i + 1) for i, candidate in enumerate(ranked) if candidate in true), 0.0)
    return hit, dcg / idcg if idcg else 0.0, reciprocal
