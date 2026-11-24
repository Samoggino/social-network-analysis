#!/usr/bin/env python3
"""RQ5: walk-forward prediction of the top-3 recipients (12, 10 and 8 points).

Run from the RQ5 directory:
    python src/analyze_rq5_prediction.py

Question. Do geography, language and the communities found in the voting
networks improve the prediction of strong voting ties in later editions, beyond
the popularity of the recipient and the historical preference between the two
countries?

Design. For every voter, edition and layer the eligible recipients are ranked
and the first three are kept: they are the predicted recipients of 12, 10 and 8
points. The four models are nested, and each is a logistic regression fitted on
the eligible dyads of the training editions:

    M0a  popularity of the recipient
    M0b  M0a + direct historical tie i -> j and reciprocity j -> i
    M1   M0b + same UN subregion and shared language family
    M2   M1 + same training-time community and its internal high-vote rate

Walk-forward folds, as in the proposal: test 2023 on 2016-2019 and 2021-2022,
then 2024, 2025 and 2026 adding one edition at a time. Popularity, ties, group
rates, communities, scaling and coefficients are rebuilt inside each fold from
the training editions only, so no information from the test edition enters the
model.

Metrics. Hit@3 (share of the three true recipients found among the first
three, which equals precision and recall at 3 for a single ballot), NDCG@3 and
MRR as secondary measures. The comparison with the constrained random baseline
and, above all, between M0b and M1/M2 is the point of the exercise. With four
test editions the results are reported per edition and layer, not only as a
mean, and the year-level spread is part of the result.
"""

from __future__ import annotations

import itertools

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rq5_common import (
    FEATURES,
    FIGURES_DIR,
    FOLDS,
    HIGH,
    LAYERS,
    MODELS,
    MODEL_ORDER,
    RESULTS_DIR,
    TOP_K,
    Training,
    build_design,
    fit_logistic,
    load_all,
    load_attributes,
    ranking_metrics,
    save_csv,
    score,
    standardise,
)

SEED = 42
N_BOOTSTRAP = 2000
COMPARISONS = (
    ("M0b", "M0a"),   # value of the direct historical tie
    ("M1", "M0b"),    # value of geography and language
    ("M2", "M1"),     # value of the SNA communities
    ("M2", "M0b"),    # everything beyond the strong baseline
)


def fit_models(X: np.ndarray, y: np.ndarray) -> dict[str, dict]:
    """Standardise once and fit each nested model on its own feature subset."""
    standardised, mean, scale = standardise(X)
    fitted: dict[str, dict] = {}
    for name, columns in MODELS.items():
        index = np.array([FEATURES.index(column) for column in columns])
        beta = fit_logistic(standardised[:, index], y)
        fitted[name] = {
            "beta": beta,
            "index": index,
            "mean": mean[index],
            "scale": scale[index],
        }
    return fitted


def evaluate(fitted: dict[str, dict], training: Training, countries: list[str],
             W: np.ndarray, E: np.ndarray) -> list[dict]:
    """Rank the eligible recipients of every voter and score the four models."""
    position = {country: training.index[country] for country in countries}
    records = []
    for voter, country in enumerate(countries):
        eligible = np.flatnonzero(E[voter])
        if len(eligible) == 0:
            continue
        true = set(eligible[(W[voter, eligible] >= HIGH)].tolist())
        if not true:
            continue
        global_voter = position[country]
        X = np.array([
            training.features(global_voter, position[countries[recipient]])
            for recipient in eligible
        ])
        for name in MODEL_ORDER:
            model = fitted[name]
            Xs = (X[:, model["index"]] - model["mean"]) / model["scale"]
            values = score(model["beta"], Xs)
            order = np.argsort(-values, kind="mergesort")
            ranked = [int(eligible[index]) for index in order]
            hit, ndcg, reciprocal = ranking_metrics(true, ranked)
            records.append({
                "test_year": None,
                "layer": None,
                "model": name,
                "voter": country,
                "eligible": len(eligible),
                "hit3": hit,
                "ndcg3": ndcg,
                "mrr": reciprocal,
                "random_hit3": TOP_K / len(eligible),
            })
    return records


