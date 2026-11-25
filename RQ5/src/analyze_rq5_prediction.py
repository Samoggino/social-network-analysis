"""Walk-forward prediction of Eurovision's three high-point recipients."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from rq5_common import (
    ATTRIBUTES, BASELINE, COMMUNITY_SEEDS, CONSENSUS_MODEL, CONSENSUS_SEEDS, FEATURES,
    GRADIENT_TOL, HIGH, L2, LAYERS, MATRIX_DIR, MAX_ITER, MIN_HISTORY, MODELS, MODEL_ORDER,
    ROOT, RQ2_SRC, SMOOTH, STEP_TOL, TEST_YEARS, TIE_SEED, TOP_K, YEARS, History, design,
    fit_logistic, load_attributes, rank_scores, ranking_metrics, read_matrix, save_csv, standardise,
)

METRICS = ("hit3", "ndcg3", "mrr")
COMPARISONS = (("M0b", "M0a"), ("M1", "M0b"), ("M2", "M1"), ("M2", "M0b"),
               *((model, BASELINE) for model in MODELS))


def load_consensus(rq2_src: Path):
    """Reuse only the RQ2 consensus routines, without running its analysis."""
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(rq2_src.resolve()))
    try:
        from analyze_rq2_consensus import co_assignment_matrix, consensus_labels, modal
    finally:
        sys.path.pop(0)
        sys.dont_write_bytecode = previous

    def partition(graph, nodes):
        co_assignment, sizes, _ = co_assignment_matrix(graph, nodes, n_seeds=CONSENSUS_SEEDS)
        labels = consensus_labels(co_assignment, modal(sizes))
        return [{country for country, label in zip(nodes, labels) if label == group}
                for group in np.unique(labels)]

    return partition


@dataclass(frozen=True)
class Fitted:
    beta: np.ndarray
    indices: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    features: tuple[str, ...]
    diagnostics: dict

    def score(self, X: np.ndarray) -> np.ndarray:
        return self.beta[0] + ((X[:, self.indices] - self.mean) / self.scale) @ self.beta[1:]


def fit_models(X: np.ndarray, y: np.ndarray, models: dict) -> dict[str, Fitted]:
    scaled, mean, scale = standardise(X)
    fitted = {}
    for model, features in models.items():
        indices = np.array([FEATURES.index(feature) for feature in features])
        beta, diagnostics = fit_logistic(scaled[:, indices], y)
        fitted[model] = Fitted(beta, indices, mean[indices], scale[indices], features, diagnostics)
    return fitted


def fit_fold(matrices: dict, layer: str, test_year: int, attributes: dict,
             histories: dict, consensus=None):
    def get_history(before):
        key = (layer, before)
        if key not in histories:
            histories[key] = History(matrices, layer, before, attributes)
        history = histories[key]
        if consensus is not None and "consensus" not in history.partitions:
            history.learn_consensus(consensus)
        return history

    current = get_history(test_year)
    row_years = current.years[MIN_HISTORY:]
    target_parts = []
    features = {"best": [], "consensus": []}
    for year in row_years:
        past = get_history(year)
        countries, votes, eligible = matrices[year, layer]
        features["best"].append(design(past, countries, eligible, "best"))
        if consensus is not None:
            features["consensus"].append(design(past, countries, eligible, "consensus"))
        target_parts.append((votes[eligible] >= HIGH).astype(float))
    y = np.concatenate(target_parts)
    fitted = fit_models(np.vstack(features["best"]), y, MODELS)
    if consensus is not None:
        fitted.update(fit_models(np.vstack(features["consensus"]), y, {CONSENSUS_MODEL: FEATURES}))
    return current, fitted, {"training_editions": len(current.years), "row_editions": len(row_years),
                             "training_dyads": len(y), "positives": int(y.sum()), "p0": current.p0}


def predict(history: History, fitted: dict, countries: tuple, eligible: np.ndarray,
            year: int) -> list[dict]:
    """Produce the full rankings given only the known roster and prior features."""
    predictions = []
    for i, voter in enumerate(countries):
        candidates = tuple(countries[j] for j in np.flatnonzero(eligible[i]))
        if len(candidates) < TOP_K:
            raise ValueError(f"Insufficient eligible recipients for {voter} in {year}")
        X = np.array([history.features(voter, recipient) for recipient in candidates])
        choices = {BASELINE: (X[:, FEATURES.index("tie_points")], X[:, FEATURES.index("pop")])}
        for model, fit in fitted.items():
            values = X
            if model == CONSENSUS_MODEL:
                values = np.array([history.features(voter, recipient, "consensus") for recipient in candidates])
            choices[model] = (fit.score(values), None)
        for model, (scores, secondary) in choices.items():
            ranked, old_ranked, tie = rank_scores(candidates, scores, year, voter, secondary)
            predictions.append({"voter": voter, "model": model, "ranked": ranked,
                                "legacy": old_ranked, "cutoff_tie": int(tie)})
    return predictions


def evaluate(predictions: list[dict], history: History, countries: tuple,
             votes: np.ndarray, eligible: np.ndarray) -> list[dict]:
    truths = {country: {countries[j] for j in np.flatnonzero(eligible[i] & (votes[i] >= HIGH))}
              for i, country in enumerate(countries)}
    if any(len(true) != TOP_K for true in truths.values()):
        raise ValueError("Expected exactly three high-point recipients in every ballot")
    results = []
    for result in predictions:
        voter = result["voter"]
        true = truths[voter]
        ranked = result["ranked"]
        found = set(ranked[:TOP_K]) & true
        seen = {recipient for recipient in true if history.has_history(voter, recipient)}
        results.append({
            "model": result["model"], "cutoff_tie": result["cutoff_tie"], "random_hit3": TOP_K / len(ranked),
            **dict(zip(METRICS, ranking_metrics(true, ranked))),
            **{f"legacy_{m}": value for m, value in zip(METRICS, ranking_metrics(true, result["legacy"]))},
            "seen": len(seen), "found_seen": len(found & seen),
            "unseen": len(true - seen), "found_unseen": len(found - seen),
        })
    return results


def average(values) -> float:
    return float(np.mean(list(values)))


def summarise(evaluated: list[dict], year: int, layer: str) -> list[dict]:
    summary = []
    for model in dict.fromkeys(row["model"] for row in evaluated):
        rows = [row for row in evaluated if row["model"] == model]
        summary.append({
            "test_year": year, "layer": layer, "model": model, "voters": len(rows),
            **{metric: average(r[metric] for r in rows) for metric in (*METRICS, "random_hit3")},
            "cutoff_ties": sum(r["cutoff_tie"] for r in rows),
        })
    return summary


def compare(predictions: dict) -> tuple[list[dict], list[dict]]:
    comparisons, robustness = [], []
    for layer in LAYERS:
        for model, reference in COMPARISONS:
            delta = {y: predictions[y, layer, model]["hit3"] - predictions[y, layer, reference]["hit3"]
                     for y in TEST_YEARS}
            comparisons.append({
                "layer": layer, "comparison": f"{model}-{reference}", "mean_diff": average(delta.values()),
                "min_year": min(delta.values()), "max_year": max(delta.values()),
                "years_better": sum(v > 1e-12 for v in delta.values()),
                **{f"delta_{y}": v for y, v in delta.items()},
            })
            for excluded in TEST_YEARS:
                kept = [y for y in TEST_YEARS if y != excluded]
                value = average(predictions[y, layer, model]["hit3"] for y in kept)
                base = average(predictions[y, layer, reference]["hit3"] for y in kept)
                robustness.append({"scenario": "leave_one_edition_out", "test_year": excluded,
                                   "layer": layer, "model": model, "reference": reference, "metric": "hit3",
                                   "value": value, "reference_value": base, "difference": value - base,
                                   "observations": len(kept)})
    return comparisons, robustness


def fold_sensitivity(evaluated: list[dict], summary: dict, year: int, layer: str) -> list[dict]:
    records = []
    for model, current in summary.items():
        rows = [row for row in evaluated if row["model"] == model]
        info = {"test_year": year, "layer": layer, "model": model}
        for coverage in ("seen", "unseen"):
            count = sum(row[coverage] for row in rows)
            found = sum(row[f"found_{coverage}"] for row in rows)
            records.append({"scenario": f"recovery_{coverage}", **info, "metric": "positive_recall",
                            "value": found / count if count else "", "observations": count, "found": found})
        if model in MODELS:
            for metric in METRICS:
                original_ties = average(r[f"legacy_{metric}"] for r in rows)
                records.append({"scenario": "tie_break", **info, "reference": "legacy_column_order",
                                "metric": metric, "value": current[metric], "reference_value": original_ties,
                                "difference": current[metric] - original_ties, "observations": len(rows)})
    for reference in ("M1", "M2"):
        for metric in METRICS:
            value, base = summary[CONSENSUS_MODEL][metric], summary[reference][metric]
            records.append({"scenario": "consensus", "test_year": year, "layer": layer,
                            "model": CONSENSUS_MODEL, "reference": reference, "metric": metric,
                            "value": value, "reference_value": base, "difference": value - base,
                            "observations": summary[reference]["voters"]})
    return records


def plot(root: Path, predictions: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.1), sharey=True, layout="constrained")
    palette = ("#1d557a", "#3d7e64", "#b25a25", "#71538c")
    for ax, layer in zip(axes, LAYERS):
        values = np.array([[predictions[year, layer, model]["hit3"] for model in MODEL_ORDER]
                           for year in TEST_YEARS])
        x = np.arange(len(MODEL_ORDER))
        for i, year in enumerate(TEST_YEARS):
            ax.scatter(x + (i - 1.5) * .115, values[i], s=40, color=palette[i], label=str(year), zorder=3)
        ax.scatter(x, values.mean(axis=0), marker="_", s=250, linewidth=2.8, color="#252525",
                   label="Mean over editions", zorder=4)
        random = average(predictions[y, layer, "M0a"]["random_hit3"] for y in TEST_YEARS)
        ax.axhline(random, color="#757575", linestyle="--", label="Random mean", zorder=1)
        ax.set(xticks=x, xticklabels=MODEL_ORDER, ylim=(0, 0.57),
               title="National televote" if layer == "public" else "Jury")
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Hit@3")
    axes[1].legend(loc="upper left", ncols=3, fontsize=8, frameon=False)
    fig.suptitle("RQ5 | Top-three recipients in the four test editions")
    folder = root / "figures" / "rq5"
    folder.mkdir(parents=True, exist_ok=True)
    fig.savefig(folder / "rq5_hit3_by_model.png", dpi=180)
    plt.close(fig)


def fingerprint(paths: dict[str, Path]) -> dict:
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}


def run(matrices_dir: Path, attributes_file: Path, rq2_src: Path, root: Path) -> None:
    paths = {(year, layer): matrices_dir / f"{year}_{layer}.csv" for year in YEARS for layer in LAYERS}
    input_paths = {f"matrices/{path.name}": path for path in paths.values()}
    input_paths["attributes/country_attributes_rq2.csv"] = attributes_file
    for name in ("analyze_rq2_consensus.py", "analyze_rq2_partitions.py"):
        input_paths[f"rq2_method/{name}"] = rq2_src / name
    hashes = fingerprint(input_paths)
    matrices = {key: read_matrix(path) for key, path in paths.items()}
    attributes = load_attributes(attributes_file)
    consensus = load_consensus(rq2_src)
    histories, predictions = {}, {}
    coefficients, folds, diagnostics, robust = [], [], [], []
    for year in TEST_YEARS:
        for layer in LAYERS:
            history, fitted, info = fit_fold(matrices, layer, year, attributes, histories, consensus)
            countries, votes, eligible = matrices[year, layer]
            ranked = predict(history, fitted, countries, eligible, year)
            evaluated = evaluate(ranked, history, countries, votes, eligible)
            summary = {row["model"]: row for row in summarise(evaluated, year, layer)}
            predictions.update({(year, layer, name): summary[name] for name in MODEL_ORDER})
            _, _, n_communities, modularity = history.partitions["best"]
            _, _, n_consensus, consensus_modularity = history.partitions["consensus"]
            fold_labels = {"test_year": year, "layer": layer}
            folds.append({**fold_labels, **info, "communities": n_communities, "modularity": modularity,
                          "consensus_communities": n_consensus, "consensus_modularity": consensus_modularity,
                          "voters": len(countries), "random_hit3": summary["M0a"]["random_hit3"]})
            for model, fit in fitted.items():
                diagnostics.append({**fold_labels, "model": model, **fit.diagnostics,
                                    "gradient_inf": f"{fit.diagnostics['gradient_inf']:.12e}"})
                for feature, beta in zip(fit.features, fit.beta[1:]):
                    coefficients.append({**fold_labels, "model": model, "feature": feature, "coefficient": beta})
            robust.extend(fold_sensitivity(evaluated, summary, year, layer))
            print(f"{year} {layer}: M0b={summary['M0b']['hit3']:.3f}, M2={summary['M2']['hit3']:.3f}",
                  flush=True)
    comparisons, omitted = compare(predictions)
    robust.extend(omitted)
    if hashes != fingerprint(input_paths):
        raise RuntimeError("An input changed during the RQ5 analysis")
    save_csv(root, "rq5_predictions_by_year.csv",
             ("test_year", "layer", "model", "voters", *METRICS, "random_hit3", "cutoff_ties"),
             list(predictions.values()))
    save_csv(root, "rq5_model_comparison.csv",
             ("layer", "comparison", "mean_diff", "min_year", "max_year", "years_better",
              *(f"delta_{year}" for year in TEST_YEARS)), comparisons)
    save_csv(root, "rq5_coefficients.csv",
             ("test_year", "layer", "model", "feature", "coefficient"), coefficients)
    save_csv(root, "rq5_fold_diagnostics.csv",
             ("test_year", "layer", "training_editions", "row_editions", "training_dyads", "positives", "p0",
              "communities", "modularity", "consensus_communities", "consensus_modularity",
              "voters", "random_hit3"), folds)
    save_csv(root, "rq5_fit_diagnostics.csv",
             ("test_year", "layer", "model", "iterations", "converged", "gradient_inf"), diagnostics)
    save_csv(root, "rq5_robustness.csv",
             ("scenario", "test_year", "layer", "model", "reference", "metric", "value",
              "reference_value", "difference", "observations", "found"), robust)
    config = {
        "folds": {y: [past for past in YEARS if past < y] for y in TEST_YEARS},
        "layers": LAYERS, "minimum_editions_of_history": MIN_HISTORY, "high_score_threshold": HIGH,
        "top_k": TOP_K, "smoothing": SMOOTH, "solver": {"l2": L2, "max_iter": MAX_ITER,
                                                     "step_tolerance": STEP_TOL,
                                                     "gradient_tolerance": GRADIENT_TOL},
        "tie_seed": TIE_SEED, "louvain_seeds": list(COMMUNITY_SEEDS),
        "consensus_seeds": list(range(CONSENSUS_SEEDS)), "inputs_sha256": hashes,
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "networkx": nx.__version__, "matplotlib": matplotlib.__version__},
    }
    (root / "results" / "rq5" / "rq5_run_config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    plot(root, predictions)


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--matrices", type=Path, default=MATRIX_DIR)
    cli.add_argument("--attributes", type=Path, default=ATTRIBUTES)
    cli.add_argument("--rq2-src", type=Path, default=RQ2_SRC)
    cli.add_argument("--output-dir", type=Path, default=ROOT)
    options = cli.parse_args()
    run(options.matrices, options.attributes, options.rq2_src, options.output_dir)


if __name__ == "__main__":
    main()
