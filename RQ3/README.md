# RQ3 — Prestige and Bridging

**Research question.** Which countries receive consensus (prestige), how concentrated is that consensus, and does it come from the country's own geographic, cultural or voting group or from across Europe? How do the answers differ between juries and televoting?

## Data and conventions

- 20 networks: Grand Finals 2016–2026 (2020 cancelled), jury and public layers kept separate, WLD excluded.
- Input matrices: `../RQ1/processed_data/matrices/` (identical to the RQ2 copy and to `scripts/build_graph.py --matrices`). `W[i, j]` = points from voter *i* to finalist *j*; an empty cell is an impossible vote.
- Groups:
  - `region` (UN M49 subregion) and `eurovision_block` (cultural block), from `../RQ2/processed_data/tables/country_attributes_rq2.csv`. The language coding is not used.
  - `community`: the RQ2 consensus partition of each full network, from `../RQ2/results/rq2/rq2_consensus_labels.csv`. It combines 200 Louvain runs by average linkage, so it does not depend on a single seed. The file also gives each country's *firmness*: its mean co-assignment with the other members of its community across the runs.
- The script only reads files outside `RQ3/`. If the RQ2 consensus is rerun, RQ3 must be rerun too.

## Measures

**Prestige of each finalist** (course measures):

- in-degree and in-strength;
- *points per opportunity* = in-strength / number of voters that could vote for it, which makes editions and layers comparable;
- PageRank (α = 0.85, weighted) and HITS authority. Each voter also gets a hub score: how much it votes for the finalists that receive consensus.
- Betweenness on the finalists-only network, with distance = 1/points. It is exploratory: the networks are dense and every voter has exactly ten outgoing edges.

**Concentration of prestige among finalists:** Gini of in-strength, share of points taken by the top three, Herfindahl index.

**Bridging**, for every finalist and for each kind of group:

- *home excess* = share of its points that come from its own group − share of its eligible voters in that group. 0 means support that ignores groups; > 0 means support concentrated in its own group.
- *participation ratio* = participation coefficient of the incoming points, 1 − Σ_g (points from g / points)², divided by the same quantity computed on eligible voters. Lower values mean support from fewer groups.
- *firmness* of the RQ2 community membership. A country with low firmness is often placed in different communities by different Louvain runs: it sits between communities.

**Prestige and bridging together**, per network: Spearman correlation between points per opportunity and participation ratio. Do the most voted finalists draw on more groups?

**Null model.** Uniform random ballots that follow the rules: every voter gives 1–8, 10 and 12 to ten random eligible finalists. There are 2000 samples per network.

- The home excess is 0 under this model.
- The participation ratio is about 0.93 rather than 1, because ten ballots of points are a finite sample.
- The prestige–participation correlation is about 0.25, not 0: under uniform ballots the in-degree varies by chance, and a finalist drawn with more voters also draws them from more groups. Section 8 shows that this is an artefact of the uniform null, not a property of popularity.

Observed values are always compared with the null, not with 0 or 1.

**Jury vs public:** exact paired sign-flip test over the ten editions (2¹⁰ configurations), with Holm and Benjamini–Hochberg corrections over the 12 network-level statistics.

**Sensitivity to countries with few points:** the regional home excess, participation ratio and prestige–participation correlation are recomputed excluding finalists voted by fewer than 5 countries (34 of 257 finalist entries for juries, 69 of 257 for the public). The same rule is applied in the null model.

**Popularity-preserving null** (`src/analyze_rq3_popularity_null.py`). The uniform null erases popularity as well as grouping: in it no country is really popular. The second null keeps, for every finalist, the number of voters that gave it points and the multiset of points it received, and redraws only *which* eligible voters gave them. In-degree and in-strength are therefore identical to the observed network, and the concentration measures are unchanged by construction, so this null tests the bridging measures only. Three statistics are tested per network and per grouping: mean home excess, mean participation ratio, and the Spearman correlation between prestige and participation. 1000 replicates per network.

**Entropy.** Normalised Shannon entropy of the share of points received, named by the official RQ3 specification next to Gini and PageRank, with the same uniform-ballot null.

**Ranking** (`src/analyze_rq3_ranking.py`). Points per opportunity is averaged over the editions in which a country was a finalist, and the rank is written with an explicit flag for countries that reached at least four finals, because a country with one final can top the list on a few votes.

## Results

Means over the ten editions:

