# Eurovision Song Contest — Social Network Analysis

## Project Overview

This project investigates voting patterns in the **Eurovision Song Contest** using Social Network Analysis (SNA).

The main objective is to study how voting relationships between countries evolve over time, comparing the behavior of professional juries and the public televote.

The analysis covers ten Eurovision editions, from **2016 to 2026**, excluding 2020, when the contest was cancelled.

The project explores reciprocity, transitivity, temporal persistence, voting communities, and other structural characteristics of the Eurovision voting network.

## Dataset and Network Representation

The dataset is based on publicly available Eurovision voting data from [EurovisionAPI](https://github.com/EurovisionAPI).

Each Eurovision edition is represented by two directed, weighted networks:

- **Jury network:** points assigned by national professional juries.
- **Public network:** points assigned through national televoting.

Countries are represented as nodes, while directed edges represent voting relationships.

An edge from country A to country B indicates that country A awarded points to country B. The edge weight corresponds to the number of points awarded (1–8, 10 or 12).

The adjacency matrices follow the convention:

`W[i, j] = points awarded by country i to country j`

Each year contains two adjacency matrices, one for jury votes and one for public votes, resulting in **20 annual networks**.

The analysis distinguishes between zero scores and ineligible voting relationships. In particular, only finalists can receive points, while eligible non-finalist countries may still cast votes.

---

## Research Question 1 — Reciprocity, Transitivity and Temporal Persistence

**How do reciprocity and triadic voting structures differ between jury and public voting, and how persistent are these relationships across Eurovision editions?**

RQ1 investigates whether voting patterns are consistent with random voting mechanisms or reveal structural regularities that cannot be fully explained by annual voting constraints.

### 1. Annual Network Analysis

The first stage analyzes each Eurovision edition independently.

The following properties are examined:

- Binary and weighted reciprocity.
- Reciprocity among high-scoring votes.
- Binary and weighted transitive closure.
- Directed triadic structures.
- Directed cycles and transitive motifs.
- Voting intensity within triadic configurations.

The analysis distinguishes between exact triad census configurations and motifs embedded in denser networks.

**Script:** `RQ1/src/analyze_rq1.py`

### 2. Annual Null Models

Observed network properties are compared with randomized networks to determine whether they differ from patterns expected under controlled voting mechanisms.

Two approaches are used:

**Uniform ballot null model**

Randomizes voting assignments while respecting voting eligibility and the Eurovision ballot scoring structure.

This model provides an initial reference, but does not control for differences in the popularity of competing songs.

**Popularity-controlled null model**

Uses Markov Chain Monte Carlo (MCMC) edge swaps to generate randomized networks while preserving:

- Annual voting eligibility.
- Each voter's set of assigned point values.
- The number of incoming positive votes received by each country, separately for finalist and non-finalist voters.

This controls for recipient popularity measured through incoming positive vote counts (in-degree), but does not preserve the total number of points received (in-strength).

**Script:** `RQ1/src/rq1_popularity_control.py`

Multiple MCMC chains and convergence diagnostics are used to evaluate the stability of the simulated distributions.

### 3. Temporal Persistence Analysis

The annual analysis is extended to investigate whether the same voting relationships reappear across different Eurovision editions.

The temporal analysis considers:

- Country pairs that repeatedly exchange votes.
- Pairs that remain reciprocal whenever both countries are eligible to receive votes.
- Repeated exchanges of high scores (10 or 12 points).
- Persistent directed cycles.
- Persistent transitive configurations.

For each pair or triadic configuration, persistence is calculated relative to the number of editions in which the corresponding structure could occur.

The main analysis includes configurations with at least three eligible editions.

**Script:** `RQ1/src/rq1_temporal_persistence_v2.py`

### 4. Temporal Null Model

A temporal null model is used to assess whether the observed persistence exceeds what would be expected from the structure of the annual voting networks.

The model independently randomizes each annual jury and public network using constrained MCMC edge swaps.

It preserves annual voting eligibility, ballot scores, and recipient in-degree within voter strata, while removing the original identities of voting relationships.

The primary comparison examines the difference between public and jury voting for:

1. Pairs reciprocal in every eligible edition.
2. Pairs reciprocal in at least 75% of eligible editions.
3. Pairs with at least two repeated reciprocal exchanges of 10 or 12 points.

Additional exploratory comparisons consider persistent directed cycles and transitive configurations.

The main temporal null-model results are based on **400 simulated histories across four MCMC chains**.

Monte Carlo p-values and multiple-testing corrections are reported for the primary metrics.

**Script:** `RQ1/src/rq1_temporal_null_model.py`

---

## RQ1 — Main Findings

### Annual Voting Patterns

Means over the ten editions, finalists-only networks:

| Annual metric | Jury | Public | Public − Jury | Expected by the popularity-controlled null | p (two-sided) | Holm |
|---|---:|---:|---:|---:|---:|---:|
| Binary reciprocity | 0.461 | 0.469 | +0.008 | +0.004 | 0.68 | 1.00 |
| Reciprocity of 10/12-point votes | 0.136 | 0.214 | +0.078 | +0.008 | 0.0025 | 0.027 |
| Directed transitive closure | 0.532 | 0.646 | +0.113 | +0.107 | 0.090 | 0.72 |
| Weighted transitive closure | 0.292 | 0.358 | +0.065 | +0.075 | 0.0050 | 0.045 |

Holm correction is applied across the 11 metrics of the popularity-controlled null model (400 samples per network, 4 chains; all R-hat and lag-1 diagnostics OK).

- **Overall reciprocity** is almost identical between jury and public networks, and the difference is not significant.
- **Reciprocal 10/12-point exchanges** are more frequent in public voting (higher in 8 of 10 editions) and the difference is far larger than the null expects. This is the main annual result.
- **Transitive closure** is higher in public voting in every edition, but the popularity-controlled null reproduces almost all of the difference (+0.107 expected vs +0.113 observed): it is largely explained by the concentration of votes on a few popular finalists. The uniform-ballot null model, which does not control popularity, had found it significant.
- **Weighted closure** is significant in the *opposite* direction: the public advantage is smaller than the null expects, so it is not evidence of stronger closed structures in public voting.
- Exact `030C` cycles, more frequent in jury networks under the uniform null, are no longer different once popularity is controlled.

**Caveat on the 10/12-point result.** The null model preserves the number of countries voting for each finalist (in-degree) but not the points they receive (in-strength). High points can therefore move freely in the simulations, so part of the 10/12-point reciprocity result may still reflect the concentration of top scores on a few favourites.

### Temporal Voting Patterns

The temporal analysis reveals stronger differences between jury and public voting.

| Temporal metric | Jury | Public |
|---|---:|---:|
| Pairs always reciprocal | 6 | 15 |
| Pairs reciprocal in at least 75% of opportunities | 15 | 26 |
| Pairs with at least two repeated reciprocal high-score exchanges | 3 | 9 |
| Directed cycles always present | 7 | 7 |
| Transitive configurations always present | 37 | 62 |
| Transitive configurations present in at least 75% of opportunities | 104 | 173 |

All persistence measures are evaluated over configurations with at least three eligible editions.

### Results of the Temporal Null Model

The temporal null model indicates that the difference between public and jury voting is particularly pronounced for persistent reciprocal pairs and repeated high-score exchanges.

For the three primary pair-persistence metrics, the 400-history simulation produced Monte Carlo p-values at the simulation resolution limit of approximately 0.0025.

These comparisons remained below 0.05 following Holm correction across the three selected metrics.

The results suggest that **public voting relationships are more temporally persistent than jury voting relationships**, beyond what is expected under the annual in-degree-controlled null model.

However, these findings should be interpreted as exploratory rather than confirmatory evidence.

They do not, by themselves, establish the causes of persistent voting relationships.

---

## Research Question 2 — Community Structure and Homophily

**How do community structure and homophily differ between jury and public voting, and do the detected communities reflect geographic or linguistic groups?**

RQ2 moves from the structure of individual votes to the structure of the whole network: modularity, the geographic and linguistic composition of the vote flows, and the agreement between the communities found by modularity optimisation and external country attributes.

### 1. Descriptive Structure

For each of the 20 annual networks, on the undirected sum-weighted projection:

- Louvain community detection, number of communities and modularity.
- Newman assortativity by UN M49 subregion.
- Share of points awarded inside the voter's own subregion, on the full network and on the finalists-only sub-network.

The country attribute table classifies the 45 voting countries by UN M49 subregion, by broad language family (allowing several families for multilingual countries), and by a Eurovision cultural block used as a sensitivity check.

**Script:** `RQ2/src/analyze_rq2.py`

### 2. Opportunity Correction, Margins and Tests

A country cannot vote for itself and can only vote for finalists, so part of the observed homophily is imposed by the composition of the final. The expected share of same-subregion choices under random selection is computed analytically for each voter as `|R_v| / |E_v|`, where `E_v` are the eligible finalists and `R_v` those from the same subregion. This gives a benchmark that does not require simulation.

The analysis separates two margins:

- **Extensive margin:** how often a same-subregion country enters the ten chosen ones.
- **Intensive margin:** how many points it receives once chosen.

Homophily is tested by permuting region and language labels across countries, which preserves the vote network and the size of every group. The two voting levels are compared with an exact paired sign-flip test over the ten editions, using all 2¹⁰ configurations, with Holm and Benjamini–Hochberg corrections.

**Script:** `RQ2/src/analyze_rq2_opportunity.py`

### 3. Partition Agreement and Stability

The agreement between the Louvain partition and the geographic, linguistic and cultural partitions is measured with Normalised Mutual Information and the Adjusted Rand Index, against a permutation benchmark. Because NMI is not corrected for chance, ARI is the quantity used to decide whether the agreement is real.

Louvain is stochastic, so the partition is also rerun over 100 seeds at three resolutions; the mean pairwise ARI between runs and the co-assignment matrix describe how reproducible a single run is.

**Script:** `RQ2/src/analyze_rq2_partitions.py`

### 4. Consensus Partition

Since a single run is not a result, the 200 runs at the default resolution are combined into one consensus partition: the co-assignment matrix becomes a distance, countries are merged with average linkage until the modal number of communities is reached, and the consensus is used as the partition to report.

**Script:** `RQ2/src/analyze_rq2_consensus.py`

### 5. Modularity Null

Modularity depends on density and on the degree sequence, so its raw value is not evidence. The binary structure is kept and the edge weights are permuted across it (500 draws), which tests whether the large weights are placed where they are by chance. A topological rewiring is not used, because the projection of a final is nearly half complete and edge swaps have almost no admissible moves.

**Script:** `RQ2/src/analyze_rq2_modularity_null.py`

### 6. Language with Geography Held Constant

Language families are spatially clustered, so a linguistic effect may be geography in disguise. For every voter only finalists from other subregions are kept as eligible, and the observed choices are compared with the share of those eligible countries sharing a language. A language effect that survives is an effect of its own.

**Script:** `RQ2/src/analyze_rq2_language_within.py`

---

## RQ2 — Main Findings

### Homophily and Opportunity Structure

Choosing ten countries at random, **18.7%** of the choices would already fall inside the voter's own subregion. Both levels sit above that benchmark, so geographic homophily is not an artefact of the opportunity structure.

| Mean 2016–2026 | Jury | Public |
|---|---:|---:|
| Choices inside the same subregion | 21.9% | 25.1% |
| Excess ratio (choices) | 1.18 | 1.34 |
| Points to the same subregion | 23.3% | 29.5% |
| Excess ratio (points) | 1.25 | 1.59 |
| Mean points if chosen, same subregion | 6.16 | 6.86 |
| Mean points if chosen, other subregions | 5.70 | 5.46 |
| Intensive margin | +0.47 | +1.40 |

Public voting is more homophilic on all three margins: it chooses neighbours more often and gives them more points once chosen. The intensive margin of +1.4 points is consistent with the RQ1 result on 10- and 12-point exchanges.

The paired comparison between the two levels is significant for every geographic metric and for none of the linguistic ones:

| Metric | Public − Jury | Exact p | Holm |
|---|---:|---:|---:|
| Choices inside the same subregion | +3.2 pp | 0.0020 | 0.012 |
| Points to the same subregion | +6.2 pp | 0.0020 | 0.012 |
| Intensive margin, region | +0.93 points | 0.0098 | 0.039 |
| Choices with a shared language | +0.45 pp | 0.744 | 1.000 |
| Points to a shared language | +0.93 pp | 0.660 | 1.000 |
| Intensive margin, language | +0.11 points | 0.701 | 1.000 |

### Communities and Geography

| Mean 2016–2026, full network | Jury | Public |
|---|---:|---:|
| NMI with UN M49 subregions | 0.273 | 0.432 |
| *permutation benchmark* | *0.157* | *0.131* |
| ARI with UN M49 subregions | 0.091 | 0.280 |
| NMI with language families | 0.342 | 0.378 |
| ARI with language families | 0.083 | 0.141 |
| NMI with cultural blocks | 0.320 | 0.423 |

Because NMI is not corrected for chance, its permutation baseline is 0.13–0.25 rather than zero. ARI has zero expected value under permutation, and it shows the actual result: jury communities have almost no agreement with geography, while public communities agree three times as much. The cultural-block partition behaves like the UN one, so the finding does not depend on the UN classification.

The same conclusion holds when a **consensus** partition built from 200 runs replaces a single seed: ARI 0.10 for juries and 0.27 for the public, while the consensus agrees with the individual runs at 0.60 and 0.81 respectively.

### Stability

| Mean pairwise ARI, 100 seeds | Jury | Public |
|---|---:|---:|
| Resolution 0.8 | 0.54 | 0.66 |
| Resolution 1.0 | 0.51 | 0.74 |
| Resolution 1.2 | 0.56 | 0.75 |

With roughly 25 nodes, a single Louvain run is not a result: at resolution 1.0 the jury partition varies substantially across seeds. Public communities are both more geographic and more reproducible; jury communities are neither.

### Modularity Against a Null

| Mean, full network | Jury | Public |
|---|---:|---:|
| Observed modularity | 0.154 | 0.160 |
| Modularity under weight permutation | 0.162 | 0.154 |
| Excess | −0.008 | +0.006 |
| Networks with p < 0.05 | 2/10 | 2/10 |

Modularity around 0.15 is what a random placement of the same weights produces on a projection of this density, so it is reported but not used as evidence. The evidence for geographic structure comes from the agreement between partitions and labels and from the vote flows.

### Language Beyond Geography

Restricting the computation to pairs from different subregions, 18.2% of the choices go to a country sharing a language family against an expected 15.2% for juries and 15.5% for the public (excess ratio 1.20 and 1.18). The excess is significant for juries (exact p = 0.006, Holm 0.023) and in the same direction for the public in 9 of 10 editions, but not significant there after correction (Holm 0.082). Language therefore has a small effect of its own, but it contributes equally to both voting levels and cancels in the comparison between them.

**RQ2 conclusion:** the difference between public and jury voting is **geographic**. Public communities coincide with subregions much more than jury communities, are far more stable across seeds, and public voters give more points to neighbours once these are chosen. Language has a small effect, identical in the two layers, and modularity taken alone is not evidence here.

### Language Coding

With a defensible language coding the share of points to a shared language is 26.3% for juries and 27.2% for the public. The values reported in the original run (28.9% and 30.5%) are reproduced only by grouping Albania, Armenia, Azerbaijan, Cyprus, Georgia, Greece and Israel under a single `Other` label. The reconstruction documents the difference rather than hiding it, and keeps the linguistically defensible coding.

---

## Methodological Limitations

Several limitations should be considered when interpreting the results:

- The dataset was checked for structural consistency, but independent external validation of every country-to-country vote remains incomplete.
- The popularity-controlled models preserve recipient in-degree, not total received points (in-strength).
- MCMC diagnostics assess stability but cannot guarantee uniform sampling from all admissible networks.
- The temporal null model randomizes annual networks independently and does not incorporate historical dependence.
- Some hypotheses and metrics were selected after preliminary exploration of the data.
- Multiple-testing corrections do not completely eliminate post-selection concerns.
- Persistent voting patterns cannot automatically be attributed to geographical, linguistic, cultural, or political factors.
- The region and language variables describe countries, not songs, and the language coding is the most fragile construct in the analysis; an alternative coding is documented in `RQ2/README.md`.
- Louvain is stochastic: community counts and modularity are reported together with a stability analysis, not as point estimates.
- Modularity in RQ2 is tested against a weight-shuffling null rather than a topological one, because the projection is nearly half complete and edge swaps have almost no admissible moves.
- The RQ2 permutation tests shuffle labels across countries and therefore ignore spatial autocorrelation between neighbouring countries.
- The cross-region language test conditions on subregion composition, which is not random, so its estimate is descriptive rather than causal.
- The opportunity correction, margin decomposition, partition agreement, stability, consensus and null-model analyses were added during the reconstruction and are exploratory extensions of the original specification.

The reported p-values are conditional on the assumptions of the corresponding null models.

---

## Repository Structure

```text
social-network-analysis/
├── README.md
├── docs/
├── eurovision_setup_collega/
├── scripts/
│   ├── build_graph.py
│   ├── style_gexf.py
│   └── gephi/
├── output/
│   └── gephi/eurovision.gephi
│
├── RQ1/
│   ├── src/
│   │   ├── analyze_rq1.py
│   │   ├── rq1_popularity_control.py
│   │   ├── rq1_temporal_persistence_v2.py
│   │   └── rq1_temporal_null_model.py
│   │
│   ├── processed_data/
│   │   └── matrices/
│   │
│   ├── results/
│   │   └── rq1/
│   │
│   └── figures/
│       └── rq1/
│
├── RQ2/
│   ├── README.md
│   ├── src/
│   │   ├── build_eurovision_data.py
│   │   ├── make_country_attributes.py
│   │   ├── analyze_rq2.py
│   │   ├── analyze_rq2_opportunity.py
│   │   ├── analyze_rq2_partitions.py
│   │   ├── analyze_rq2_consensus.py
│   │   ├── analyze_rq2_modularity_null.py
│   │   └── analyze_rq2_language_within.py
│   │
│   ├── processed_data/
│   │   ├── matrices/
│   │   └── tables/
│   │
│   ├── results/
│   │   └── rq2/
│   │
│   └── figures/
│       └── rq2/
│
└── RQ3/
    ├── README.md
    ├── src/
    │   ├── analyze_rq3.py
    │   ├── analyze_rq3_popularity_null.py
    │   └── analyze_rq3_ranking.py
    ├── results/
    │   └── rq3/
    └── figures/
        └── rq3/
```

The `RQ1`, `RQ2` and `RQ3` directories each contain the analysis scripts, the prepared voting matrices, the numerical results and the visualizations for the corresponding research question. The `docs` directory collects the project documents. `scripts/` builds the vote networks for Gephi (see *Grafi e Gephi* below); its output in `output/` is regenerated and not versioned, except the Gephi project. Other research questions and project components can be added to the repository as development continues.

---

## Reproducing RQ1

### Requirements

The analysis uses Python and the scientific computing libraries NumPy, NetworkX, and Matplotlib.

Install the required packages:

```bash
python -m pip install numpy networkx matplotlib
```

The voting matrices in `RQ1/processed_data/matrices/` are produced by `eurovision_setup_collega/build_eurovision_data.py`; `python3 scripts/build_graph.py --matrices` writes identical matrices to `output/processed_data/`.

### Costly results

The two MCMC null models take hours to run. Their outputs are versioned so they do not need to be recomputed; rerunning the commands below overwrites them.

| Outputs | Script | Parameters |
|---|---|---|
| `rq1_popularity_robust_*` and `figures/rq1/rq1_popularity_robust_comparison.png` | `rq1_popularity_control.py` | 400 samples, 4 chains, burn-in 15, thinning 4, seed 20261118 |
| `rq1_temporal_null_*` and `figures/rq1/rq1_temporal_null_comparison.png` | `rq1_temporal_null_model.py` | 400 histories, 4 chains, burn-in 15, thinning 4, seed 20261118 |

The parameters of each run are recorded in its `*_config.json`. The temporal null model also reads `rq1_temporal_pairs.csv` and `rq1_temporal_motifs.csv`: if `rq1_temporal_persistence_v2.py` is rerun on different data, the temporal null model must be rerun too. All other RQ1 outputs are regenerated in minutes.

### Running the analysis

First, move into the RQ1 directory:

```bash
cd RQ1
```

Run the annual network analysis:

```bash
python src/analyze_rq1.py
```

Run the popularity-controlled annual null model:

```bash
python src/rq1_popularity_control.py --simulations 400 --chains 4 --burnin-per-edge 15 --thin-per-edge 4
```

Run the descriptive temporal persistence analysis:

```bash
python src/rq1_temporal_persistence_v2.py
```

Finally, run the temporal null model:

```bash
python src/rq1_temporal_null_model.py --histories 400 --chains 4 --burnin-per-edge 15 --thin-per-edge 4
```

The scripts use the voting matrices stored in `processed_data/matrices/`.

Generated numerical results are stored in `results/rq1/`, while plots are stored in `figures/rq1/`.

The MCMC analyses may require substantial computation time, depending on the available hardware and simulation parameters.

---

## Reproducing RQ2

The scripts use the voting matrices stored in `RQ2/processed_data/matrices/` and the country attribute table in `RQ2/processed_data/tables/`, so no external download is needed.

Move into the RQ2 directory and run the three analysis steps:

```bash
cd RQ2
python src/analyze_rq2.py
python src/analyze_rq2_opportunity.py
python src/analyze_rq2_partitions.py
python src/analyze_rq2_consensus.py
python src/analyze_rq2_modularity_null.py
python src/analyze_rq2_language_within.py
```

The partition and stability script takes about a minute, as it reruns Louvain over 100 seeds and three resolutions for each of the 20 networks; the modularity null takes about forty-five seconds.

To rebuild the matrices from the raw EurovisionAPI export instead:

```bash
python src/build_eurovision_data.py path/to/dataset-main/data/senior
python src/make_country_attributes.py
```

Every random seed used above is explicit in the scripts, so the results are reproducible. A single Louvain run is not robust to the seed (mean ARI between two runs 0.51 for juries and 0.74 for the public), which is why the stability analysis and the consensus partition are part of the pipeline.

---

## Reproducing RQ3

RQ3 (prestige and bridging) reads the matrices in `RQ1/processed_data/matrices/`, the attribute table in `RQ2/processed_data/tables/` and the RQ2 consensus partition in `RQ2/results/rq2/rq2_consensus_labels.csv` (rerun RQ3 if the RQ2 consensus changes). It runs in about a minute and a half:

```bash
cd RQ3
python src/analyze_rq3.py
python src/analyze_rq3_popularity_null.py
python src/analyze_rq3_ranking.py
```

The first script writes the main results, the second re-tests the bridging measures against a null that keeps each finalist's popularity fixed, and the third writes the ranked table of prestige; the last one reads the output of the first.

Method, results and limitations are in `RQ3/README.md`.

---

## Grafi e Gephi (`scripts/build_graph.py`)

Il dataset EurovisionAPI (non ufficiale, ma completo) e le API sono clonati
nelle cartelle `dataset/` ed `eurovision-api/`:

```bash
git clone git@github.com:EurovisionAPI/dataset.git dataset
git clone git@github.com:EurovisionAPI/eurovision-api.git eurovision-api
```

I grafi vengono costruiti da `scripts/build_graph.py`, che usa solo la
standard library di Python 3. Lo script applica **le stesse regole della
pipeline del gruppo** (`build_eurovision_data.py`, vedi
`eurovision_setup_collega/`): con `--matrices` produce matrici e tabelle
identiche byte per byte a quelle dei compagni.

### Regole sui dati (condivise con il gruppo)

- **Edizioni**: finali 2016–2026, 2020 escluso (annullato): 10 edizioni.
  Il 2016 è il primo anno con punti di giuria e televoto separati.
- **Solo Grand Final**: i paesi eliminati in semifinale votano nella finale
  ma non possono ricevere punti.
- **Giuria e televoto sempre separati** (`jury`, `public`): 10 edizioni × 2
  livelli = **20 reti annuali**. `total` (somma dei due) esiste solo su
  richiesta e non è usato nelle analisi.
- **WLD** (voto del "resto del mondo", dal 2023) è escluso: non è un paese.
- **Validazione**: nessun autovoto, punti in {0, 1–8, 10, 12}, ogni votante
  vota tutti gli altri finalisti e assegna esattamente 1–8, 10, 12 (58 punti),
  stessi votanti per giuria e televoto. Se un controllo fallisce lo script si
  ferma.
- **Zero ≠ cella vuota**: un'*opportunità* è una coppia (A, B) in cui A poteva
  votare B. Uno 0 è un'opportunità senza punti (nessun arco, ma conta nelle
  normalizzazioni); una cella vuota è un voto impossibile.

