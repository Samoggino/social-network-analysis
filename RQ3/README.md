# RQ3 — Prestige and Bridging

**Research question.** Which countries receive consensus (prestige), how concentrated is that consensus, and does it come from the country's own geographic, cultural or voting group or from across Europe? How do the answers differ between juries and televoting?

## Data and conventions

- The 20 networks cover the grand finals from 2016 to 2026, excluding 2020. Each edition has a jury and a national televote network. The Rest of the World ballot (`WLD`) is excluded.
- RQ3 reads the matrices in `../RQ2/processed_data/matrices/`. `W[i, j]` gives the points from voter *i* to finalist *j*. A blank cell marks an ineligible vote and a zero marks an eligible vote with no points awarded.
- Groups:
  - `region` (UN M49 subregion) and `eurovision_block` (cultural block), from `../RQ2/processed_data/tables/country_attributes_rq2.csv`. The language coding is not used.
  - `community`: the RQ2 consensus partition of each full network, from `../RQ2/results/rq2/rq2_consensus_labels.csv`. It combines 200 Louvain runs by average linkage, so it does not depend on a single seed. The file also gives each country's *firmness*: its mean co-assignment with the other members of its community across the runs.
The three scripts use the revised RQ2 as their input. The consensus reader also accepts the older column names for explicit input overrides.

## Measures

**Prestige of each finalist** (course measures):

- in-degree and in-strength;
- *points per opportunity* = in-strength / number of eligible voters, to account for differences in voting opportunities across editions and layers.
- Weighted PageRank (α = 0.85) and HITS authority. HITS also assigns a hub score to each voter.
- Betweenness on the finalists-only network, with distance equal to the reciprocal of the points awarded. It is exploratory given the density of the networks.

**Concentration of prestige among finalists.** The measures are the Gini coefficient of in-strength, the top-three share of points, the Herfindahl index (HHI), and Shannon entropy. Entropy is normalised by the logarithm of the total number of eligible finalists, including finalists who received zero points.

**Bridging** is measured for each finalist and grouping.

- *Home excess* is the share of points from the finalist’s own group minus the share of its eligible voters in that group. A positive value means the group supplied more than its share of voting opportunities.
- *Participation ratio* is the participation coefficient of incoming points, 1 − Σ_g (points from g / total points)², divided by the same coefficient for the distribution of eligible voters across groups. Lower values indicate that support is more concentrated across groups.
- *Firmness* is a separate RQ2 measure of how often a country is grouped with the other members of its consensus community across Louvain runs.

Home excess and participation ratio are undefined for finalists with zero points. There are 19 such entries across the dataset (5 jury and 14 televote). The bridging means and the network-level Spearman correlation between points per opportunity and participation ratio use the finalists with defined values. The regional sensitivity analysis requires at least five voters to have awarded points. In the observed data this excludes 34 of 257 jury finalist entries and 69 of 257 televote entries. The same threshold applies within each simulated network.

**Ranking** (`src/analyze_rq3_ranking.py`). Points per opportunity is averaged over the editions in which a country was a finalist, and the rank is written with an explicit flag for countries that reached at least four finals, because a country with one final can top the list on a few votes.

## Null models and statistical tests

**Uniform ballots (2,000 samples per network).** Each voter awards 1–8, 10 and 12 to ten distinct, randomly chosen eligible finalists. This preserves voting eligibility and the full score set of each ballot. The number of voters and the points received by a finalist vary by chance. This reference gives a mean regional home excess close to zero, a mean participation ratio of about 0.934 and a mean prestige–participation correlation of about 0.25. A finalist drawn by more voters tends to draw support from more groups even under uniform ballots.

**Recipient popularity fixed (1,000 samples per network).** For each finalist, the script independently reassigns its observed positive scores to a uniformly sampled set of distinct eligible voters. This preserves the recipient’s in-degree, in-strength and multiset of received scores. A voter’s number of outgoing votes, total points awarded and score set can vary because each recipient is sampled independently. Keeping the received totals fixed makes Gini, top-three share, HHI and entropy invariant. The model is used to test bridging statistics, including the correlation with prestige.

### Annual Monte Carlo tests

`rq3_null_model.csv`, `rq3_popularity_null.csv` and `rq3_entropy.csv` report nominal p-values for each edition and layer. `p_high` is the one-sided upper-tail probability and `p_low` is the one-sided lower-tail probability. `p_two_sided` counts draws whose absolute deviation from the simulated mean is at least as large as the observed deviation. Each p-value uses the Monte Carlo correction `(extreme draws + 1) / (finite draws + 1)`. With `B` finite draws, the smallest possible p-value is `1 / (B + 1)`. The CSVs apply no multiple-testing adjustment to these annual p-values. Counts at the 0.05 threshold below are descriptive and name the tail used.