| Statistic | Jury | Public | Random ballots | Public > Jury | p exact | Holm |
|---|---:|---:|---:|---:|---:|---:|
| Gini of points received | 0.447 | 0.538 | 0.137 | 10/10 | 0.002 | 0.023 |
| Share of points to the top three | 0.315 | 0.372 | 0.166 | 10/10 | 0.002 | 0.023 |
| Home excess, subregion | 0.083 | 0.193 | 0 | 9/10 | 0.004 | 0.023 |
| Home excess, cultural block | 0.076 | 0.152 | 0 | 10/10 | 0.002 | 0.023 |
| Home excess, RQ2 community | 0.235 | 0.307 | 0 | 9/10 | 0.004 | 0.023 |
| Participation ratio, subregion | 0.835 | 0.727 | 0.934 | 0/10 | 0.002 | 0.023 |
| Participation ratio, cultural block | 0.849 | 0.763 | 0.934 | 0/10 | 0.002 | 0.023 |
| Participation ratio, RQ2 community | 0.788 | 0.656 | 0.934 | 0/10 | 0.002 | 0.023 |
| Spearman prestige–participation, subregion | 0.717 | 0.815 | 0.25 | 8/10 | 0.041 | 0.041 |
| Home excess, subregion, ≥ 5 voters | 0.078 | 0.158 | 0 | 8/10 | 0.008 | 0.023 |
| Spearman prestige–participation, subregion, ≥ 5 voters | 0.635 | 0.772 | 0.25 | 9/10 | 0.014 | 0.027 |

1. **Prestige is far more concentrated than random voting**, in every network. Televoting is more concentrated than juries in every edition: the public converges on fewer winners.

2. **Juries and public reward different countries.** The Spearman correlation between jury and public in-strength within the same final is only 0.40 on average (minimum 0.21).
   - Countries much stronger with the public: UA, RO, RU, MD (+2.6 to +3.3 points per opportunity).
   - Countries much stronger with juries: MT, AU, CH, SE (−1.6 to −2.6).
   - See `figures/rq3/rq3_jury_vs_public_prestige.png`.

3. **Public support depends more on the country's own group**, whichever grouping is used. Against the null, the home excess on subregions is significant in all 10 public networks and in 8/10 jury networks. The participation ratio is lower for the public on all three groupings.
   - The same holds for the RQ2 communities. The community home excess is larger than the regional one, but that is expected, because the communities are built from the same votes (see the limitations). The useful result is the jury/public comparison, which agrees with the fixed groups.

4. **The most voted finalists draw support from across Europe.** The correlation between prestige and participation is positive in every network: 0.72 for juries and 0.82 for the public, against 0.25 under random ballots. It is above the null's 97.5% quantile in 9/10 jury and 10/10 public networks. The result holds with blocks (0.88 / 0.87) and with RQ2 communities (0.62 / 0.74).
   - Bloc support is therefore typical of mid- and low-ranking countries, while top countries receive points from every group (`figures/rq3/rq3_prestige_vs_participation.png`).
   - The relation is stronger for the public (8/10 editions, Holm 0.041). In televoting, a country that is not a favourite gets its points mainly from its neighbours.
   - It is not driven by countries with one or two voters. Excluding finalists voted by fewer than 5 countries, the correlation drops only slightly (0.64 / 0.77) and stays above the null's 97.5% quantile in 9/10 networks for each layer. The public home excess also stays more than twice the jury's (0.16 vs 0.08).

5. **Countries "between communities" are not bridges in the voting sense.** The firmness of a country's RQ2 membership is not correlated with the spread of its incoming points (mean Spearman +0.06 for juries, −0.05 for the public, with mixed signs).
   - A country that the Louvain runs move between communities is not one that draws points from several groups.
   - The least firm memberships among regular finalists are HU, MD, LV, SI and CZ for juries, and MT, ES, AT and CZ for the public.

6. **Prestige measures agree.** PageRank and HITS authority rank finalists almost like in-strength (Spearman 0.94 and 0.99). On these dense, complete-ballot networks, the recursive measures add little beyond the points received. Betweenness survives a little more: its correlation with in-strength is 0.78, so it re-ranks the middle of the table without changing the picture, and it is not used further. The hub score of voters is moderately related to the mean strength of the countries they chose (0.69), which means it measures a taste for consensus finalists and not simply the size of the countries voted for; with ten choices out of roughly twenty-five finalists the question does not require it, and it stays in `rq3_country_year.csv` as a diagnostic.

