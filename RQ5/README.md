# RQ5 — Walk-Forward Prediction of Strong Voting Ties

**Research question.** Do geographical, linguistic and network-based communities improve the prediction of strong voting ties in future Eurovision editions, beyond historical popularity and pairwise voting patterns?

The target is not the winner or the exact score of a song. For every voter and layer the analysis ranks the eligible recipients and keeps the first three: they are the predicted recipients of the 12, 10 and 8 points. The question is whether the groups found in RQ2 and RQ3 add predictive value out of sample. A negative answer is informative and was anticipated in the proposal.

## Data and conventions

- 10 Grand Finals, 2016–2026 (2020 cancelled), jury and public layers kept separate, WLD excluded.
- Input matrices: `../RQ1/processed_data/matrices/`. `W[i, j]` = points from voter *i* to recipient *j*; an empty cell is an impossible vote.
- Attributes: `../RQ2/processed_data/tables/country_attributes_rq2.csv` — UN M49 subregion (`region`) and language families (`language_groups`, a `;`-separated set for multilingual countries).
- Each ballot gives ten scores and exactly three of them are 8 or more; the loader verifies this on every matrix and stops otherwise. The three high scores are the target.
- The eligible recipients of the test edition are known before the show and are used to define the ranking set. The model never sees the test ballots.

## Walk-forward design

No random split of the vote rows: that would leave the same editions in training and test. The folds follow the proposal, and every quantity that could carry information from the test edition is rebuilt inside the fold from the training editions only.

| Fold | Training editions | Test edition |
|---|---|---|
| 1 | 2016–2019, 2021–2022 | 2023 |
| 2 | 2016–2019, 2021–2023 | 2024 |
| 3 | 2016–2019, 2021–2024 | 2025 |
| 4 | 2016–2019, 2021–2025 | 2026 |

Popularity, direct ties, group rates, the Louvain partition, the feature scaling and the regression coefficients are all recomputed from scratch in each fold.

**Training rows use the past only, like the test rows.** Inside a fold, the features of a training edition *y* are computed from the training editions *before y*, never from *y* itself: the tie i→j of a 2019 training row comes from 2016–2018. Otherwise the features of a training row would contain its own target, the regression would learn inflated coefficients for the history features, and those coefficients would not hold on the test edition, whose features necessarily come from the past. The first two editions of each fold (2016 and 2017) therefore serve only as history: the training rows come from 4, 5, 6 and 7 editions in the four folds (`row_editions` in the diagnostics). The test edition uses all the training editions as history. The hyperparameters are fixed ex ante, not tuned on the four test editions: L2 penalty 1.0 on standardised features and smoothing constant a = 5 in every rate. This follows the proposal, which allows either an inner temporal validation or ex-ante values.

## Models

The four models are nested logistic regressions for P(the voter gives 8+ points to the recipient), fitted on the eligible dyads of the training editions. The predicted probability orders the eligible recipients; the first three are the prediction. Coefficients are learned, never chosen by hand.

| Model | Features | What it adds |
|---|---|---|
| M0a — popularity | `pop` | Historical rate at which the recipient receives 8+ points from any voter |
| M0b — historical tie | M0a + `tie`, `tie_points`, `recip` | Historical direct 8+ rate of i→j, mean points of i→j, and reciprocity j→i |
| M1 — external factors | M0b + `same_region`, `shared_language` | Geography (UN subregion) and language family |
| M2 — SNA communities | M1 + `same_community`, `cohesion` | Same Louvain community on the training networks, and the community's internal high-vote rate |

