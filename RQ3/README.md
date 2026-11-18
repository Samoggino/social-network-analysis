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
- The prestige–participation correlation is about 0.25, not 0: a finalist that gets more points also gets them from more voters, and therefore from more groups.

Observed values are always compared with the null, not with 0 or 1.

**Jury vs public:** exact paired sign-flip test over the ten editions (2¹⁰ configurations), with Holm and Benjamini–Hochberg corrections over the 12 network-level statistics.

**Sensitivity to countries with few points:** the regional home excess, participation ratio and prestige–participation correlation are recomputed excluding finalists voted by fewer than 5 countries (34 of 257 finalist entries for juries, 69 of 257 for the public). The same rule is applied in the null model.

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

6. **Prestige measures agree.** PageRank and HITS authority rank finalists almost like in-strength (Spearman 0.94 and 0.99). On these dense, complete-ballot networks, the recursive measures add little beyond the points received.

## Limitations

- **Exploratory results.** The editions are not independent samples, and the statistics were chosen without a pre-registered plan.
- **The uniform null model does not preserve popularity.** The concentration test therefore only says that voting is not random; it does not separate quality from bloc voting. In the null no finalist is really popular, so the mechanical part of the prestige–participation correlation (0.25) is probably underestimated. A popularity-preserving null (the RQ1 edge-swap model) is still to do. The jury–public comparison does not have this problem.
- **Circularity of the communities.** The RQ2 communities come from the same votes, so the community home excess and participation ratio are inflated by construction, and their null test is not an independent test. They are used for the jury/public comparison and to check the results obtained with fixed groups.
- **Country-level noise.** A country that gets few points has noisy bridging measures. A finalist whose points all come from one group, often a single voter, gets participation 0 (the points at the bottom of the prestige–participation figure). This is the mechanical part of the prestige–participation relation that the null model measures (about 0.25); the ≥ 5 voters sensitivity check shows that the results do not depend on these cases. Country-level values in `rq3_country_aggregate.csv` should be read together with `finals` and the points received.
- **Overlap with RQ2.** The home excess overlaps with the same-region share of RQ2, seen from the side of the recipient instead of the voter. The report should present it as the recipient-side view, not as a separate result.

## Outputs

`results/rq3/`:

- `rq3_country_year.csv`: every country, edition and layer, with all prestige and bridging measures, its RQ2 community and firmness;
- `rq3_network_summary.csv`: network-level statistics and rank correlations;
- `rq3_null_model.csv`: observed value, null mean, 95% range and Monte Carlo p-values;
- `rq3_layer_differences.csv`: jury vs public tests;
- `rq3_country_aggregate.csv`: means over the editions in which a country was a finalist.

`figures/rq3/`: `rq3_concentration.png`, `rq3_jury_vs_public_prestige.png`, `rq3_home_bias.png`, `rq3_prestige_vs_participation.png`.

## Reproducing

Requirements: Python with `numpy`, `networkx`, `matplotlib` (no scipy needed).

```bash
cd RQ3
python src/analyze_rq3.py                     # about one minute, byte-identical across runs
python src/analyze_rq3.py --simulations 5000  # more null samples
```

Options: `--matrices DIR`, `--attributes CSV`, `--communities CSV`, `--simulations N` (default 2000), `--seed` (default 2026).
