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

## Methodological Limitations

Several limitations should be considered when interpreting the results:

- The dataset was checked for structural consistency, but independent external validation of every country-to-country vote remains incomplete.
- The popularity-controlled models preserve recipient in-degree, not total received points (in-strength).
- MCMC diagnostics assess stability but cannot guarantee uniform sampling from all admissible networks.
- The temporal null model randomizes annual networks independently and does not incorporate historical dependence.
- Some hypotheses and metrics were selected after preliminary exploration of the data.
- Multiple-testing corrections do not completely eliminate post-selection concerns.
- Persistent voting patterns cannot automatically be attributed to geographical, linguistic, cultural, or political factors.

The reported p-values are conditional on the assumptions of the corresponding null models.

---

## Repository Structure

```text
social-network-analysis/
├── README.md
├── eurovision_setup_collega/
│
└── RQ1/
    ├── src/
    │   ├── analyze_rq1.py
    │   ├── rq1_popularity_control.py
    │   ├── rq1_temporal_persistence_v2.py
    │   └── rq1_temporal_null_model.py
    │
    ├── processed_data/
    │   └── matrices/
    │
    ├── results/
    │   └── rq1/
    │
    └── figures/
        └── rq1/
```

The `RQ1` directory contains the analysis scripts, prepared voting matrices, numerical results, and visualizations.

Other research questions and project components can be added to the repository as development continues.

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

## Project Status

- **RQ1:** Annual structural analysis, popularity-controlled null models, temporal persistence analysis, and temporal null model completed.
- **Other research questions:** Under development.

## Data Source

EurovisionAPI — [GitHub repository](https://github.com/EurovisionAPI)

The project is developed for academic purposes as part of a university course in Social Network Analysis.