def aggregate(records: list[dict], year: int, layer: str) -> dict[str, dict]:
    for record in records:
        record["test_year"] = year
        record["layer"] = layer
    summary: dict[str, dict] = {}
    for name in MODEL_ORDER:
        subset = [record for record in records if record["model"] == name]
        summary[name] = {
            "voters": len(subset),
            "hit3": float(np.mean([r["hit3"] for r in subset])),
            "ndcg3": float(np.mean([r["ndcg3"] for r in subset])),
            "mrr": float(np.mean([r["mrr"] for r in subset])),
            "random_hit3": float(np.mean([r["random_hit3"] for r in subset])),
        }
    return summary


def plot(predictions: list[dict], comparison: list[dict]) -> None:
    """Left: hit@3 by model, mean and range over the test editions. Right: lifts."""
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    positions = np.arange(len(MODEL_ORDER))
    layer_colour = {"jury": "#246b91", "public": "#cf7135"}

    for layer, offset in (("jury", -0.18), ("public", 0.18)):
        means, lows, highs = [], [], []
        for name in MODEL_ORDER:
            values = [p["hit3"] for p in predictions
                      if p["layer"] == layer and p["model"] == name]
            means.append(float(np.mean(values)))
            lows.append(float(np.min(values)))
            highs.append(float(np.max(values)))
        axes[0].bar(positions + offset, means, width=0.34,
                    color=layer_colour[layer], label=layer.title())
        axes[0].errorbar(positions + offset, means,
                         yerr=[np.array(means) - np.array(lows),
                               np.array(highs) - np.array(means)],
                         fmt="none", color="#333333", linewidth=1)
    axes[0].axhline(float(np.mean([p["random_hit3"] for p in predictions])),
                    color="#666666", linestyle=":", linewidth=0.9,
                    label="Random, three eligible")
    axes[0].set_xticks(positions, MODEL_ORDER)
    axes[0].set_ylabel("Hit@3")
    axes[0].set_title("Top-3 hit rate, mean and range over the test editions")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(axis="y", alpha=0.2)

    for index, (better, baseline) in enumerate(COMPARISONS):
        for layer, offset in (("jury", -0.18), ("public", 0.18)):
            value = float(np.mean([
                row["mean_diff"] for row in comparison
                if row["layer"] == layer and row["comparison"] == f"{better}-{baseline}"
            ]))
            axes[1].bar(index + offset, value, width=0.34,
                        color=layer_colour[layer], label=layer.title() if index == 0 else None)
    axes[1].axhline(0, color="#333333", linewidth=0.8)
    axes[1].set_xticks(range(len(COMPARISONS)), [f"{a} - {b}" for a, b in COMPARISONS])
    axes[1].set_ylabel("Mean difference in Hit@3")
    axes[1].set_title("Added value of each block of features")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].grid(axis="y", alpha=0.2)

    figure.suptitle("RQ5 - Prediction of the top-3 recipients")
    figure.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    figure.savefig(FIGURES_DIR / "rq5_hit3_by_model.png", dpi=200)
    plt.close(figure)


def sign_flip(differences: list[float]) -> float:
    """Exact two-sided test over the few test editions (2^4 = 16 sign flips)."""
    observed = float(np.mean(differences))
    values = np.array([
        np.mean(np.array(differences) * np.array(signs))
        for signs in itertools.product((1, -1), repeat=len(differences))
    ])
    return float((np.abs(values) >= abs(observed) - 1e-12).mean())