### Paired comparisons between jury and televote

Both comparisons use a **two-sided exact paired sign-flip test**. The test takes the public-minus-jury difference within each edition and compares the magnitude of the mean difference with the magnitudes under all 1,024 sign patterns across the ten paired editions. `rq3_layer_differences.csv` tests the observed statistics. `rq3_popularity_null_layer_diff.csv` tests z-scores computed by subtracting each network’s popularity-preserving null mean and dividing by its null standard deviation.

`p_exact` is the unadjusted p-value. `p_holm` controls the family-wise error rate and `p_fdr` reports the Benjamini–Hochberg adjustment for the false discovery rate. The corrections are applied to the 12 statistics **within each CSV**. The results below use Holm-adjusted p-values for the paired comparisons. Inference depends on the sign-flip exchangeability assumption and is exploratory across these editions.

## Results

**Revision note.** Both revisions corrected the indexing of retained finalists. The integrated code uses the same retained countries for observed and simulated statistics, computes ranks across replicates, and normalises entropy over all eligible finalists.

The table reports means over the ten editions. The random-ballot column gives the uniform null mean averaged across editions and layers. The p-value columns refer to the paired test on the observed statistics.

| Statistic | Jury | Public | Random ballots | Public > Jury | p exact (two-sided) | p Holm |
|---|---:|---:|---:|---:|---:|---:|
| Gini of points received | 0.447 | 0.538 | 0.137 | 10/10 | 0.002 | 0.023 |
| Share of points to the top three | 0.315 | 0.372 | 0.166 | 10/10 | 0.002 | 0.023 |
| Herfindahl index | 0.067 | 0.082 | 0.041 | 10/10 | 0.002 | 0.023 |
| Home excess, subregion | 0.083 | 0.193 | 0 | 9/10 | 0.004 | 0.023 |
| Home excess, cultural block | 0.085 | 0.184 | 0 | 10/10 | 0.002 | 0.023 |
| Home excess, RQ2 community | 0.235 | 0.307 | 0 | 9/10 | 0.004 | 0.023 |
| Participation ratio, subregion | 0.835 | 0.727 | 0.934 | 0/10 | 0.002 | 0.023 |
| Participation ratio, cultural block | 0.846 | 0.750 | 0.934 | 0/10 | 0.002 | 0.023 |
| Participation ratio, RQ2 community | 0.788 | 0.656 | 0.934 | 0/10 | 0.002 | 0.023 |
| Spearman prestige–participation, subregion | 0.717 | 0.815 | 0.252 | 8/10 | 0.041 | 0.041 |
| Home excess, subregion, ≥ 5 voters | 0.078 | 0.158 | 0 | 8/10 | 0.008 | 0.023 |
| Spearman prestige–participation, subregion, ≥ 5 voters | 0.635 | 0.772 | 0.252 | 9/10 | 0.014 | 0.027 |

1. **Televoting is more concentrated in every edition.** Gini, the top-three share and HHI are higher for the televote in all ten editions. For each of these statistics, all 20 networks have a nominal upper-tail p-value below 0.05 against uniform ballots.

2. **Juries and public reward different countries.** The Spearman correlation between jury and public in-strength within the same final is only 0.40 on average (minimum 0.21).
   - Countries much stronger with the public: UA, RO, RU, MD (+2.6 to +3.3 points per opportunity).
   - Countries much stronger with juries: MT, AU, CH, SE (−1.6 to −2.6).
   - See `figures/rq3/rq3_jury_vs_public_prestige.png`.

3. **The televote has higher geographic home excess.** It is higher in nine of ten editions, with a mean gap of 0.110 (11.0 percentage points). Against the uniform-ballot null, the nominal two-sided p-value for regional home excess is below 0.05 in 8/10 jury networks and 10/10 televote networks. The observed mean participation ratio is lower in televoting for all three groupings. The results for RQ2 communities are descriptive because the groups were estimated from the same votes.

4. **Prestige and geographic participation are positively correlated in the observed data.** The Spearman coefficient is positive in every network. The televote coefficient is higher in 8 of ten editions, with a Holm-adjusted p-value of 0.041 in the paired test on observed coefficients. The scatterplot shows this descriptive pattern (`figures/rq3/rq3_prestige_vs_participation.png`). Mean correlations are also positive for cultural blocks (0.85 jury, 0.85 televote) and RQ2 communities (0.62 jury, 0.74 televote). Section 8 evaluates the geographic correlation against the corrected popularity-preserving reference.