- `pop`, `tie` and `recip` are smoothed rates: (high votes + a·p0) / (opportunities + a), where p0 is the training base rate (0.119).
- `tie_points` is the smoothed mean points given, divided by 12 only to keep the scale comparable.
- `cohesion` is the smoothed internal high-vote rate of the voter's community minus p0; it is zero when voter and recipient are in different communities.
- Reciprocity is placed in M0b, not in M2, because it is a property of the dyad rather than of the community. M2 therefore tests the community structure alone, given the full dyadic history. This is a small, conservative deviation from the illustrative grouping of the proposal.
- Communities: Louvain on the undirected aggregate of the training voting networks (edge weight = points accumulated over the training editions), ten seeds, the partition with the highest modularity is kept. The modularity is 0.085–0.101 for juries and 0.139–0.154 for the public across the folds. The number of communities is 4, 4, 3, 3 for both layers: the partitions are coarse and broadly geographical, and they are recomputed in every fold.

## Metrics and inference

- **Hit@3** — share of the three true high-vote recipients found among the first three. With three true and three predicted recipients this equals Precision@3 and Recall@3 at the ballot level.
- **NDCG@3** and **MRR** — secondary measures that also weight the order of the three recipients.
- **Constrained random baseline** — three eligible recipients picked at random. Its expected Hit@3 is 3/n, with n ≈ 25 eligible recipients, so about 0.12. The historical M0b, not this baseline, is the decisive comparison.
- Results are reported per edition and layer, with the mean and the range over the four folds. The thousands of vote dyads are not thousands of independent editions, so the uncertainty is computed by a **stratified bootstrap over voters**, resampling voters inside each test edition (2000 draws, seed 42), on the paired per-voter Hit@3 differences. The exact sign-flip test over the four editions is reported for completeness, but with four editions its smallest attainable two-sided p is 0.125, so it cannot reject at 0.05 and the bootstrap interval is the main inferential tool.

## Results

Mean over the four test editions (range in Hit@3 across editions in brackets):

| Layer | Model | Hit@3 | NDCG@3 | MRR |
|---|---|---:|---:|---:|
| Jury | M0a | 0.234 (0.171–0.306) | 0.241 | 0.474 |
| Jury | M0b | **0.246** (0.198–0.306) | 0.260 | 0.494 |
| Jury | M1 | 0.235 (0.180–0.279) | 0.256 | 0.507 |
| Jury | M2 | 0.230 (0.210–0.261) | 0.256 | 0.516 |
| Public | M0a | 0.210 (0.162–0.252) | 0.238 | 0.508 |
| Public | M0b | 0.427 (0.360–0.459) | 0.463 | 0.726 |
| Public | M1 | 0.428 (0.342–0.477) | 0.459 | 0.712 |
| Public | M2 | **0.430** (0.333–0.477) | 0.461 | 0.711 |
| Random | — | 0.121 | — | — |

Hit@3 by edition:

| Layer | Edition | M0a | M0b | M1 | M2 |
|---|---|---:|---:|---:|---:|
| Jury | 2023 | 0.306 | 0.306 | 0.279 | 0.261 |
| Jury | 2024 | 0.171 | 0.198 | 0.180 | 0.216 |
| Jury | 2025 | 0.279 | 0.270 | 0.270 | 0.234 |
| Jury | 2026 | 0.181 | 0.210 | 0.210 | 0.210 |
| Public | 2023 | 0.198 | 0.432 | 0.414 | 0.432 |
| Public | 2024 | 0.252 | 0.360 | 0.342 | 0.333 |
| Public | 2025 | 0.162 | 0.459 | 0.477 | 0.477 |
| Public | 2026 | 0.229 | 0.457 | 0.476 | 0.476 |

Model comparisons on Hit@3 (paired per voter, stratified bootstrap over voters, 95% interval; `years better` = editions with a positive mean difference):