def bootstrap(differences_by_year: dict[int, list[float]], years: tuple[int, ...],
              rng: np.random.Generator) -> tuple[float, float]:
    """Stratified bootstrap over voters, resampling inside each test edition."""
    draws = []
    for _ in range(N_BOOTSTRAP):
        per_year = []
        for year in years:
            values = np.array(differences_by_year[year])
            per_year.append(np.mean(values[rng.integers(0, len(values), len(values))]))
        draws.append(np.mean(per_year))
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def main() -> None:
    matrices = load_all()
    attributes = load_attributes()
    universe = sorted({country for countries, _, _ in matrices.values()
                       for country in countries})
    years = tuple(test for test, _ in FOLDS)
    rng = np.random.default_rng(SEED)

    predictions: list[dict] = []
    coefficients: list[list] = []
    diagnostics: list[list] = []
    differences: dict[tuple[str, str, str], dict[int, list[float]]] = {}

    for test_year, train_years in FOLDS:
        for layer in LAYERS:
            training = Training(matrices, layer, train_years, universe, attributes)

            parts, targets = [], []
            for year in train_years:
                countries, W, E = matrices[(year, layer)]
                X, y, _ = build_design(training, countries, W, E)
                parts.append(X)
                targets.append(y)
            X_train = np.vstack(parts)
            y_train = np.concatenate(targets)
            fitted = fit_models(X_train, y_train)

            for name in MODEL_ORDER:
                model = fitted[name]
                for column, beta in zip(MODELS[name], model["beta"][1:]):
                    coefficients.append([test_year, layer, name, column, float(beta)])

            countries, W, E = matrices[(test_year, layer)]
            fold_records = evaluate(fitted, training, countries, W, E)
            summary = aggregate(fold_records, test_year, layer)

            for name in MODEL_ORDER:
                entry = summary[name]
                predictions.append({
                    "test_year": test_year, "layer": layer, "model": name, **entry,
                })
            diagnostics.append([
                test_year, layer, len(train_years), X_train.shape[0], int(y_train.sum()),
                training.p0, training.community_info["communities"],
                training.community_info["modularity"], summary["M0a"]["voters"],
                float(np.mean([r["random_hit3"] for r in fold_records])),
            ])

            for better, baseline in COMPARISONS:
                paired = {}
                for model in (better, baseline):
                    paired[model] = {
                        r["voter"]: r["hit3"] for r in fold_records if r["model"] == model
                    }
                per_voter = [paired[better][voter] - paired[baseline][voter]
                             for voter in paired[better]]
                differences.setdefault((layer, better, baseline), {})[test_year] = per_voter

            print(f"{test_year}: {layer} trained on {len(train_years)} editions, "
                  f"Hit@3 M0b {summary['M0b']['hit3']:.3f}, M2 {summary['M2']['hit3']:.3f}",
                  flush=True)

    save_csv(
        RESULTS_DIR / "rq5_predictions_by_year.csv",
        ["test_year", "layer", "model", "voters", "hit3", "ndcg3", "mrr", "random_hit3"],
        [[p["test_year"], p["layer"], p["model"], p["voters"], p["hit3"], p["ndcg3"],
          p["mrr"], p["random_hit3"]] for p in predictions],
    )
    save_csv(
        RESULTS_DIR / "rq5_coefficients.csv",
        ["test_year", "layer", "model", "feature", "coefficient"],
        coefficients,
    )
    save_csv(
        RESULTS_DIR / "rq5_fold_diagnostics.csv",
        ["test_year", "layer", "training_editions", "training_dyads", "positives",
         "p0", "communities", "modularity", "voters", "random_hit3"],
        diagnostics,
    )

    comparison_rows = []
    for layer in LAYERS:
        for better, baseline in COMPARISONS:
            per_voter = differences[(layer, better, baseline)]
            yearly = [float(np.mean(per_voter[year])) for year in years]
            all_values = np.concatenate([np.array(per_voter[year]) for year in years])
            low, high = bootstrap(per_voter, years, rng)
            comparison_rows.append([
                layer, f"{better}-{baseline}", float(np.mean(yearly)),
                float(np.min(yearly)), float(np.max(yearly)),
                sum(value > 0 for value in yearly), sign_flip(yearly), low, high,
                float(np.mean(all_values)),
            ])
    save_csv(
        RESULTS_DIR / "rq5_model_comparison.csv",
        ["layer", "comparison", "mean_diff", "min_year", "max_year", "years_better",
         "p_exact_4years", "ci_low", "ci_high", "mean_diff_voter_level"],
        comparison_rows,
    )

    comparison_records = [
        {"layer": row[0], "comparison": row[1], "mean_diff": row[2]}
        for row in comparison_rows
    ]
    plot(predictions, comparison_records)

    print(f"Results: {RESULTS_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    print("RQ5 complete.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise SystemExit(f"RQ5 failed: {exc}") from exc