5. **Community firmness and participation show little association on average.** Mean Spearman correlations are +0.07 for juries and −0.05 for the televote, with mixed signs across editions. Among countries with at least three finals, the memberships with the lowest mean firmness include HU, MD, LV, SI and CZ for juries, and MT, ES, AT and CZ for the televote.

6. **Prestige measures agree.** PageRank and HITS authority produce rankings close to in-strength, with mean Spearman coefficients of 0.937 and 0.995. Betweenness has a mean correlation of 0.78 with in-strength. Voter hub scores have a mean correlation of 0.69 with the mean in-strength of the ten finalists the voter scored. Both measures are exploratory diagnostics.

7. **Home excess relative to the popularity-preserving null.** The table shows the subregional statistics when each finalist’s in-degree and received scores are held fixed.

| Mean over the editions, subregion | Jury | Public |
|---|---:|---:|
| Home excess, observed | 0.083 | 0.193 |
| Home excess under the null | 0.000 | 0.000 |
| z-score | 2.87 | 5.89 |
| Home excess, nominal upper-tail p < 0.05 | 8/10 | 10/10 |
| Home excess, nominal two-sided p < 0.05 | 7/10 | 10/10 |
| Participation ratio, observed | 0.835 | 0.727 |
| Participation ratio under the null | 0.865 | 0.814 |
| z-score | −1.69 | −4.20 |
| Participation ratio, nominal lower-tail p < 0.05 | 5/10 | 8/10 |

The positive mean home excess in both layers exceeds the mean under this conditional reference. For the revised cultural blocks, observed home excess is 0.085 for juries and 0.184 for the televote, with nominal upper-tail p-values below 0.05 in 9/10 and 10/10 networks, respectively. These are comparisons with a model of who could have supplied the observed points.

8. **Prestige and cross-group participation at fixed popularity.** The original script used positions in the filtered finalist list to index the full country list. That misaligned prestige and simulated participation in all 20 networks. The corrected code maps each retained finalist to its original country index, including in the analysis restricted to finalists with at least five voters.

| Ten-year mean | Jury | Public |
|---|---:|---:|
| Observed prestige–participation Spearman | 0.717 | 0.815 |
| Uniform-ballot null (separate model) | approximately 0.25 | approximately 0.25 |
| Corrected popularity-preserving null | 0.753 | 0.836 |
| Mean z against corrected popularity null | -0.270 | -0.413 |

The observed means are below the corrected null means in both layers. Under that null, zero of ten annual upper-tail p-values fall below 0.05 in either layer. The observed association is compatible with this reference at fixed recipient popularity. For a finalist with N eligible voters, a positive group-diversity baseline and normalised score weights w, the expected participation ratio under this model is N/(N−1) × (1−Σ w²). Both finite voter coverage and concentration of received scores contribute to that benchmark. The paired comparison of the correlation z-scores gives **two-sided p exact = 0.8125 and p Holm = 1.0**. The five-voter sensitivity test on those z-scores gives p exact = 0.1582 and p Holm = 0.6328.

9. **Televoting shows higher home excess relative to the popularity-preserving reference.** These paired comparisons use the z-scores against that null.

| Statistic | Public minus jury z | p exact (two-sided) | p Holm |
|---|---:|---:|---:|
| Home excess, subregion | +3.02 | 0.0039 | 0.039 |
| Home excess, cultural block | +2.99 | 0.0020 | 0.0234 |
| Home excess, subregion, at least 5 voters | +3.06 | 0.0059 | 0.0410 |
| Participation ratio, subregion | -2.52 | 0.0156 | 0.094 |
| Participation ratio, subregion, at least 5 voters | -3.71 | 0.0020 | 0.023 |
| Prestige–participation, subregion | -0.143 | 0.8125 | 1.0 |
| Prestige–participation, cultural block | -1.487 | 0.0039 | 0.0391 |

The geographic and cultural home-excess comparisons have Holm-adjusted p-values below 0.05. For the revised cultural blocks, the prestige–participation correlation z-score is lower for the televote (means +0.467 for juries and −1.019 for the televote). This comparison uses each layer's own fixed-popularity reference. The subregional participation-ratio comparison meets that threshold in the five-voter subset (0.0234). The unrestricted subregional comparison has p Holm = 0.0938.

10. **Entropy gives another view of concentration.** Normalised Shannon entropy averages 0.895 for juries and 0.844 for the televote, against 0.990 under uniform ballots. The nominal two-sided Monte Carlo p-value is about 0.00050 in all 20 networks. Shannon entropy and the Herfindahl index can rank distributions differently.

11. **The two layers do not rank the same countries.** Averaged over the finals in which a country competed, and restricted to the 33 countries with at least four finals:

