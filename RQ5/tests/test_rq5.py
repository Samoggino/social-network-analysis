import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import rq5_common as common
from analyze_rq5_prediction import evaluate, fit_fold, predict


def small_ballots(countries, seed):
    eligible = ~np.eye(len(countries), dtype=bool)
    votes = np.zeros(eligible.shape)
    rng = np.random.default_rng(seed)
    for i, options in enumerate(eligible):
        votes[i, rng.permutation(np.flatnonzero(options))] = [12, 10, 8, 4, 0][:options.sum()]
    return countries, votes, eligible


class TemporalTests(unittest.TestCase):
    def test_test_votes_and_future_roster_cannot_change_a_prior_prediction(self):
        names = tuple("ABCDEF")
        attributes = {name: ("R", frozenset({name, "shared"})) for name in (*names, "Z")}
        matrices = {(year, "jury"): small_ballots(names, year) for year in (2018, 2019, 2021, 2022, 2023)}
        graph_inputs = []

        def consensus(graph, nodes):
            graph_inputs.append((set(graph), set(nodes)))
            return [set(nodes)]

        history, fitted, _ = fit_fold(matrices, "jury", 2023, attributes, {}, consensus)
        countries, votes, eligible = matrices[2023, "jury"]
        prediction = predict(history, fitted, countries, eligible, 2023)
        altered = matrices.copy()
        altered[2023, "jury"] = small_ballots(names, 10)
        altered[2026, "jury"] = small_ballots(tuple("ABCDFZ"), 13)
        other, other_fit, _ = fit_fold(altered, "jury", 2023, attributes, {}, consensus)
        self.assertEqual(prediction, predict(other, other_fit, countries, eligible, 2023))
        self.assertTrue(all(a == b == set(names) for a, b in graph_inputs))
        for model in fitted:
            np.testing.assert_array_equal(fitted[model].beta, other_fit[model].beta)
        self.assertNotEqual(evaluate(prediction, history, countries, votes, eligible),
                            evaluate(prediction, other, *altered[2023, "jury"]))

    def test_timing_and_features_for_unknown_countries(self):
        names = tuple("ABCDEF")
        matrix = small_ballots(names, 2)
        attrs = {name: ("R" if name != "Z" else "S", frozenset({"Shared"}))
                 for name in (*names, "Z")}
        history = common.History({(2021, "public"): matrix, (2022, "public"): matrix}, "public", 2022, attrs)
        self.assertEqual(history.years, (2021,))
        self.assertEqual(set(history.graph), set(names))
        _, points, _ = matrix
        features = history.features("A", "B")
        a, p0, pbar = common.SMOOTH, history.p0, history.mean_points
        self.assertAlmostEqual(features[1], (int(points[0, 1] >= 8) + a * p0) / (1 + a))
        self.assertAlmostEqual(features[2], (points[0, 1] + a * pbar) / (1 + a) / 12)
        self.assertAlmostEqual(features[3], (int(points[1, 0] >= 8) + a * p0) / (1 + a))
        np.testing.assert_allclose(history.features("A", "Z"),
                                   (p0, p0, pbar / 12, p0, 0, 1, 0, 0))
        self.assertTrue(history.has_history("A", "B"))
        self.assertFalse(history.has_history("A", "Z"))


class RankingTests(unittest.TestCase):
    def test_metrics_measured_at_correct_positions(self):
        truth = {"A", "C", "D"}
        hit, ndcg, mrr = common.ranking_metrics(truth, ("B", "A", "D", "C", "E"))
        self.assertAlmostEqual(hit, 2 / 3)
        self.assertAlmostEqual(ndcg, (1 / np.log2(3) + 1 / 2) / (1 + 1 / np.log2(3) + 1 / 2))
        self.assertEqual(mrr, 1 / 2)
        self.assertEqual(common.ranking_metrics(truth, ("B", "E", "F", "A", "C", "D")), (0, 0, .25))

    def test_tie_break_is_stable_under_input_permutation(self):
        names = tuple("ABCDE")
        scores = np.array([1, 1, 1, 1, 0])
        actual, legacy, tied = common.rank_scores(names, scores, 2023, "Q")
        order = np.array([3, 4, 0, 1, 2])
        shuffled = common.rank_scores(tuple(np.array(names)[order]), scores[order], 2023, "Q")
        self.assertEqual(actual, shuffled[0])
        self.assertTrue(tied)
        self.assertEqual(legacy, names)
        ranked, _, tied = common.rank_scores(names, scores, 2023, "Q", np.arange(5))
        self.assertEqual(ranked, tuple("DCBAE"))
        self.assertFalse(tied)

    def test_prediction_excludes_ineligible_recipients(self):
        names, votes, eligible = small_ballots(tuple("ABCDEF"), 2023)
        hist = common.History({(2022, "jury"): (names, votes, eligible)}, "jury", 2023,
                              {name: ("R", frozenset({"L"})) for name in names})
        rows = predict(hist, {}, names, eligible, 2023)
        for index, row in enumerate(rows):
            self.assertEqual(set(row["ranked"]), {name for name, allowed in zip(names, eligible[index]) if allowed})
            self.assertNotIn(row["voter"], row["ranked"])


class ValidationTests(unittest.TestCase):
    def test_matrix_keeps_zero_separate_from_ineligible(self):
        names = tuple("ABCDEFGHIJKL")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "matrix.csv"
            records = []
            for voter in names:
                choices = iter(common.BALLOT + (0,))
                records.append([voter, *("" if name == voter else next(choices) for name in names)])
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows([("country", *names), *records])
            _, points, mask = common.read_matrix(path)
            self.assertEqual(points[0, -1], 0)
            self.assertTrue(mask[0, -1])
            self.assertFalse(mask[0, 0])
            records[0][1] = 0
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows([("country", *names), *records])
            with self.assertRaisesRegex(ValueError, "eligibility"):
                common.read_matrix(path)

    def test_solver_checks_convergence(self):
        X = np.array([[-2], [-1], [0], [1], [2], [3]], dtype=float)
        y = np.array([0, 0, 1, 0, 1, 1], dtype=float)
        beta, diagnostics = common.fit_logistic(X, y)
        self.assertTrue(np.isfinite(beta).all())
        self.assertLessEqual(diagnostics["gradient_inf"], common.GRADIENT_TOL)
        with patch.object(common, "MAX_ITER", 1):
            with self.assertRaisesRegex(ValueError, "did not converge"):
                common.fit_logistic(X, y)


if __name__ == "__main__":
    unittest.main()
