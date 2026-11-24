#!/usr/bin/env python3
"""Shared machinery for RQ5: walk-forward prediction of the top-3 recipients.

Import only. The analysis script is analyze_rq5_prediction.py.

Target. For each voter i, layer L and test edition t, rank the eligible
recipients j and keep the first three: they are the predicted recipients of the
12, 10 and 8 points. The question is not the exact order 12/10/8 (which is a
possible extension), but whether the three countries are the right ones.

Models. Four nested additive scores, as in the project proposal:

    M0a  popularity of the recipient in the training editions
    M0b  M0a + the historical direct tie i -> j and its reciprocity j -> i
    M1   M0b + same UN subregion and shared language family
    M2   M1 + same community (Louvain on the training networks) and the
         community's internal high-vote rate

Each model is a logistic regression for P(the voter gives 8+ points to the
recipient), with L2 penalty, fitted on the eligible dyads of the training
editions. The coefficients are therefore learned, not chosen by hand, and the
ranking is produced by the predicted probability.

Walk-forward. For a test edition t the training set is every edition before t
(2016-2019 and 2021 onwards, 2020 cancelled). Everything that could carry
information from the test edition - popularity, direct ties, group rates,
communities, scaling and coefficients - is rebuilt from the training editions
only, inside each fold.

Classification threshold. The proposal fixes the number of positives: three per
ballot. For this reason the evaluation is a ranking one (top-3) and not a
classification one, and it is computed only on recipients that were eligible
for that specific voter and edition.
"""

from __future__ import annotations

import csv
from pathlib import Path

import networkx as nx
import numpy as np

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
HIGH = 8                      # 8, 10 and 12 points; exactly three per ballot
SMOOTH = 5.0                  # a in p_G = (k_G + a p0) / (n_G + a)
L2 = 1.0                      # fixed ex ante, on standardised features
COMMUNITY_SEEDS = range(10)   # Louvain seeds; the best modularity is kept
TOP_K = 3

FOLDS = (
    (2023, (2016, 2017, 2018, 2019, 2021, 2022)),
    (2024, (2016, 2017, 2018, 2019, 2021, 2022, 2023)),
    (2025, (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024)),
    (2026, (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025)),
)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "src" else SCRIPT_DIR
MATRIX_DIR = ROOT.parent / "RQ1" / "processed_data" / "matrices"
ATTRIBUTES = ROOT.parent / "RQ2" / "processed_data" / "tables" / "country_attributes_rq2.csv"
RESULTS_DIR = ROOT / "results" / "rq5"
FIGURES_DIR = ROOT / "figures" / "rq5"

FEATURES = (
    "pop", "tie", "tie_points", "recip",
    "same_region", "shared_language", "same_community", "cohesion",
)

MODELS = {
    "M0a": ("pop",),
    "M0b": ("pop", "tie", "tie_points", "recip"),
    "M1": ("pop", "tie", "tie_points", "recip", "same_region", "shared_language"),
    "M2": ("pop", "tie", "tie_points", "recip", "same_region", "shared_language",
           "same_community", "cohesion"),
}
MODEL_ORDER = tuple(MODELS)


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
    # The voting rule is fixed: ten scores per ballot, three of them 8 or more.
    for i, country in enumerate(countries):
        given = W[i][W[i] > 0]
        if len(given) == 0:
            continue
        if len(given) != 10 or int((given >= HIGH).sum()) != TOP_K:
            raise ValueError(
                f"Unexpected ballot for {country} in {path.name}: "
                f"{len(given)} scores, {int((given >= HIGH).sum())} high"
            )
    return countries, W, E


def load_all() -> dict[tuple[int, str], tuple[list[str], np.ndarray, np.ndarray]]:
    return {
        (year, layer): read_matrix(MATRIX_DIR / f"{year}_{layer}.csv")
        for year in YEARS
        for layer in LAYERS
    }


