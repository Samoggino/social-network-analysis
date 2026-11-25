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

RQ2 uses two references. One permutes positive edge weights on the fixed projection. The other samples rule-compliant ballots with eligible recipients and projects the resulting network. Each uses 2,000 samples for every edition, layer and scope. Holm is applied separately to the 40 tests per model.

Scripts `RQ2/src/analyze_rq2_modularity_null.py` and `RQ2/src/analyze_rq2_ballot_null.py`.

### 6. Language with Geography Held Constant

Language families are spatially clustered, so a linguistic effect may be geography in disguise. For every voter only finalists from other subregions are kept as eligible, and the observed choices are compared with the share of those eligible countries sharing a language. The result describes the association conditional on subregion eligibility.

**Script:** `RQ2/src/analyze_rq2_language_within.py`

---

## RQ2 — Main Findings

- Televoting assigns a larger share of choices and points to countries in the same UN subregion. The mean differences are about +3.16 and +6.20 percentage points. The leave-one-edition-out results keep both differences positive.
- The consensus partition agrees more closely with geographic subregions for televoting. The partitions and their stability are reported across the Louvain runs and scopes.
- With 2,000 samples per network and scope, 5 of 40 tests using random ballots and 1 of 40 tests using shuffled weights have Holm-adjusted upper-tail p-values below 0.05. The adjustment is computed separately for each model from the nominal CSV p-values.
- The revised country attributes assign official language families to Finland, Ireland, Cyprus and Malta. The cross-subregion language analysis estimates choices and points against separate opportunity benchmarks. The paired comparison provides no evidence of a difference between layers after Holm.

The [RQ2 README](RQ2/README.md) and [report](RQ2/Spiegazione_analisi_e_risultati.pdf) describe the results and validation.

---

## Methodological Limitations

Several limitations should be considered when interpreting the results:

- The dataset was checked for structural consistency, but independent external validation of every country-to-country vote remains incomplete.
- The RQ1 popularity-controlled models fix recipient in-degree. The conditional RQ3 null also fixes the recipient's received points and score multiset.
- MCMC diagnostics assess stability but cannot guarantee uniform sampling from all admissible networks.
- The temporal null model randomizes annual networks independently and does not incorporate historical dependence.
- Some hypotheses and metrics were selected after preliminary exploration of the data.
- Multiple-testing corrections do not completely eliminate post-selection concerns.
- Persistent voting patterns cannot automatically be attributed to geographical, linguistic, cultural, or political factors.
- The region and language variables describe countries, not songs, and the language coding is the most fragile construct in the analysis; an alternative coding is documented in `RQ2/README.md`.
- Louvain is stochastic: community counts and modularity are reported together with a stability analysis, not as point estimates.
- The two RQ2 modularity nulls preserve different properties. One permutes weights on the fixed projection, and one preserves ballot eligibility and the individual score set.
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
├── data_preparation/
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
├── RQ3/
│   ├── README.md
│   ├── src/
│   │   ├── analyze_rq3.py
│   │   ├── analyze_rq3_popularity_null.py
│   │   └── analyze_rq3_ranking.py
│   ├── results/
│   │   └── rq3/
│   └── figures/
│       └── rq3/
│
├── RQ4/
│   ├── README.md
│   ├── src/
│   │   ├── analyze_rq4_layer_similarity.py
│   │   ├── analyze_rq4_temporal_stability.py
│   │   └── rq4_common.py
│   ├── results/
│   │   └── rq4/
│   └── figures/
│       └── rq4/
│
└── RQ5/
    ├── README.md
    ├── src/
    │   ├── analyze_rq5_prediction.py
    │   └── rq5_common.py
    ├── results/
    │   └── rq5/
    └── figures/
        └── rq5/
