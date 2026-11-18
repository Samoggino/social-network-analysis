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

The annual analysis reveals that:

- Overall binary reciprocity is relatively similar between jury and public networks.
- High-scoring reciprocal exchanges are generally more frequent in public voting.
- Public networks exhibit greater transitive closure in the observed data.
- Some annual differences become less pronounced after controlling for the number of positive votes received by each finalist.
- The distinction between exact triadic configurations and motifs embedded in larger structures is important for interpreting the results.

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

### Stability

| Mean pairwise ARI, 100 seeds | Jury | Public |
|---|---:|---:|
| Resolution 0.8 | 0.54 | 0.66 |
| Resolution 1.0 | 0.51 | 0.74 |
| Resolution 1.2 | 0.56 | 0.75 |

With roughly 25 nodes, a single Louvain run is not a result: at resolution 1.0 the jury partition varies substantially across seeds. Public communities are both more geographic and more reproducible; jury communities are neither.

**RQ2 conclusion:** the difference between public and jury voting is **entirely geographic**. Public communities coincide with subregions much more than jury communities, are far more stable across seeds, and public voters give more points to neighbours once these are chosen. On language the two levels are statistically indistinguishable, although both show a mild homophily against chance.

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
- Modularity in RQ2 is descriptive; a degree-preserving null model for modularity is not yet implemented.
- The RQ2 permutation tests shuffle labels across countries and therefore ignore spatial autocorrelation between neighbouring countries.
- The opportunity correction, margin decomposition, partition agreement and stability analyses were added during the reconstruction and are exploratory extensions of the original specification.

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
└── RQ2/
    ├── README.md
    ├── src/
    │   ├── build_eurovision_data.py
    │   ├── make_country_attributes.py
    │   ├── analyze_rq2.py
    │   ├── analyze_rq2_opportunity.py
    │   └── analyze_rq2_partitions.py
    │
    ├── processed_data/
    │   ├── matrices/
    │   └── tables/
    │
    ├── results/
    │   └── rq2/
    │
    └── figures/
        └── rq2/
```

The `RQ1` and `RQ2` directories each contain the analysis scripts, the prepared voting matrices, the numerical results and the visualizations for the corresponding research question. The `docs` directory collects the project documents. `scripts/` builds the vote networks for Gephi (see *Grafi e Gephi* below); its output in `output/` is regenerated and not versioned, except the Gephi project. Other research questions and project components can be added to the repository as development continues.

---

## Reproducing RQ1

### Requirements

The analysis uses Python and the scientific computing libraries NumPy, pandas, NetworkX, and Matplotlib.

Install the required packages:

```bash
python -m pip install numpy pandas networkx matplotlib
```

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
```

The last script takes about a minute, as it reruns Louvain over 100 seeds and three resolutions for each of the 20 networks.

To rebuild the matrices from the raw EurovisionAPI export instead:

```bash
python src/build_eurovision_data.py path/to/dataset-main/data/senior
python src/make_country_attributes.py
```

Any country ordering or random seed used above is explicit in the scripts: the Louvain seed affects the number of communities and modularity in the third decimal, which is why the stability analysis is part of the pipeline.

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
- **RQ2:** Community structure, opportunity-corrected homophily, extensive and intensive margins, partition agreement and Louvain stability completed.
- **Other research questions:** Under development.

## Data Source

EurovisionAPI — [GitHub repository](https://github.com/EurovisionAPI)

The project is developed for academic purposes as part of a university course in Social Network Analysis.
