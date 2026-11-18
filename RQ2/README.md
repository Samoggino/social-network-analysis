# RQ2 — Voting Communities and Homophily

**Research question.** How do community structure and homophily differ between jury and
public voting? Do the communities detected by modularity optimisation coincide with
geographic and linguistic groups, and is the difference between the two voting levels
geographic or cultural?

This folder contains the analysis scripts, the prepared voting matrices, the numerical
results and the figures for RQ2. The pipeline was rebuilt from scratch — the original scripts
were exchanged as attachments and are not available — and every script here was validated
against the numbers reported in the project conversation (see
[Validation](#4-validation-against-the-original-run)).

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

### 2.1 Descriptive structure (`src/analyze_rq2.py`)

For each of the 20 networks, on the undirected sum-weighted projection:

- Louvain community detection (`resolution = 1.0`, `seed = 42`), number of communities and
  modularity;
- Newman assortativity by subregion;
- share of points awarded inside the voter's own subregion, computed both on the full
  network and on the sub-network of countries that reached the final.

### 2.2 Opportunity correction, margins and tests (`src/analyze_rq2_opportunity.py`)

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

### 2.3 Partitions and stability (`src/analyze_rq2_partitions.py`)

Agreement between the Louvain partition and (a) UN M49 subregions, (b) primary language
family, (c) Eurovision cultural block, measured with NMI and ARI. NMI is not corrected for
chance, ARI is, so both are reported: with 4–5 groups the expected NMI under permutation is
about 0.13–0.25, not zero. A permutation benchmark (500 draws) quantifies that baseline.

Stability is measured by rerunning Louvain over 100 seeds at three resolutions and computing
the mean pairwise ARI between runs, together with the co-assignment matrix.

### 2.4 Consensus partition (`src/analyze_rq2_consensus.py`)

Because a single run is not a result, the 200 runs at the default resolution are turned into
one consensus partition: the co-assignment matrix becomes a distance (`1 − co-assignment`),
countries are merged with average linkage until the modal number of communities across runs
is reached, and the resulting partition is compared with the geographic, linguistic and
cultural ones. Its mean ARI with the individual runs measures how well it represents them.
The community of every country is saved in `rq2_consensus_labels.csv`, together with its mean
co-assignment with the other members of its community (how firmly the runs agree); RQ3 reads
this file.

### 2.5 Modularity null (`src/analyze_rq2_modularity_null.py`)

Modularity depends on density and on the degree sequence, so its raw value is not evidence.
The null keeps the binary structure and permutes the edge weights across it (500 draws): the
set of possible votes is unchanged, every edge survives, and only the association between
"this pair" and "these points" is destroyed. The observed modularity is compared with the
modularity that the same Louvain procedure reaches on the permuted networks.

A topological rewiring is not used: the projection of a final is nearly half complete
(density 0.44 on the full network, 0.62 on the finalists-only network), double edge swaps have
almost no admissible moves, and in a test run they failed to produce a single valid replicate
on three of the forty networks.

### 2.6 Language with geography held constant (`src/analyze_rq2_language_within.py`)

Language families are spatially clustered, so a linguistic effect may be geography in
disguise. For every voter only finalists from *other* subregions are kept as eligible, and
only the choices falling on them are counted. The benchmark is the share of those eligible
countries sharing a language, weighted by the number of cross-region choices of each voter
(the observed share pools all choices, so the benchmark must too). If language has an effect
of its own the observed share must exceed it; if the effect is only geography the two
coincide. The excess is tested per layer with the exact paired sign-flip test over the ten
editions (`rq2_language_within_excess.csv`, Holm and BH over the four tests).

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
python src/analyze_rq2_partitions.py        # about 1 minute
python src/analyze_rq2_consensus.py         # about 20 seconds
python src/analyze_rq2_modularity_null.py   # about 45 seconds
python src/analyze_rq2_language_within.py
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
**18.6%** of jury points and **27.4%** of public points go to the voter's own subregion, and
the Balkan community described for the 2016 public network (Bosnia and Herzegovina, Croatia,
Montenegro, North Macedonia, Serbia, Slovenia) is recovered by the same seeded run.

That community is a property of that particular run, not of the data: section 5.5 shows that
the consensus over 200 runs does not isolate it, which is precisely why the stability
analysis exists.

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
language family. The reconstruction documents the difference rather than hiding it.

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
higher (0.28)**.

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

**With 26 nodes, a single Louvain run is not a result.** A mean ARI of 0.51 means that two
seeds out of three produce different partitions; the community structure must be presented
as a stable core, not as a single coloured graph.

### 5.5 Consensus partition

200 runs per network at the default resolution, average-linkage consensus at the modal
number of communities:

| Mean 2016–2026, full network | Jury | Public |
|---|---:|---:|
| Communities in the consensus | 3.8 | 3.5 |
| Communities in the individual runs (mean) | 4.04 | 3.54 |
| Modularity of the consensus | 0.156 | 0.161 |
| **Mean ARI between consensus and the runs** | **0.604** | **0.806** |
| ARI with subregions | 0.100 | **0.273** |
| *same, single seeded run* | *0.091* | *0.280* |
| ARI with language families | 0.070 | 0.165 |
| ARI with cultural blocks | 0.062 | 0.171 |

The consensus is a much better summary of the ensemble than any single run: it agrees with
the individual runs at 0.60 (jury) and 0.81 (public), against the 0.51 and 0.74 that two runs
agree with each other. But it points to the same conclusion as section 5.3 — **ARI 0.10
against geography for juries, 0.27 for the public** — and the paired comparison confirms it:

| Metric | Public − Jury | Exact p | Holm |
|---|---:|---:|---:|
| ARI with subregions | +0.173 | 0.0039 | 0.027 |
| NMI with subregions | +0.166 | 0.0039 | 0.027 |
| ARI with cultural blocks | +0.109 | 0.0020 | 0.020 |
| ARI with language families | +0.095 | 0.031 | 0.063 |
| ARI between consensus and runs | +0.202 | 0.0020 | 0.020 |

The result therefore does not depend on the arbitrary choice of a seed: with a partition
that represents 200 runs, geography still separates the two levels, and the language gap
remains below the corrected threshold. The consensus of the 2016 public network, for
instance, groups a large Western-Asian/Eastern-European block together with Spain, France and
Italy, and a second block running from Austria to Sweden through Croatia, Hungary, Poland and
Serbia — recognisably geographic, but not the Balkan community of the single run.

### 5.6 Is modularity larger than chance?

500 weight permutations per network, topology fixed:

| Mean, full network | Jury | Public |
|---|---:|---:|
| Density of the projection | 0.445 | 0.443 |
| Observed modularity | 0.154 | 0.160 |
| Modularity under the null | 0.162 | 0.154 |
| Null standard deviation | 0.010 | 0.010 |
| Excess over the null | −0.008 | +0.006 |
| z-score | −0.82 | +0.51 |
| Networks with p < 0.05 | 2/10 | 2/10 |

On the finalists-only network the density is 0.62 and the excess is +0.003 (jury) and +0.006
(public), with 3/10 and 2/10 networks significant.

**The modularity of these networks is what a random placement of the same weights produces.**
The value around 0.15 must therefore not be read as evidence of clear communities: with 25–45
nodes and a nearly half-complete projection, that is simply what Louvain returns. The layer
difference is also not significant (+0.014, exact p = 0.053, Holm 0.211).

This is the technical counterpart of the stability result, and it changes what can be claimed:
the evidence for geographic structure in RQ2 comes from the agreement between partitions and
labels (section 5.3) and from the vote flows (section 5.1), **not** from modularity.

### 5.7 Language with geography held constant

Only pairs from different subregions, averaged over the ten editions:

| | Jury | Public |
|---|---:|---:|
| Choices to a shared language | 18.2% | 18.2% |
| Expected, same-region pairs excluded | 15.2% | 15.5% |
| Excess ratio | 1.20 | 1.18 |
| Points to a shared language | 19.8% | 19.0% |
| Excess ratio (points) | 1.31 | 1.23 |
| Intensive margin | +0.65 | +0.22 |
| Editions above expected (choices) | 9/10 | 9/10 |
| Exact p, choices (Holm) | 0.006 (0.023) | 0.041 (0.082) |
| Exact p, points (Holm) | 0.006 (0.023) | 0.061 (0.082) |

Excluding same-subregion pairs barely reduces the relative excess (1.22 → about 1.19 on
choices), so the linguistic homophily of section 5.1 is **not** just geography in disguise: a
small effect survives among countries that share nothing but a language family. It is
significant for juries after correction; for the public it is in the same direction in 9 of
10 editions but does not survive the Holm correction.

But it is the *same* effect in both layers: the paired differences are −0.04 pp (p = 0.97),
−0.8 pp (p = 0.69) and −0.43 points (p = 0.34). Language contributes to both voting levels
equally, so it cancels in the comparison between them. That is exactly why the layer
difference is geographic and not cultural.

---

## 6. Conclusion

> The difference between public and jury voting is **geographic**. Public communities
> coincide with subregions much more than jury communities (ARI 0.28 vs 0.09, unchanged when
> a 200-run consensus replaces a single seed), they are far more stable across seeds (0.74 vs
> 0.51), and public voters give more points to neighbours once these are chosen (+1.4 against
> +0.5). Language does have a small effect of its own — about +19% over chance even between
> different subregions — but it is identical in the two layers, so it cannot explain the
> difference. Modularity, taken alone, is not evidence here: it does not exceed a
> weight-shuffling null.

---

## 7. Limitations

- Region and language are attributes of countries, not of songs: a country competing in a
  non-national language is still classified by its main national language. The dataset does
  provide the language of each song through the `lyrics/o_<language>.txt` files, which makes a
  song-level check possible; it is not implemented here, and note that 245 of 429 songs
  (57%) are in English, which would weaken the variable rather than strengthen it.
- The language variable is the most fragile construct of the analysis: families are broad
  (Germanic, Slavic, Romance), and the effect of the alternative coding used in the original
  run is documented in section 4 rather than hidden.
- The permuted-label nulls ignore spatial autocorrelation between neighbouring countries, and
  the cross-region test of section 5.7 conditions on a post-treatment variable: subregion
  composition is not random, so the estimate is descriptive rather than causal.
- Modularity is reported with a null, and that null is deliberately conservative in one
  direction: permuting weights breaks the association between a country's strength and its
  scores, which is a real feature of the data.
- Louvain remains stochastic even in its consensus form: the consensus summarises the runs, it
  does not make them identical.
- The analyses of sections 2.2–2.6 were added during the reconstruction and are exploratory
  extensions of the original specification, with the multiple-testing corrections reported
  alongside every comparison.

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