| Layer | Comparison | Mean difference | Editions better | 95% bootstrap CI | Exact p (4 editions) |
|---|---|---:|---:|---|---:|
| Jury | M0b − M0a | +0.0116 | 2/4 | [−0.025, 0.048] | 0.500 |
| Jury | M1 − M0b | −0.0113 | 1/4 | [−0.036, 0.014] | 0.500 |
| Jury | M2 − M1 | −0.0045 | 1/4 | [−0.021, 0.011] | 1.000 |
| Jury | M2 − M0b | −0.0158 | 1/4 | [−0.043, 0.012] | 0.500 |
| Public | M0b − M0a | **+0.2171** | 4/4 | **[0.173, 0.263]** | 0.125 |
| Public | M1 − M0b | +0.0003 | 2/4 | [−0.018, 0.021] | 1.000 |
| Public | M2 − M1 | +0.0023 | 1/4 | [−0.016, 0.021] | 1.000 |
| Public | M2 − M0b | +0.0025 | 3/4 | [−0.018, 0.023] | 1.000 |

NDCG@3 and MRR give the same picture: the only difference that survives is the public M0b − M0a lift (+0.225 NDCG, +0.218 MRR); every M1 − M0b, M2 − M1 and M2 − M0b difference is within about ±0.02 on all three metrics, with signs that change from one metric to another.

Mean standardised coefficients over the four folds (M2, the full model):

| Feature | Jury | Public |
|---|---:|---:|
| `pop` | +0.01 | −0.05 |
| `tie` | +0.07 | −0.00 |
| `tie_points` | +0.24 | +0.67 |
| `recip` | +0.03 | +0.09 |
| `same_region` | +0.12 | +0.17 |
| `shared_language` | +0.08 | +0.10 |
| `same_community` | +0.02 | +0.21 |
| `cohesion` | +0.06 | +0.03 |

1. **Every model beats random voting clearly, but the gap is layer-specific.** Hit@3 is about twice the random baseline for juries (0.23–0.25 against 0.12) and 3.5 times for the public with the history features (0.43 against 0.12). The televote is markedly more predictable than the jury from history alone, consistent with its higher temporal stability in RQ4.

2. **Direct history is the decisive feature for the public, not for juries.** For the public, M0b improves Hit@3 by +0.217 over popularity alone, in all four editions, and the bootstrap interval excludes zero. For juries the same step is small and uncertain (+0.012, 2/4 editions, interval around zero): the jury vote is much less persistent at the dyad level (RQ4), so its history adds little to popularity.

3. **Geography and language add nothing to the ranking beyond the dyadic history.** M1 − M0b is −0.011 for juries and +0.000 for the public, with intervals around zero and no consistent sign. The coefficients of `same_region` and `shared_language` are positive (about +0.1 to +0.2 standardised): a neighbour or a country sharing a language is somewhat more likely to get 8+ points, but the effect is too small to change which three recipients come first once the history of the pair is known.

4. **The SNA communities add no predictive value.** The key test of the proposal, M2 − M1, is −0.005 for juries and +0.002 for the public, with intervals that include zero and no consistent sign across editions; M2 − M0b is equally flat. The community terms are small for juries (+0.02, +0.06) and moderate only for `same_community` in the public (+0.21), next to `same_region` (+0.17): the Louvain partitions are coarse — three or four communities, modularity 0.09–0.15 — and broadly geographical, so they mostly repeat what geography and the history of the pair already say.

5. **Reading the coefficients.** The history block is collinear: `tie` (rate of 8+ votes i→j) and `tie_points` (mean points i→j) measure almost the same thing, and the regression puts the weight on `tie_points`, so `tie` is close to zero. The block should be read together, not feature by feature; the comparison between nested models, not the single coefficient, is the evidence.

6. **The result is a negative result, and it is informative.** The communities found in the voting networks describe their geography, but they do not generalise into an out-of-sample advantage for the top-3 recipients. As the proposal anticipated, the correct conclusion is that in these data the SNA communities offer no robust predictive gain, not that a group bonus should be forced. Reporting this is preferable to tuning a bonus until one of the four test editions improves.

*Correction (2026-11-24).* A first version computed the features of the training rows on all the training editions, including the edition of the row itself, so that each training row contained its own target. The test evaluation was not affected, but the coefficients of the history features were inflated (`tie` about +1.4 for juries and +1.7 for the public) and the out-of-sample accuracy was lower (Hit@3 of M0b 0.219 / 0.393 instead of 0.246 / 0.427). With features from the past only, the conclusions are the same — history decisive for the public, no gain from geography, language or communities — but the numbers and the reading of the coefficients above replace the earlier ones.