Con lo snapshot attuale: 45 paesi, 43 finalisti almeno una volta (BA e ME
solo votanti), 19.698 opportunità di voto nazionali.

### Cosa rappresenta il grafo

- **Nodo** = paese. `role` = `finalist` oppure `voter_only` (mai finalista
  nel periodo scelto).
- **Arco orientato `A -> B`** = `A` ha assegnato punti a `B`; peso = punti.
- Su più edizioni (`--aggregate`) esiste un solo arco per coppia, con i punti
  sommati e le statistiche per opportunità.

### Uso rapido

```bash
python3 scripts/build_graph.py                    # 20 reti annuali -> output/per-year/
python3 scripts/build_graph.py --year 2025        # 2025, giuria e televoto
python3 scripts/build_graph.py --score jury       # solo giurie (10 reti)
python3 scripts/build_graph.py --finalists-only   # sottorete dei finalisti (RQ1)
python3 scripts/build_graph.py --matrices         # anche output/processed_data/ come i compagni
python3 scripts/build_graph.py --aggregate --edge-weight per_opportunity  # rete 2016-2026 per livello
python3 scripts/build_graph.py --year 2025 --min-points 8   # dicotomizzazione: solo voti >= 8
python3 scripts/build_graph.py --country IT --ego-mode in   # chi vota l'Italia, per edizione
python3 scripts/build_graph.py --all-countries    # una rete ego per paese (aggregata)
python3 scripts/build_graph.py --list-countries
```

