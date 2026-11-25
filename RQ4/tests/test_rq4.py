import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import analyze_rq4_temporal_stability as temporal
from rq4_common import Comparison, Edition, FixedEffects, holm, null_summary, permutation_orders


def edition(finalists, seed):
    labels = tuple("ABCDEF")
    roles = np.isin(labels, list(finalists))
    eligible = roles[None, :] & ~np.eye(len(labels), dtype=bool)
    points = np.random.default_rng(seed).integers(0, 13, (2, len(labels), len(labels))) * eligible
    return Edition(labels, points.astype(float), eligible, roles)


class FixedEffectsTests(unittest.TestCase):
    def test_incomplete_mask_matches_independent_least_squares(self):
        voters = np.array([0, 0, 0, 1, 1, 2, 2, 2])
        recipients = np.array([0, 1, 2, 0, 2, 0, 1, 2])
        first = np.array([2, 3, 0, 6, 7, 2, 9, 12], dtype=float)
        second = np.array([3, 1, 1, 7, 6, 1, 10, 8], dtype=float)
        fit = FixedEffects.fit(voters, recipients)
        design = np.column_stack((np.ones(len(voters)), voters == 1, voters == 2,
                                  recipients == 1, recipients == 2))

        def ols_residual(y):
            return y - design @ np.linalg.lstsq(design, y, rcond=None)[0]

        np.testing.assert_allclose(fit.residuals(first), ols_residual(first), atol=1e-12)
        np.testing.assert_allclose(design.T @ fit.residuals(first), 0, atol=1e-12)
        self.assertAlmostEqual(float(fit.correlation(first, second)),
                               np.corrcoef(ols_residual(first), ols_residual(second))[0, 1])
        additive = voters + recipients + 2
        self.assertTrue(np.isnan(fit.correlation(first, additive)))


class PermutationTests(unittest.TestCase):
    def test_masks_and_selected_dyads_survive_a_role_change(self):
        a, b = edition("ABCD", 1), edition("ABEF", 2)
        rng = np.random.default_rng(20)
        comparison = Comparison.align(a, b)
        for batch in zip(permutation_orders(a, 40, rng), permutation_orders(b, 40, rng)):
            moved = []
            for network, order in zip((a, b), batch):
                np.testing.assert_array_equal(network.finalists[order], network.finalists)
                np.testing.assert_array_equal(network.eligible[np.ix_(order, order)], network.eligible)
                for layer in network.points:
                    np.testing.assert_array_equal(np.sort(layer[np.ix_(order, order)], axis=1),
                                                  np.sort(layer[order], axis=1))
                moved.append(network.eligible[np.ix_(order, order)])
            self.assertEqual(list(zip(*np.nonzero(moved[0] & moved[1]))),
                             list(zip(*comparison.first)))

    def test_shared_edition_and_layer_orders(self):
        editions = {2019: edition("ABCD", 1), 2021: edition("ABEF", 2), 2022: edition("ACDE", 3)}
        _, comparisons = temporal.observed_pairs(editions, 1)
        rng = np.random.default_rng(140)
        orders = {year: permutation_orders(net, 3, rng) for year, net in editions.items()}
        with patch.object(temporal, "permutation_orders", side_effect=list(orders.values())) as permute:
            actual = temporal.temporal_batch(editions, comparisons, 3, rng)
        self.assertEqual(permute.call_count, len(editions))
        for call, net in zip(permute.call_args_list, editions.values()):
            self.assertIs(call.args[0], net)

        expected = np.zeros((2, 3))
        for (year_a, year_b), pair in comparisons.items():
            for layer in range(2):
                for replicate in range(3):
                    a = editions[year_a].points[layer][np.ix_(*([orders[year_a][replicate]] * 2))]
                    b = editions[year_b].points[layer][np.ix_(*([orders[year_b][replicate]] * 2))]
                    x, y = pair.effects.residuals(a[pair.first]), pair.effects.residuals(b[pair.second])
                    expected[layer, replicate] += np.corrcoef(x, y)[0, 1] / len(comparisons)
        np.testing.assert_allclose(actual, expected, atol=1e-12)

    def test_monte_carlo_tails_and_holm(self):
        samples = np.array([-2, -1, 0, 1, 2])
        self.assertAlmostEqual(null_summary(3, samples)["p_raw"], 2 / 6)
        self.assertAlmostEqual(null_summary(-3, samples)["p_raw"], 2 / 6)
        self.assertEqual(null_summary(0, samples)["p_raw"], 1)
        np.testing.assert_allclose(holm([0.04, 0.001, 0.02]), [0.04, 0.003, 0.04])


class RobustnessTests(unittest.TestCase):
    def test_fixed_support_and_exclusion_of_incident_pairs(self):
        editions = {2019: edition("ABCD", 1), 2021: edition("ABEF", 2),
                    2022: edition("ACDE", 3), 2023: edition("ACDF", 4)}
        fixed = temporal.always_eligible(editions)
        self.assertEqual(fixed, {(country, "A") for country in "BCDEF"})
        records, _ = temporal.observed_pairs(editions, 3)
        remaining = temporal.without_edition(records, 2021)
        self.assertEqual({(row["year_a"], row["year_b"]) for row in remaining}, {(2022, 2023)})
        fixed_records, _ = temporal.observed_pairs(editions, 1, fixed)
        self.assertEqual({(row["cells"], row["voters"], row["recipients"]) for row in fixed_records},
                         {(5, 5, 1)})
        self.assertTrue(all(np.isnan(row["residual_pearson"]) for row in fixed_records))


if __name__ == "__main__":
    unittest.main()