## Connection with RQ2–RQ4

RQ2 finds geographic homophily and communities that match geography (though their modularity is not above a weight-shuffling null), RQ3 finds a home excess in the votes and RQ4 finds that the public layer is more stable than the jury. RQ5 asks whether those descriptive facts translate into prediction. The answer is selective: the dyadic persistence found in RQ4 does translate, and strongly so for the public; the group structure found in RQ2 does not, because it is largely captured by geography, language and the dyadic history that M1 and M0b already contain. This is the distinction between a structure that exists and a structure that is useful out of sample.

## Limitations

- **Four test editions.** The exact test over editions has a floor of p = 0.125 and cannot reject at 0.05; the bootstrap over voters gives a usable interval but still summarises four years. The bootstrap resamples voters inside each edition separately, so it does not model the dependence of the same voter across editions; the per-edition table is reported for that reason and is part of the result, not an appendix.
- **No inner hyperparameter search.** L2 and the smoothing constant are fixed ex ante, as the proposal allows, so the coefficients are not tuned on the test years. A nested temporal validation could change the level of the results, but not the comparison between nested models, which is the object of the analysis.
- **Different history length in training and test.** Training rows have 2 to 8 editions of history, the test edition 6 to 9. The smoothing keeps short histories close to the base rate, but the training rows of the earliest editions are noisier than the test rows.
- **Top-3 only.** The order 12/10/8 and the point magnitudes are not modelled; Hit@3 gives the same credit to a correct set in any order, and NDCG@3 and MRR are only secondary.
- **Eligibility and voters change across editions.** The ranking set is the eligible recipients of that edition, and a country that enters or leaves the final has no training history. The smoothing keeps its features at the base rate, but it cannot give it a real history.
- **Communities are unstable and coarse.** A single Louvain run depends on the seed (RQ2), so the fold uses the best of ten seeds by modularity. This is still one partition, not the 200-run consensus used in RQ2; a consensus partition per fold would be more faithful to RQ2, but with M2 − M1 so close to zero it is unlikely to change the conclusion. The instability itself limits what a community feature can predict, and the low modularity of the aggregate networks (0.09–0.15) is part of the explanation of the null result.
- **Static, coarse attributes.** Region and language describe countries, not songs or performers, and the language coding is the most fragile construct of the project (see RQ2). No song-level covariate is used.
- **Predictive, not causal.** A positive coefficient for `tie` means that past high votes predict future high votes; it does not identify a causal effect of the pair, and the analysis makes no causal claim.

## Outputs

| File | Content |
|---|---|
| `results/rq5/rq5_predictions_by_year.csv` | Hit@3, NDCG@3, MRR, voters and random baseline for each edition, layer and model |
| `results/rq5/rq5_model_comparison.csv` | Paired model differences, editions better, exact p, bootstrap interval |
| `results/rq5/rq5_coefficients.csv` | Fitted standardised coefficients for each fold, layer, model and feature |
| `results/rq5/rq5_fold_diagnostics.csv` | Training editions, editions that give training rows, dyads, positives, p0, communities, modularity, voters |
| `figures/rq5/rq5_hit3_by_model.png` | Hit@3 by model (mean and range) and the lift of each block of features |

## Reproduction

From the `RQ5` directory:

```bash
python src/analyze_rq5_prediction.py
```

The script reads only the matrices in `../RQ1/processed_data/matrices/` and the attribute table in `../RQ2/processed_data/tables/`, so no external download is needed. It runs in about seven seconds. The Louvain seeds are 0–9 and the bootstrap seed is 42; two consecutive runs produce byte-identical CSV files and figure. The Python dependencies are NumPy, NetworkX and Matplotlib, the same as the other research questions.