Esempio: `--year 2025` genera `output/per-year/2025_jury.gexf` e
`2025_public.gexf`, entrambi con 37 nodi (26 finalisti + 11 votanti
eliminati) e 370 archi (37 votanti × 10 paesi votati).

### Opzioni

| Opzione | Default | Significato |
|---|---|---|
| `--from`, `--to`, `--year` | `2016`, `2026` | Edizioni incluse (prima del 2016 non c'è la separazione giuria/televoto) |
| `--score` | `both` | `both` (giuria e televoto separati), `jury`, `public`/`tele`, `total` |
| `--aggregate` | off | Una rete sull'intero periodo invece di una per edizione |
| `--finalists-only` | off | Solo i finalisti come votanti (reciprocità e triadi) |
| `--min-points N` | `1` | Un voto diventa arco solo se vale almeno `N` punti |
| `--edge-weight` | `sum` | Peso in Gephi: `sum`, `mean`, `per_opportunity`, `frequency` |
| `--country CODE`, `--ego-mode` | –, `in` | Rete ego: voti ricevuti (`in`), dati (`out`) o entrambi |
| `--all-countries` | off | Una rete ego per paese in `output/per-country/<livello>/` |
| `--matrices` | off | Scrive `output/processed_data/` (matrici + `votes_master.csv` + `nodes.csv`) |
| `--output-dir`, `--name` | `output/` | Cartella e nome dei file |

### File prodotti

Per ogni rete: `*.gexf` (Gephi), `*_nodes.csv`, `*_edges.csv`; in
`per-year/` e `per-country/` anche un `index.csv` riassuntivo.

Attributi degli archi:

| Attributo | Significato |
|---|---|
| `weight` | Il valore scelto con `--edge-weight` |
| `points` | Punti totali |
| `n_votes` | Numero di volte in cui A ha dato punti a B |
| `opportunities` | Edizioni in cui A poteva votare B |
| `frequency` | `n_votes / opportunities` |
| `weight_mean` | Punti medi quando A sceglie B (`points / n_votes`) |
| `per_opportunity` | Punti medi per opportunità, zeri inclusi (`points / opportunities`) |
| `first_year`, `last_year`, `years` | Copertura temporale |

Attributi dei nodi: `role`, `years_finalist`, `years_voting`,
`opportunities_in`, `opportunities_out`, `in_weight`, `out_weight`,
`in_degree`, `out_degree`, `votes_received`, `votes_given`, `flag_url`.

### Grafi già impostati per Gephi

`scripts/style_gexf.py` (richiede `networkx`) scrive accanto a ogni GEXF un
`*_styled.gexf` che Gephi apre già impostato: layout force-directed,
colore = comunità Louvain (attributo `modularity_class`; grigio i paesi mai
finalisti), dimensione = punti ricevuti, spessore archi = `weight`.

```bash
python3 scripts/build_graph.py --finalists-only --min-points 8
python3 scripts/style_gexf.py output/per-year/*_finalists_min8.gexf
gephi output/per-year/2025_public_finalists_min8_styled.gexf
```

Etichette e frecce si attivano a mano nel tab **Preview** (non sono salvabili
nel GEXF).

### Import in Gephi

1. `File > Open` e selezionare il file `.gexf`.
2. Layout force-directed (`ForceAtlas2` o `Fruchterman-Reingold`).
3. Dimensione dei nodi: **Ranking** su `in_weight`; colore: `role`, oppure
   `Modularity Class` dopo aver lanciato Louvain da **Statistics**.
4. Spessore degli archi: **Ranking → Edges → weight → Thickness**; in
   **Preview** attivare le frecce.

In alternativa: `File > Import Spreadsheet`, prima `*_nodes.csv` poi
`*_edges.csv`.

### Note metodologiche

- In una rete annuale ogni votante ha sempre esattamente 10 archi uscenti:
  la struttura interessante sta nei pesi, nella reciprocità e nelle soglie
  (`--min-points`), non nel grado uscente.
- I non finalisti hanno solo archi uscenti: abbassano artificialmente
  reciprocità e cicli. Per quelle metriche usare `--finalists-only`.
- Nelle reti aggregate i punti grezzi favoriscono chi è stato più spesso in
  finale: per confronti usare `per_opportunity` o `frequency`.
- La validazione è interna; il confronto con i registri ufficiali EBU non è
  stato fatto.

---

## Link utili

- [Google Drive](https://drive.google.com/drive/folders/1RnNtQ6CDBwP8irH7YeirozYXSrutNwkV)

## Project Status

- **RQ1:** Annual structural analysis, popularity-controlled null models, temporal persistence analysis, and temporal null model completed.
- **RQ2:** Community structure, opportunity-corrected homophily, extensive and intensive margins, partition agreement, consensus partition, modularity null model and cross-region language test completed.
- **RQ3:** Prestige (in-strength, PageRank, HITS), concentration of consensus and bridging with fixed geographic/cultural groups and with the RQ2 consensus communities completed, with a sensitivity check on finalists voted by fewer than 5 countries. The bridging measures and the prestige–participation correlation are also tested against a popularity-preserving null, which confirms them: the correlation is 0.72 / 0.82 observed against 0.01 / −0.05 under that null, so it is bloc support and not a sample-size effect. Open items:
  - [x] **Popularity-preserving null model.** Done in `RQ3/src/analyze_rq3_popularity_null.py`: in-degree and in-strength are held fixed per finalist and only the identity of its voters is redrawn. Result 4 of `RQ3/README.md` is therefore confirmed, and the 0.25 of the uniform ballots turns out to be an artefact of that null rather than a popularity effect.
  - [ ] **TODO — agree the formulation of RQ3 in the group.** The current one (prestige + bridging, see `RQ3/README.md`) has not been approved by the group yet.
  - [ ] **TODO — write the RQ3 section of the report**, linking it to RQ1 (popularity there is a confounder to control, here it is the object of study) and to RQ2 (the home excess is the RQ2 homophily seen from the recipient's side), so that results are not repeated.
  - [ ] **TODO — decide whether `RQ3/results/` and `RQ3/figures/` are versioned.** They are regenerated in about a minute and a half.
- **Other research questions:** Under development.

## Data Source

EurovisionAPI — [GitHub repository](https://github.com/EurovisionAPI)

The project is developed for academic purposes as part of a university course in Social Network Analysis.