```

Each `RQ` directory contains its source and results. RQ1 and RQ2 contain voting matrices. RQ3 reads its matrices and labels from RQ2. RQ4 and RQ5 read the RQ1 matrices, and RQ5 reads the RQ2 country attributes. The `docs` directory collects the project documents. `scripts/` builds the vote networks for Gephi (see *Grafi e Gephi* below); its output in `output/` is regenerated and not versioned, except the Gephi project. Other research questions and project components can be added to the repository as development continues.

---

## Reproducing RQ1

### Requirements

The analysis uses Python and the scientific computing libraries NumPy, NetworkX, and Matplotlib.

Install the required packages:

```bash
python -m pip install numpy networkx matplotlib
```

The voting matrices in `RQ1/processed_data/matrices/` are produced by `data_preparation/build_eurovision_data.py`; `python3 scripts/build_graph.py --matrices` writes identical matrices to `output/processed_data/`.

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

To regenerate the paper figure (PNG and PDF) from the validated RQ1 CSVs without rerunning the simulations, run `python -B src/rq1_temporal_null_model.py --plot-only` from `RQ1/`.

The MCMC analyses may require substantial computation time, depending on the available hardware and simulation parameters.

---

## Reproducing RQ2

Run the pipeline in `RQ2/`. The matrices are included.

```bash
cd RQ2
python -m pip install -r requirements.txt
python run_all.py
```

Full data checks, the optional matrix reconstruction and the two modularity nulls are described in [RQ2/README.md](RQ2/README.md).

---

## Reproducing RQ3

RQ3 reads the matrices, country attributes and consensus labels directly from RQ2. Run RQ2 first if its inputs or consensus change.

```bash
cd RQ3
python -m pip install -r requirements.txt
python src/analyze_rq3.py
python src/analyze_rq3_popularity_null.py
python src/analyze_rq3_ranking.py
```

The ranking script uses the aggregate from the first script. The [RQ3 README](RQ3/README.md) and [report](RQ3/Spiegazione_analisi_e_risultati.pdf) document the parameters, results and tests.

---

## Reproducing RQ4

RQ4 compares jury and national televote within each Grand Final and measures stability across editions. It reads the 20 voting matrices in `RQ1/processed_data/matrices/`.

```bash
cd RQ4
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
python -B run_all.py
```

The primary metric is Pearson correlation after fitting additive voter and recipient fixed effects on the common eligible dyads. The primary tests use 9,999 permutations within finalist roles, preserving eligibility. In the temporal null, each edition uses one permutation shared by both voting layers and reused across all pairs involving that edition. Two-sided Monte Carlo p-values are Holm-adjusted separately for the ten within-edition tests and the three lag-1 tests. Other metrics, lags 2–9 and robustness checks are descriptive.

The [RQ4 README](RQ4/README.md) documents the results and the null hypotheses. The run configuration records the seeds, software versions and matrix checksums.

---

## Reproducing RQ5

RQ5 ranks the eligible recipients of the 8-, 10- and 12-point votes in the Grand Finals of 2023–2026. It reads the vote matrices from `RQ1/processed_data/matrices/` and country attributes from `RQ2/processed_data/tables/`.

```bash
cd RQ5
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
python -B src/analyze_rq5_prediction.py
```

The four nested models and the simple History baseline use only earlier editions to construct their features. Historical graphs contain only countries observed by that point. The Louvain consensus method from RQ2 is used as a sensitivity check and is recomputed on the available history. The [RQ5 README](RQ5/README.md) documents the metrics, tie-breaking rule, input checksums and reproducibility checks.

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
`data_preparation/`): con `--matrices` produce matrici e tabelle
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

### Figure di rete per la relazione

`scripts/gephi/render_report.sh` produce le due figure di rete della relazione
con le librerie di Gephi (ForceAtlas2 + export Preview, senza GUI; serve un
display X/Wayland per l'export PNG) e le bandiere come icone dei nodi:

- `output/gephi/report/fig_strong_ties.png`: rete aggregata 2016–2026,
  arco A → B se A ha dato in media ≥ 6 punti per opportunità (≥ 3 finali);
  archi colorati se interni alla subregione ONU, grigi altrimenti
  (giuria 74 archi, 35% intra-subregione; televoto 130, 48%);
- `output/gephi/report/fig_reciprocal_ties.png`: coppie reciproche in almeno
  il 75% delle finali ammissibili (RQ1: 15 giuria, 26 televoto).

Richiede prima `python3 scripts/build_graph.py --aggregate --edge-weight per_opportunity`.
Le bandiere sono scaricate una volta da flagcdn.com in `output/gephi/flags/`.

### Bandiere nei grafici matplotlib

`scripts/flags.py` aggiunge le bandiere dei paesi (PNG da flagcdn.com, in cache
in `output/flags/`) ai grafici in cui compaiono paesi: rete delle comunità 2016
(`analyze_rq2.py`), heatmap di consenso e stabilità (`analyze_rq2_consensus.py`,
`analyze_rq2_partitions.py`), home bias per paese e prestigio giuria vs
televoto (`analyze_rq3.py`). I grafici senza paesi (serie temporali,
istogrammi, `rq3_prestige_vs_participation` con un punto per finalista ed
edizione) restano invariati.

### Ambiente Python

Gli script vanno eseguiti nell'env locale `.venv` (mai il Python di sistema):
`.envrc` lo crea con `uv` alla prima `direnv allow`, con le versioni di
`RQ2/requirements.txt` più scipy per RQ3.

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
- **RQ3:** Prestige, concentration and the origin of support. The observed geographic prestige–participation correlation (0.717 jury, 0.815 public) is compatible with the fixed-popularity reference (0.753 and 0.836). Public geographic home excess is higher in the paired comparison of standardised deviations (Holm p = 0.0391).
  - [x] **Popularity-preserving null model.** The recipient's voter count and score multiset are held fixed. The corrected indexing uses the same retained finalists in the observed and simulated correlations.
  - [ ] **TODO — agree the formulation of RQ3 in the group.** The current one (prestige + bridging, see `RQ3/README.md`) has not been approved by the group yet.
  - [ ] **TODO — write the RQ3 section of the report**, linking it to RQ1 (popularity there is a confounder to control, here it is the object of study) and to RQ2 (the home excess is the RQ2 homophily seen from the recipient's side), so that results are not repeated.
  - [ ] **TODO — decide whether `RQ3/results/` and `RQ3/figures/` are versioned.** They are regenerated in about a minute and a half.
- **RQ4.** The mean within-edition fixed-effect residual Pearson correlation is 0.2413 (Holm p = 0.0020 in each of the ten editions). Across consecutive editions it is 0.1178 for juries and 0.4717 for televote, a gap of +0.3539 with televote higher in all nine pairs. Both layer means and the gap exceed the reference with exchangeable country labels across editions (Holm p = 0.0006 for each). The gap test concerns that reference. Equal stability between two processes that may both be persistent is a separate question.
  - The gap is +0.3464 on the 130 always-eligible dyads and ranges from +0.3182 to +0.3743 when omitting one edition at a time. The [RQ4 README](RQ4/README.md) reports the descriptive sensitivity of the other metrics.
  - [ ] **TODO — agree the formulation of RQ4 in the group.** The current formulation covers layer similarity and temporal stability.
  - [ ] **TODO — write the RQ4 section of the report.** Relate matrix-level similarity to the persistence of reciprocal and triadic configurations in RQ1.
  - [ ] **TODO — confirm which outputs in `RQ4/results/` and `RQ4/figures/` should remain versioned.**
- **RQ5 (optional, predictive).** In the four test editions, adding vote history to recipient popularity improved mean televote Hit@3 from 0.2103 to 0.4273 (+0.2171, higher in all four editions). The simple History baseline reached 0.4160. For juries, History and M0b both reached 0.2461.
  - Adding geography and language together changed mean Hit@3 by +0.0093 for juries and +0.0024 for televote. Adding the main community features changed it by -0.0113 and +0.0025, respectively. Using Louvain consensus instead of the main partition changed M2 by +0.0023 and -0.0068. These differences describe the four observed editions. Their predictive value in future editions remains open.
  - [ ] **TODO — agree the formulation of RQ5 in the group.** The current formulation covers walk-forward prediction of the three highest-point recipients.
  - [ ] **TODO — write the RQ5 section of the report.** Relate the prediction results to the community analysis in RQ2 and the temporal stability analysis in RQ4.
  - [ ] **TODO — confirm which outputs in `RQ5/results/` and `RQ5/figures/` should remain versioned.**
  - [ ] **TODO — optional inner temporal validation** to choose the L2 penalty and smoothing constant. Both are currently fixed in advance.

## Data Source

EurovisionAPI — [GitHub repository](https://github.com/EurovisionAPI)

The project is developed for academic purposes as part of a university course in Social Network Analysis.