def load_attributes(path: Path = ATTRIBUTES) -> dict[str, dict]:
    """Country attributes, with the language families as a set."""
    if not path.is_file():
        raise FileNotFoundError(f"Attribute table not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    attributes = {}
    for row in rows:
        attributes[row["country"]] = {
            "region": row["region"],
            "languages": {part.strip() for part in row["language_groups"].split(";") if part.strip()},
            "block": row["eurovision_block"],
        }
    return attributes


class Training:
    """Historical statistics of one fold and one layer, training editions only.

    Countries are mapped to a global index so that editions with different
    participants can be accumulated. Every count is a number of eligible
    opportunities: a high-vote rate is always "high votes / times the voter
    could vote for that recipient".
    """

    def __init__(self, matrices, layer: str, years: tuple[int, ...],
                 universe: list[str], attributes: dict[str, dict]):
        index = {country: position for position, country in enumerate(universe)}
        size = len(universe)
        self.universe = universe
        self.index = index
        self.layer = layer
        self.attributes = attributes

        self.high_received = np.zeros(size)
        self.opportunities_received = np.zeros(size)
        self.high_direct = np.zeros((size, size))
        self.opportunities_direct = np.zeros((size, size))
        self.points_sum = np.zeros((size, size))

        for year in years:
            countries, W, E = matrices[(year, layer)]
            positions = np.array([index[country] for country in countries])
            rows, columns = np.nonzero(E)
            ii, jj = positions[rows], positions[columns]
            values = W[rows, columns]
            high = values >= HIGH

            np.add.at(self.opportunities_direct, (ii, jj), 1.0)
            np.add.at(self.points_sum, (ii, jj), values)
            np.add.at(self.high_direct, (ii, jj), high.astype(float))
            np.add.at(self.opportunities_received, jj, 1.0)
            np.add.at(self.high_received, jj, high.astype(float))

        self.p0 = float(self.high_direct.sum() / self.opportunities_direct.sum())
        self.mean_points = float(self.points_sum.sum() / self.opportunities_direct.sum())

        # Smoothed rates, as in the proposal.
        self.pop = (self.high_received + SMOOTH * self.p0) / (
            self.opportunities_received + SMOOTH)
        self.tie = (self.high_direct + SMOOTH * self.p0) / (
            self.opportunities_direct + SMOOTH)
        self.tie_points = (self.points_sum + SMOOTH * self.mean_points) / (
            self.opportunities_direct + SMOOTH)
        # Reciprocity: the same rate in the other direction. It uses the
        # transposed counts, so an opportunity that does not exist is smoothed
        # to p0 and does not become a zero.
        self.recip = (self.high_direct.T + SMOOTH * self.p0) / (
            self.opportunities_direct.T + SMOOTH)

        self.partition, self.community_info = louvain_partition(
            matrices, layer, years, universe)
        self.cohesion = self._community_cohesion()

    def _community_cohesion(self) -> dict[int, float]:
        """Smoothed internal high-vote rate of each community, minus p0."""
        communities: dict[int, float] = {}
        labels = np.array([self.partition[country] for country in self.universe])
        for community in set(labels.tolist()):
            members = labels == community
            internal = np.ix_(members, members)
            opportunities = self.opportunities_direct[internal].sum()
            high = self.high_direct[internal].sum()
            communities[community] = float(
                ((high + SMOOTH * self.p0) / (opportunities + SMOOTH)) - self.p0)
        return communities

    def features(self, i: int, j: int) -> tuple[float, ...]:
        same_region = 1.0 if self.attributes[self.universe[i]]["region"] == \
            self.attributes[self.universe[j]]["region"] else 0.0
        shared_language = 1.0 if (
            self.attributes[self.universe[i]]["languages"]
            & self.attributes[self.universe[j]]["languages"]) else 0.0
        same_community = 1.0 if self.partition[self.universe[i]] == \
            self.partition[self.universe[j]] else 0.0
        cohesion = same_community * self.cohesion[self.partition[self.universe[i]]]
        return (
            self.pop[j],
            self.tie[i, j],
            self.tie_points[i, j] / 12.0,
            self.recip[i, j],
            same_region,
            shared_language,
            same_community,
            cohesion,
        )


def louvain_partition(matrices, layer: str, years: tuple[int, ...],
                      universe: list[str]) -> tuple[dict[str, int], dict[str, float]]:
    """Louvain on the undirected aggregate of the training networks.

    Only training editions enter the graph. Of COMMUNITY_SEEDS runs the one with
    the highest modularity is kept, so the result does not depend on a lucky
    seed; the spread of the modularity is reported by the analysis script.
    """
    graph = nx.Graph()
    graph.add_nodes_from(universe)
    for year in years:
        countries, W, E = matrices[(year, layer)]
        for a, country_a in enumerate(countries):
            for b, country_b in enumerate(countries):
                if a != b and E[a, b] and W[a, b] > 0:
                    weight = float(W[a, b])
                    if graph.has_edge(country_a, country_b):
                        graph[country_a][country_b]["weight"] += weight
                    else:
                        graph.add_edge(country_a, country_b, weight=weight)

    best_partition, best_modularity = None, -np.inf
    for seed in COMMUNITY_SEEDS:
        partition = nx.algorithms.community.louvain_communities(
            graph, weight="weight", seed=seed)
        modularity = nx.algorithms.community.modularity(graph, partition, weight="weight")
        if modularity > best_modularity:
            best_partition, best_modularity = partition, modularity

    labels: dict[str, int] = {}
    for label, community in enumerate(sorted(best_partition, key=lambda c: sorted(c)[0])):
        for country in community:
            labels[country] = label
    for country in universe:                     # isolated countries
        labels.setdefault(country, len(labels))
    return labels, {
        "modularity": float(best_modularity),
        "communities": len(best_partition),
        "weighted_edges": float(graph.number_of_edges()),
    }


def build_design(training: Training, countries: list[str], W: np.ndarray,
                 E: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Feature matrix and target for every eligible dyad of one edition."""
    rows, columns = np.nonzero(E)
    ii = np.array([training.index[country] for country in np.array(countries)[rows]])
    jj = np.array([training.index[country] for country in np.array(countries)[columns]])
    X = np.array([training.features(int(i), int(j)) for i, j in zip(ii, jj)])
    y = (W[rows, columns] >= HIGH).astype(float)
    return X, y, np.column_stack([rows, columns])


def standardise(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = X.mean(axis=0)
    scale = X.std(axis=0)
    scale[scale == 0] = 1.0
    return (X - mean) / scale, mean, scale


def fit_logistic(X: np.ndarray, y: np.ndarray, l2: float = L2,
                 max_iter: int = 100) -> np.ndarray:
    """L2 logistic regression by Newton iterations (no scipy needed)."""
    n, d = X.shape
    design = np.hstack([np.ones((n, 1)), X])
    penalty = l2 * np.r_[0.0, np.ones(d)]
    beta = np.zeros(d + 1)
    for _ in range(max_iter):
        linear = design @ beta
        p = 1.0 / (1.0 + np.exp(-np.clip(linear, -35, 35)))
        weight = np.clip(p * (1 - p), 1e-8, None)
        gradient = design.T @ (p - y) + penalty * beta
        hessian = (design * weight[:, None]).T @ design + np.diag(penalty)
        step = np.linalg.solve(hessian, gradient)
        beta -= step
        if np.abs(step).max() < 1e-8:
            break
    return beta


def score(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    return beta[0] + X @ beta[1:]


def ranking_metrics(true: set[int], ranked: list[int], k: int = TOP_K) -> tuple[float, float, float]:
    """Hit@k, NDCG@k and reciprocal rank of the first true recipient."""
    top = ranked[:k]
    hits = len(set(top) & true)
    hit = hits / k
    dcg = sum(1.0 / np.log2(position + 2) for position, item in enumerate(top) if item in true)
    idcg = sum(1.0 / np.log2(position + 2) for position in range(min(k, len(true))))
    ndcg = dcg / idcg if idcg else 0.0
    reciprocal = 0.0
    for position, item in enumerate(ranked):
        if item in true:
            reciprocal = 1.0 / (position + 1)
            break
    return hit, ndcg, reciprocal