7. **The home excess and the prestige–participation correlation survive a popularity-preserving null.** The uniform null of the section above assumes that no finalist is popular, so part of the observed bridging could be explained by who collects points rather than by where the points come from. Holding in-degree and in-strength fixed per finalist:

| Mean over the editions, subregion | Jury | Public |
|---|---:|---:|
| Home excess, observed | 0.083 | 0.193 |
| Home excess under the null | 0.000 | 0.000 |
| z-score | 2.87 | 5.89 |
| Networks with p < 0.05 | 8/10 | 10/10 |
| Participation ratio, observed | 0.835 | 0.727 |
| Participation ratio under the null | 0.865 | 0.814 |
| z-score | −1.69 | −4.20 |
| Networks with p < 0.05 | 5/10 | 8/10 |

   The home excess is therefore not a popularity effect: it is support that comes from a finalist's own group more often than the same finalists' popularity would explain. On the fixed cultural block the pattern is stronger (0.076 and 0.152, 9/10 and 10/10 networks). The participation ratio is the measure that suffers most from fixing popularity, as expected, since it is built on the same counts: the jury evidence becomes weak (5/10) while the public evidence remains clear (8/10).

8. **The prestige–participation correlation is not mechanical.** Under the popularity-preserving null the correlation between points per opportunity and participation ratio is **0.006 for juries and −0.05 for the public**, not the 0.25 that uniform ballots produce:

| | Jury | Public |
|---|---:|---:|
| Observed | 0.717 | 0.815 |
| Under uniform ballots | ≈ 0.25 | ≈ 0.25 |
| Under the popularity-preserving null | 0.006 | −0.05 |
| z-score against the second null | 5.81 | 8.62 |
| Networks with p < 0.05 | 9/10 | 10/10 |

   The 0.25 of the uniform null is an artefact of drawing ballots at random, where in-degree varies by chance; once the observed in-degrees are fixed, a random assignment of voters produces no correlation at all. The positive correlation is therefore bloc support: the countries that are not favourites get their points from fewer groups, and that is a real feature of the votes, not a sample-size effect. The result also holds on the cultural block (0.875 / 0.874) and, more weakly, on the RQ2 communities (0.622 / 0.736).

9. **Tevoting is more homophilic than juries even after controlling for popularity.** The paired comparison on the z-scores of the second null, with the community rows kept for completeness although they are circular:

| Statistic (z against the popularity-preserving null) | Public − Jury | Exact p | Holm |
|---|---:|---:|---:|
| Home excess, subregion | +3.02 | 0.0039 | 0.039 |
| Home excess, block | +2.57 | 0.0020 | 0.023 |
| Participation ratio, subregion | −2.52 | 0.0156 | 0.094 |
| Prestige–participation, subregion | +2.81 | 0.0176 | 0.094 |
| Home excess, subregion, ≥ 5 voters | +3.06 | 0.0059 | 0.047 |
| Participation ratio, subregion, ≥ 5 voters | −3.71 | 0.0020 | 0.023 |
| Home excess, RQ2 community | +0.88 | 0.168 | 0.336 |

   The layer difference in home excess is confirmed under both nulls. The participation ratio and the prestige–participation correlation keep the same sign but do not survive Holm over the twelve comparisons, and the community rows lose significance entirely — which is what the circularity warning predicts, and a further reason to compare layers on the fixed groups.

10. **Entropy says the same thing as the Gini.** Normalised entropy of the points received is 0.900 for juries and 0.860 for the public, against 0.990 under uniform ballots (10/10 networks significant in both layers). It is a monotone function of the Herfindahl index already reported, so it is conceptually redundant and is included only because the official specification names it.

11. **The two layers do not rank the same countries.** Averaged over the finals in which a country competed, and restricted to the 33 countries with at least four finals:

| Rank | Jury | Public |
|---:|---|---|
| 1 | CH 5.10 | UA 5.75 |
| 2 | SE 4.56 | BG 4.76 |
| 3 | BG 4.39 | IT 4.41 |
| 4 | AU 4.22 | IL 4.11 |
| 5 | IT 3.94 | MD 4.02 |

   The rank correlation between the two layers is only 0.27 on this set (0.31 on all finalists), so the disagreement is not a matter of a few places. Without the minimum-finals rule the jury list is headed by MK on a single final (6.18) and the public list by RU on three (5.85): both are in `rq3_country_ranking.csv` with the `stable` flag set to 0, and neither should be quoted. AU (4th for juries, 20th for the public) and MT (8th for juries, 33rd for the public) are the largest disagreements; BG and IT are the only countries in the top five of both lists, while UA and IL are top five with the public and just outside with the juries.


