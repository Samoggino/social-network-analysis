# RQ2 — Voting Communities and Homophily

**Research question.** How do community structure and homophily differ between jury and
public voting? Do the communities detected by modularity optimisation coincide with
geographic and linguistic groups, and is the difference between the two voting levels
geographic or cultural?

This folder contains the analysis scripts, the prepared voting matrices, the numerical
results and the figures for RQ2. The pipeline is rebuilt from scratch: the original scripts
were exchanged as attachments and are not available, so every script here was written again
and validated against the numbers reported in the project conversation (see
[Validation](#validation-against-the-original-run)).

---

## 1. Data

The twenty annual networks are the same used for RQ1: ten editions (2016–2026, 2020
cancelled), each with a jury and a public network. Countries are nodes, an edge from *i* to
*j* means that *i* awarded points to *j*, and the weight is the number of points
(1–8, 10, 12).

| Cell | Meaning |
|---|---|
| `1`–`8`, `10`, `12` | points awarded (positive edge) |
| `0` | eligible vote, no points |
| empty | impossible vote (self-vote, or recipient not a finalist) |

`WLD`, the international public vote introduced in 2023, is excluded from the networks: it
is not a country and has no comparable attributes. It remains in the raw dataset only.

Every matrix is validated on write: 10 positive votes per voter, exactly the scores
1–8, 10, 12, 58 points in total.

The matrices in `processed_data/matrices/` are byte-identical to those in
`RQ1/processed_data/matrices/` apart from line endings; they are duplicated so that each
research question can be run independently.

### Country attributes

`processed_data/tables/country_attributes_rq2.csv` lists the 45 voting countries with:

- `region` — UN M49 subregion (Northern, Western, Southern, Eastern Europe; Western Asia;
  Northern Africa; Northern America; Australia and New Zealand).
- `language_groups` — one or more broad language families, separated by `;`, so that
  multilingual countries are not forced into a single label.
- `eurovision_block` — a cultural block used as a sensitivity check, independent of the UN
  classification.

---

## 2. Methods

### Stage 1 — Descriptive structure (`src/analyze_rq2.py`)

For each of the 20 networks, on the undirected sum-weighted projection:

- Louvain community detection (`resolution = 1.0`, `seed = 42`), number of communities and
  modularity;
- Newman assortativity by subregion;
- share of points awarded inside the voter's own subregion, computed both on the full
  network and on the sub-network of countries that reached the final.

### Stage 2 — Opportunity correction, margins and tests (`src/analyze_rq2_opportunity.py`)

A country cannot vote for itself and can only vote for finalists, so part of the observed
homophily is forced by the composition of the final. For each voter *v* the expected share
of same-subregion choices under random selection is `|R_v| / |E_v|`, where `E_v` are the
eligible finalists and `R_v` those in the same subregion. Averaging over voters gives an
analytic benchmark, with no simulation.

Two margins are separated:

- **extensive** — how often a same-subregion country enters the ten chosen ones;
- **intensive** — how many points it receives once chosen.

Homophily is then tested by permuting region and language labels across countries (1,000
permutations), which keeps the vote network and the size of every group and answers one
question: do votes follow the labels more than a random assignment of the same labels would?
Within each family of 20 tests, p-values are corrected with Holm and Benjamini–Hochberg.

Finally the two levels are compared with an exact paired sign-flip test over the ten years:
swapping jury and public within each edition exhausts all 2¹⁰ = 1,024 configurations.

### Stage 3 — Partitions and stability (`src/analyze_rq2_partitions.py`)

Agreement between the Louvain partition and (a) UN M49 subregions, (b) primary language
family, (c) Eurovision cultural block, measured with NMI and ARI. NMI is not corrected for
chance, ARI is, so both are reported: with 4–5 groups the expected NMI under permutation is
about 0.13–0.25, not zero. A permutation benchmark (500 draws) quantifies that baseline.

Stability is measured by rerunning Louvain over 100 seeds at three resolutions and computing
the mean pairwise ARI between runs, together with the co-assignment matrix.

---

## 3. Reproducing the analysis

Requirements: Python with `numpy`, `networkx`, `matplotlib`.

```bash
cd RQ2

# only if the matrices have to be rebuilt from the raw EurovisionAPI export
python src/build_eurovision_data.py path/to/dataset-main/data/senior
python src/make_country_attributes.py

python src/analyze_rq2.py
python src/analyze_rq2_opportunity.py
python src/analyze_rq2_partitions.py     # about one minute
```

Results are written to `results/rq2/`, figures to `figures/rq2/`.

---

## 4. Validation against the original run

The structural counts of the rebuilt matrices match the original validation table exactly.

| Year | Finalists | Voters | Non-finalists |
|---|---:|---:|---:|
| 2016 | 26 | 42 | 16 |
| 2017 | 26 | 42 | 16 |
| 2018 | 26 | 43 | 17 |
| 2019 | 26 | 41 | 15 |
| 2021 | 26 | 39 | 13 |
| 2022 | 25 | 40 | 15 |
| 2023 | 26 | 37 | 11 |
| 2024 | 25 | 37 | 12 |
| 2025 | 26 | 37 | 11 |
| 2026 | 25 | 35 | 10 |

Totals: **45** voting countries, **43** that reached at least one final, BA and ME voters
only, **393** voter-editions, **7,860** positive votes.

Mean values over 2016–2026, rebuilt vs reported:

| Metric | Jury | Reported | Public | Reported | Outcome |
|---|---:|---:|---:|---:|---|
| Geographic assortativity | 0.022 | 0.022 | 0.057 | 0.057 | exact |
| Share of points inside the subregion | 0.233 | 0.233 | 0.295 | 0.295 | exact |
| Same, finalists only | 0.214 | 0.214 | 0.278 | 0.278 | exact |
| Modularity | 0.154 | 0.158 | 0.160 | 0.165 | within seed noise |
| Number of communities | 4.2 | 4.0 | 3.5 | 3.6 | within seed noise |
| Share of points to a shared language | 0.263 | 0.289 | 0.272 | 0.305 | see below |

The 2016 edition, used as a preview in the original run, is reproduced to the decimal:
**18.6%** of jury points and **27.4%** of public points go to the voter's own subregion.
The Balkan community described for the 2016 public network (Bosnia and Herzegovina,
Croatia, Montenegro, North Macedonia, Serbia, Slovenia) is also recovered identically.

### Two discrepancies, and why

**Number of communities and modularity.** Louvain depends on the random seed and on node
order. The original seed cannot be recovered, so 4.2 vs 4.0 communities and 0.154 vs 0.158
modularity are expected differences, not errors. Every deterministic metric — assortativity
and point shares — matches to the third decimal.

**The language share is a real discrepancy.** With a defensible language coding (Albanian,
Armenian, Turkic, Greek, Kartvelian and Semitic as distinct families) the result is
**26.3% jury / 27.2% public**, not 28.9% / 30.5%. The reported values are reproduced
(28.8% / 30.6%) only by grouping Albania, Armenia, Azerbaijan, Cyprus, Georgia, Greece and
Israel under a single `Other` label, which would put Georgian and Hebrew in the same
language family. The original conclusion ("language has a weaker effect than geography")
survives, but stage 2 makes it sharper: on language there is no difference between the two
levels at all.

---

## 5. Results

### 5.1 Opportunity structure and the two margins

Averaged over the ten editions:

| | Jury | Public |
|---|---:|---:|
| Expected by random choice | 18.7% | 18.7% |
| Choices inside the same subregion | 21.9% | **25.1%** |
| Excess ratio (choices) | 1.18 | **1.34** |
| Points to the same subregion | 23.3% | **29.5%** |
| Excess ratio (points) | 1.25 | **1.59** |
| Mean points if chosen, same subregion | 6.16 | **6.86** |
| Mean points if chosen, other subregions | 5.70 | 5.46 |
| Intensive margin | +0.47 | **+1.40** |

Three readings:

1. **Geographic homophily exists at both levels.** It is not an artefact of the opportunity
   structure: jury and public both sit above the 18.7% benchmark.
2. **Public voting is more homophilic on all three margins**, not only on the point share.
3. **The intensive margin is the new result.** In public voting a same-subregion country is
   not only chosen more often, it also receives **1.4 more points** once chosen; for juries
   the advantage is 0.5 points. This is consistent with the RQ1 finding on 10- and 12-point
   exchanges: public voting concentrates high scores, and part of that concentration is
   geographic.

Homophily tests, number of networks significant after Benjamini–Hochberg correction:

| Family | Significant |
|---|---:|
| Region, point share | 17/20 |
| Region, choice share | 14/20 |
| Language, point share | 14/20 |
| Language, choice share | 7/20 |

Homophily is therefore real for language as well, but weaker and less systematic.

### 5.2 Paired comparison between the levels

| Metric | Public − Jury | Exact p | Holm |
|---|---:|---:|---:|
| Choices inside the same subregion | +3.2 pp | 0.0020 | 0.012 |
| Points to the same subregion | +6.2 pp | 0.0020 | 0.012 |
| Intensive margin, region | +0.93 points | 0.0098 | 0.039 |
| Choices with a shared language | +0.45 pp | 0.744 | 1.000 |
| Points to a shared language | +0.93 pp | 0.660 | 1.000 |
| Intensive margin, language | +0.11 points | 0.701 | 1.000 |

All three geographic metrics survive Holm correction; none of the language metrics comes
close.

### 5.3 Do the communities match geography?

Means over 2016–2026 on the full network, with the permutation benchmark:

| | Jury | Public |
|---|---:|---:|
| NMI with subregions | 0.273 | **0.432** |
| *permutation benchmark* | *0.157* | *0.131* |
| ARI with subregions | 0.091 | **0.280** |
| NMI with language families | 0.342 | 0.378 |
| *permutation benchmark* | *0.254* | *0.221* |
| ARI with language families | 0.083 | 0.141 |
| NMI with cultural blocks | 0.320 | 0.423 |
| *permutation benchmark* | *0.228* | *0.191* |

NMI and ARI must be read together. With 4–5 groups the permutation baseline of NMI is
0.13–0.25, so NMI alone would make even random partitions look geographic. ARI has zero
expected value under permutation, and it is what settles the question: **the jury partition
has almost no agreement with geography (ARI 0.09), while the public partition is three times
higher (0.28)**. For language both levels sit barely above chance.

Paired comparison of the agreement scores:

| Metric | Public − Jury | Exact p | Holm |
|---|---:|---:|---:|
| NMI subregions | +0.159 | 0.0059 | 0.041 |
| ARI subregions | +0.189 | 0.0039 | 0.031 |
| NMI cultural blocks | +0.103 | 0.0020 | 0.023 |
| ARI cultural blocks | +0.105 | 0.0020 | 0.023 |
| NMI language families | +0.036 | 0.234 | 0.234 |
| ARI language families | +0.058 | 0.096 | 0.191 |

Geography and cultural blocks survive correction, language does not. The cultural blocks
behave like the UN subregions, which is reassuring: the result does not depend on the UN
classification.

### 5.4 Stability of the partitions

100 seeds per network, three resolutions, mean pairwise ARI over all pairs of partitions:

| Resolution | Jury | Public |
|---|---:|---:|
| 0.8 (≈ 2 communities) | 0.54 | 0.66 |
| 1.0 (≈ 4 communities) | 0.51 | **0.74** |
| 1.2 (≈ 6 communities) | 0.56 | 0.75 |

On the finalists-only sub-network the values rise (0.66 vs 0.78 at resolution 1.0) but the
ordering never changes.

Two consequences:

1. **With 26 nodes, a single Louvain run is not a result.** A mean ARI of 0.51 means that
   two seeds out of three produce different partitions. Communities must be presented with
   the co-assignment matrix rather than as a single coloured graph.
2. **The public partition is far more reproducible than the jury one**, and this is the same
   message as NMI and ARI, obtained independently. Public communities are both geographic
   and stable; jury communities are neither.

---

## 6. Conclusion

> The difference between public and jury voting is **entirely geographic**. Public
> communities coincide with subregions much more than jury communities (ARI 0.28 vs 0.09),
> they are far more stable across seeds (0.74 vs 0.51), and public voters give more points
> to neighbours once these are chosen. On language the two levels are statistically
> indistinguishable, although both show a mild homophily against chance.

---

## 7. Limitations

- Region and language are attributes of countries, not of songs: a country competing in a
  non-national language is still classified by its main national language. Coding language
  from the `lyrics/` folders of the raw dataset is left as a robustness check.
- The language variable is the most fragile construct of the whole analysis. Results are
  reported for a defensible coding, and the effect of the alternative coding used in the
  original run is documented above rather than hidden.
- Louvain is stochastic; community counts and modularity must be read together with the
  stability analysis, not as point estimates.
- Modularity is reported descriptively. A degree-preserving null model for modularity, as
  used in RQ1, is not yet implemented for RQ2.
- Permutation tests shuffle labels across countries and therefore ignore spatial
  autocorrelation between neighbouring countries; they answer a narrower question than a
  spatially constrained null model would.
- The analyses of stages 2 and 3 did not exist in the original run and were added during the
  reconstruction; they should be read as exploratory extensions.

---

## 8. Provenance

| Element | Source |
|---|---|
| Script specification, expected output, 2016 preview | project conversation, 17 Nov, msg. 769 |
| Run on the 20 networks, produced files | project conversation, 17 Nov, msg. 774 |
| 2016–2026 means, 2016 Balkan community | project conversation, 17 Nov, msg. 784 |
| Matrix format | `analyze_rq1.py`, 16 Nov, msg. 660 |
| Validation counts (19,800 rows, 45/43) | project conversation, 10 Nov, msg. 230 |
| Rule "WLD excluded from the networks" | project conversation, 11 Nov, msg. 395 |

Every number in this folder is recomputed from the raw EurovisionAPI data, not copied from
the conversation.