| Rank | Jury | Public |
|---:|---|---|
| 1 | CH 5.10 | UA 5.75 |
| 2 | SE 4.56 | BG 4.76 |
| 3 | BG 4.39 | IT 4.41 |
| 4 | AU 4.22 | IL 4.11 |
| 5 | IT 3.94 | MD 4.02 |

The rank correlation is 0.27 in this set and 0.31 across all finalists. With no minimum-finals threshold, MK leads the jury list on a single final (6.18) and RU leads the televote list on three (5.85). Both have `stable = 0`. Among the stable finalists, AU ranks 4th for the jury and 20th for the televote, and MT ranks 8th and 33rd. BG and IT are the only countries in both top fives.


## Limitations

- **Exploratory inference.** Annual editions share many countries and may be dependent. The statistics were selected without preregistration. Both null models address specific voting mechanisms and leave geographic causality undetermined. Song appeal, diaspora and language can contribute to the observed patterns.
- **Coverage of the televote.** From 2023 the Rest of the World contributes a single additional set of 58 points, with the weight of one participating country’s televote. Excluding `WLD` limits the public layer to national televote ballots. [Eurovision voting rules](https://www.eurovision.com/newsroom/rules-of-the-contest/)
- **Circularity of community comparisons.** The RQ2 consensus partitions were learned from the same networks and are held fixed during the simulations. Community home excess, participation and comparisons between layers are therefore descriptive. The fixed geographic and cultural group labels are specified independently of the RQ3 votes.
- **Low counts and missing statistics.** A finalist with all its points from one group has a participation ratio of zero, a common outcome with very few voters. The five-voter subset checks sensitivity to these cases. Country-level values in `rq3_country_aggregate.csv` should be read with the number of finals and the points received. With new inputs, verify that each test statistic is finite before interpreting its p-value.
- **Overlap with RQ2.** Home excess describes same-region support from the recipient’s perspective and accounts for its eligible voters. It complements the voter-side measures in RQ2.

## Outputs

`results/rq3/`:

- `rq3_country_year.csv`: every country, edition and layer, with all prestige and bridging measures, its RQ2 community and firmness;
- `rq3_network_summary.csv`: network-level statistics and rank correlations;
- `rq3_null_model.csv` reports the observed value, null mean, central 95% simulation range and nominal Monte Carlo p-values.
- `rq3_layer_differences.csv` reports paired two-sided tests on the observed statistics, with exact, Holm and Benjamini–Hochberg p-values.
- `rq3_country_aggregate.csv`: means over the editions in which a country was a finalist;
- `rq3_country_ranking.csv`: the same, ranked per layer, with the `stable` flag for countries with at least four finals;
- `rq3_ranking_agreement.csv`: rank correlation between the two layers;
- `rq3_popularity_null.csv` reports observed bridging statistics, popularity-preserving null summaries and nominal Monte Carlo p-values by grouping.
- `rq3_popularity_null_layer_diff.csv` reports paired two-sided tests on the popularity-preserving z-scores, with exact, Holm and Benjamini–Hochberg p-values.
- `rq3_entropy.csv` reports normalised entropy against uniform ballots with nominal Monte Carlo p-values.
- `rq3_measure_redundancy.csv`: betweenness against in-strength and hub against recipient strength.

`figures/rq3/`: `rq3_concentration.png`, `rq3_jury_vs_public_prestige.png`, `rq3_home_bias.png`, `rq3_prestige_vs_participation.png`, `rq3_popularity_null.png`.

## Explanation in Italian

See the [PDF report](Spiegazione_analisi_e_risultati.pdf) and its [Markdown source](Spiegazione_analisi_e_risultati.md).

## Reproducing

From the repository root, enter this copy and install its Python dependencies.

```bash
cd RQ3
python -m pip install -r requirements.txt
python src/analyze_rq3.py
python src/analyze_rq3_popularity_null.py
python src/analyze_rq3_ranking.py
```

The ranking script reads `rq3_country_aggregate.csv` produced by the first script. The popularity-null script reads the RQ2 inputs directly and also runs the entropy comparison. The scripts write to `results/rq3/` and `figures/rq3/` within this copy, overwriting the corresponding outputs. Run RQ2 first if its attributes or consensus have changed. Use the same inputs, options and Python dependency versions when comparing runs. The requirements file specifies minimum versions, so small numerical or rendering differences can occur across environments.

- `analyze_rq3.py` uses `--simulations 2000` and `--seed 2026` by default.
- `analyze_rq3_popularity_null.py` uses `--null-samples 1000` for fixed popularity, `--ballots 2000` for entropy and `--seed 2026` by default.
- Both analysis scripts accept input paths with `--matrices`, `--attributes` and `--communities`. The ranking script accepts `--matrices`, `--aggregate` and `--min-finals` (default 4).