## Limitations

- **Exploratory results.** The editions are not independent samples, and the statistics were chosen without a pre-registered plan.
- **The uniform null model does not preserve popularity.** The concentration test therefore only says that voting is not random; it does not separate quality from bloc voting. The bridging measures are re-tested against the popularity-preserving null of section 7, which fixes in-degree and in-strength per finalist; concentration cannot be tested that way, because fixing the points received fixes the Gini by construction.
- **The popularity-preserving null is not a full network rewiring.** It fixes the opportunity structure of each *recipient* and redraws the identity of its voters, which is what the bridging measures need. It does not preserve the degrees of the voters, so it is not the RQ1 edge-swap model and the two are not interchangeable.
- **The WLD is excluded.** From 2023 the real public score is half Rest of the World and half national televote; excluding the WLD leaves the national half. Public concentration and home excess are therefore measured on the part of the public vote that is attached to countries, and the public layer is the one where this matters.
- **Circularity of the communities.** The RQ2 communities come from the same votes, so the community home excess and participation ratio are inflated by construction, and their null test is not an independent test. They are used for the jury/public comparison and to check the results obtained with fixed groups.
- **Country-level noise.** A country that gets few points has noisy bridging measures. A finalist whose points all come from one group, often a single voter, gets participation 0 (the points at the bottom of the prestige–participation figure). This is the mechanical part of the prestige–participation relation that the null model measures (about 0.25); the ≥ 5 voters sensitivity check shows that the results do not depend on these cases. Country-level values in `rq3_country_aggregate.csv` should be read together with `finals` and the points received.
- **Overlap with RQ2.** The home excess overlaps with the same-region share of RQ2, seen from the side of the recipient instead of the voter. The report should present it as the recipient-side view, not as a separate result.

## Outputs

`results/rq3/`:

- `rq3_country_year.csv`: every country, edition and layer, with all prestige and bridging measures, its RQ2 community and firmness;
- `rq3_network_summary.csv`: network-level statistics and rank correlations;
- `rq3_null_model.csv`: observed value, null mean, 95% range and Monte Carlo p-values;
- `rq3_layer_differences.csv`: jury vs public tests;
- `rq3_country_aggregate.csv`: means over the editions in which a country was a finalist;
- `rq3_country_ranking.csv`: the same, ranked per layer, with the `stable` flag for countries with at least four finals;
- `rq3_ranking_agreement.csv`: rank correlation between the two layers;
- `rq3_popularity_null.csv`: observed value, popularity-preserving null and p-values for the three bridging statistics, per grouping;
- `rq3_popularity_null_layer_diff.csv`: jury vs public tests on the z-scores against that null;
- `rq3_entropy.csv`: normalised entropy of the points received against uniform ballots;
- `rq3_measure_redundancy.csv`: betweenness against in-strength and hub against recipient strength.

`figures/rq3/`: `rq3_concentration.png`, `rq3_jury_vs_public_prestige.png`, `rq3_home_bias.png`, `rq3_prestige_vs_participation.png`, `rq3_popularity_null.png`.

## Reproducing

Requirements: Python with `numpy`, `networkx`, `matplotlib` (no scipy needed).

```bash
cd RQ3
python src/analyze_rq3.py                     # about one minute
python src/analyze_rq3_popularity_null.py     # about twenty seconds
python src/analyze_rq3_ranking.py             # a few seconds
python src/analyze_rq3.py --simulations 5000  # more null samples
```

`analyze_rq3_ranking.py` reads `rq3_country_aggregate.csv`, so it must run after `analyze_rq3.py`; the popularity null reads the same inputs as `analyze_rq3.py` and is independent of it. The two additions round their CSV output to ten decimals and are byte-identical across runs. `analyze_rq3.py` does not round, so rerunning it still changes the last digits of `rq3_country_year.csv` and `rq3_country_aggregate.csv` because of the summation order: numerically stable, not byte-identical.

Options: `--matrices DIR`, `--attributes CSV`, `--communities CSV`, `--simulations N` (default 2000), `--seed` (default 2026). The additions take `--null-samples` (default 1000) and `--ballots` (default 2000).
