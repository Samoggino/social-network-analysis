#!/usr/bin/env python3
"""RQ2: Eurovision-rule constrained null for community modularity.

For each edition/layer, keep the voters, finalist eligibility, and each 58-point
ballot (scores 1..8, 10, 12). Draw ten distinct eligible recipients per voter
uniformly and randomly assign the ten scores. This destroys voter preferences
but preserves voting opportunities and the exact ballot rule.

Each replicate is projected undirected and re-optimised with Louvain, so the
comparison accounts for community optimisation on random networks. The null
is NOT a degree/strength-preserving configuration model; it is a separate
process-level baseline complementary to the fixed-topology weight shuffle.
"""
from __future__ import annotations

import csv
from pathlib import Path

import networkx as nx
import numpy as np

from analyze_rq2_partitions import (
    YEARS, LAYERS, SEED, load_matrix, weighted_projection, louvain_labels,
    benjamini_hochberg, holm, sign_flip_test,
)

ROOT = Path(__file__).resolve().parent.parent
MATRIX_DIR = ROOT / "processed_data" / "matrices"
RESULTS_DIR = ROOT / "results" / "rq2"
N_NULL = 2000  # quick reproducible run; raise to >=1000 for publication-grade Monte Carlo
BALLOT = np.array([1, 2, 3, 4, 5, 6, 7, 8, 10, 12], dtype=int)


def modularity_optimized(graph: nx.Graph, nodes: list[str], seed: int) -> float:
    communities = nx.community.louvain_communities(graph, weight="weight", seed=seed)
    return float(nx.community.modularity(graph, communities, weight="weight"))


def random_ballots(voters: list[str], finalists: set[str], rng: np.random.Generator) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(set(voters)))
    for voter in sorted(voters):
        eligible = sorted(finalists - {voter})
        if len(eligible) < len(BALLOT):
            raise ValueError(f"Insufficient finalists for {voter}")
        targets = rng.choice(eligible, len(BALLOT), replace=False)
        scores = rng.permutation(BALLOT)
        for target, points in zip(targets, scores):
            graph.add_edge(voter, str(target), weight=int(points))
    return graph


def save_csv(path: Path, header: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([round(v, 10) if isinstance(v, float) else v for v in r])


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = []
    for year in YEARS:
        for layer in LAYERS:
            directed, voters, finalists = load_matrix(MATRIX_DIR / f"{year}_{layer}.csv")
            voters = sorted(voters)
            reference = weighted_projection(directed)
            for scope in ("all", "finalists"):
                observed_graph = reference if scope == "all" else reference.subgraph(finalists).copy()
                nodes = sorted(observed_graph.nodes())
                observed = modularity_optimized(observed_graph, nodes, SEED)
                simulated = np.empty(N_NULL)
                for b in range(N_NULL):
                    randomized = random_ballots(voters, finalists, rng)
                    projected = weighted_projection(randomized)
                    sample = projected if scope == "all" else projected.subgraph(finalists).copy()
                    simulated[b] = modularity_optimized(sample, nodes, SEED)
                mean = float(simulated.mean())
                sd = float(simulated.std(ddof=1))
                p = (1 + int((simulated >= observed).sum())) / (N_NULL + 1)
                rows.append((year, layer, scope, observed, mean, sd,
                             observed - mean, (observed - mean) / sd if sd else float("nan"), p))
            print(f"{year} {layer}: ballot null complete", flush=True)

    columns = ["year", "layer", "scope", "observed_modularity", "null_mean", "null_sd", "excess", "z", "p_one_sided"]
    save_csv(RESULTS_DIR / "rq2_ballot_null.csv", columns, rows)
    comparisons = []
    for scope in ("all", "finalists"):
        for metric in ("excess", "z"):
            k = columns.index(metric)
            jury = [r[k] for r in rows if r[1] == "jury" and r[2] == scope]
            public = [r[k] for r in rows if r[1] == "public" and r[2] == scope]
            difference, p = sign_flip_test(jury, public)
            comparisons.append((scope, metric, difference, p))
    ps = [r[-1] for r in comparisons]
    save_csv(RESULTS_DIR / "rq2_ballot_null_layer_diff.csv",
             ["scope", "metric", "public_minus_jury", "p_exact", "p_holm", "p_fdr"],
             [r + (h, q) for r, h, q in zip(comparisons, holm(ps), benjamini_hochberg(ps))])


if __name__ == "__main__":
    main()
