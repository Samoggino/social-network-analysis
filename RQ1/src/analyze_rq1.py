#!/usr/bin/env python3
"""RQ1 COMPLETA — Eurovision: reciprocita, transivita, triadi e test Monte Carlo.

Da salvare come eurovision-sna/src/analyze_rq1.py
Esecuzione: py src/analyze_rq1.py
Per una prova rapida: py src/analyze_rq1.py --simulations 100
Per la sola parte descrittiva: py src/analyze_rq1.py --simulations 0

Dipendenze: numpy, networkx, matplotlib.
Legge processed_data/matrices/{anno}_{jury|public}.csv.
NON modifica mai le matrici d'origine. Sovrascrive solo i propri CSV e grafici
nella cartella results/rq1 e figures/rq1.

Metodi:
 - Analisi principalmente sulla sottorete dei soli finalisti, per confrontare
   strutture che possono essere reciproche. Reciprocita anche sulla rete completa.
 - Reciprocita binaria: archi con arco inverso / archi.
 - Reciprocita pesata: somma min(w_ij,w_ji) su archi diretti / somma w_ij.
 - Reciprocita >=8, >=10: entrambi i voti devono raggiungere la soglia.
 - Chiusura transitiva binaria: #cammini i->j->k chiusi da i->k / #cammini.
 - Chiusura transitiva pesata (0-1): media di (w_ik/12), ponderata
   per sqrt(w_ij*w_jk) su TUTTI i cammini (non chiusi = 0).
 - Intensita di ogni chiusura: media geometrica dei tre pesi (1-12),
   SENZA escludere triadi che hanno anche altri archi.
 - Cicli: ogni ciclo orientato di tre nodi e contato una sola volta;
   sono inclusi anche nei sottografi con archi aggiuntivi.
 - Censimento triadico NetworkX: 16 classi, tra cui 030T e 030C esatte.
 - Modello nullo: 1-8,10,12 assegnati casualmente senza ripetizioni a
   dieci finalisti eleggibili per ogni votante; NO controllo popolarita.
 - Test Monte Carlo: p empirico a due code su deviazione dalla media nulla,
   con correzione +1. Risultati esplorativi senza correzioni per multipli
   confronti o dipendenza tra edizioni.
"""
from __future__ import annotations

import argparse
import csv
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
BALLOT = np.array((1, 2, 3, 4, 5, 6, 7, 8, 10, 12), dtype=np.int16)
VALID = {0, *BALLOT.tolist()}
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if HERE.name.lower() == "src" else HERE
MATRICES = ROOT / "processed_data" / "matrices"
RESULTS = ROOT / "results" / "rq1"
FIGURES = ROOT / "figures" / "rq1"
COLORS = {"jury": "#246b91", "public": "#cf7135"}

# Ogni metrica e calcolata sulle matrici pesate dei soli finalisti.
# I nomi sono mantenuti stabili per il confronto delle simulazioni.
NULL_METRICS = (
    "binary_reciprocity", "weighted_reciprocity", "reciprocity_ge8",
    "reciprocity_ge10", "directed_transitive_closure", "weighted_closure",
    "triads_030T", "triads_030C", "all_transitive_motif_intensity",
    "all_cycle_motif_intensity", "all_cycle_count",
)


def write_csv(path: Path, columns: list[str], rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


def read_matrix(path: Path):
    """La cella vuota indica voto NON ammissibile; zero = voto ammissibile ma assente."""
    if not path.is_file():
        raise FileNotFoundError(f"Matrice non trovata: {path}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or header[0].strip().lower() != "country":
            raise ValueError(f"Intestazione non valida: {path.name}")
        countries = [x.strip() for x in header[1:]]
        if not countries or len(set(countries)) != len(countries):
            raise ValueError(f"Paesi duplicati: {path.name}")
        rows = {}
        for row in reader:
            if len(row) != len(header) or row[0].strip() in rows:
                raise ValueError(f"Riga errata o ripetuta: {path.name}")
            rows[row[0].strip()] = row[1:]
    if set(rows) != set(countries):
        raise ValueError(f"Le righe non coincidono con le colonne: {path.name}")
    n = len(countries)
    W = np.zeros((n, n), dtype=np.int16)
    eligible = np.zeros((n, n), dtype=bool)
    for i, source in enumerate(countries):
        for j, raw in enumerate(rows[source]):
            if not raw.strip():
                continue
            try:
                points = int(raw)
            except ValueError as exc:
                raise ValueError(f"Punteggio non intero {source}->{countries[j]}") from exc
            if points not in VALID or i == j:
                raise ValueError(f"Voto non valido {source}->{countries[j]}={points}")
            eligible[i, j] = True
            W[i, j] = points
        if not np.array_equal(np.sort(W[i, W[i] > 0]), BALLOT):
            raise ValueError(f"Scheda di voto incompleta per {source}: {path.name}")
    finalists = eligible.any(axis=0)
    expected_mask = finalists[None, :] & ~np.eye(n, dtype=bool)
    if not np.array_equal(eligible, expected_mask):
        raise ValueError(f"Maschera opportunita di voto non valida: {path.name}")
    return W, eligible, countries, finalists


def triad_triplets(n: int):
    return np.array(list(combinations(range(n), 3)), dtype=np.int32).T


def score_metrics(W: np.ndarray, triples: np.ndarray, include_exact: bool = True) -> dict[str, float]:
    """Calcola anche i cicli/chiusure contenuti in triadi con archi ulteriori."""
    W = W.astype(np.float64, copy=False)
    A = W > 0
    m = int(A.sum())
    total = W.sum()
    result = {}
    result["binary_reciprocity"] = float((A & A.T).sum() / m) if m else np.nan
    result["weighted_reciprocity"] = float(np.minimum(W, W.T).sum() / total) if total else np.nan
    for threshold in (8, 10):
        H = W >= threshold
        h = int(H.sum())
        result[f"edges_ge{threshold}"] = h
        result[f"reciprocated_edges_ge{threshold}"] = int((H & H.T).sum())
        result[f"reciprocity_ge{threshold}"] = float((H & H.T).sum() / h) if h else np.nan

    # Percorsi ordinati i->j->k con nodi distinti; i->k chiude la struttura.
    # La doppia somma include strutture che hanno archi aggiuntivi.
    paths = 0
    closed = 0
    path_weight_total = 0.0
    weighted_closed_strength = 0.0
    transitive_geo_total = 0.0
    for j in range(len(W)):
        incoming = np.flatnonzero(A[:, j])
        outgoing = np.flatnonzero(A[j, :])
        if not len(incoming) or not len(outgoing):
            continue
        ii, kk = np.meshgrid(incoming, outgoing, indexing="ij")
        ii, kk = ii.ravel(), kk.ravel()
        keep = ii != kk
        ii, kk = ii[keep], kk[keep]
        if len(ii) == 0:
            continue
        p = np.sqrt(W[ii, j] * W[j, kk])
        closing = W[ii, kk]
        paths += len(ii)
        closed += int(np.count_nonzero(closing))
        path_weight_total += float(p.sum())
        weighted_closed_strength += float(np.dot(p, closing / 12.0))
        transitive_geo_total += float(np.cbrt(W[ii, j] * W[j, kk] * closing).sum())

    result["two_paths"] = paths
    result["closed_paths"] = closed
    result["directed_transitive_closure"] = closed / paths if paths else np.nan
    result["weighted_closure"] = weighted_closed_strength / path_weight_total if path_weight_total else np.nan
    result["all_transitive_motif_count"] = closed
    result["all_transitive_motif_intensity"] = transitive_geo_total / closed if closed else np.nan
    # Normalizzazione sul numero di opportunita di percorso: zero se non chiuso.
    result["all_transitive_motif_density_weighted"] = transitive_geo_total / (12.0 * paths) if paths else np.nan

    i, j, k = triples
    a, b = A[i, j], A[j, i]
    c, d = A[i, k], A[k, i]
    e, f = A[j, k], A[k, j]
    cnt = a.astype(np.int16) + b + c + d + e + f
    asymmetric = (cnt == 3) & ~(a & b) & ~(c & d) & ~(e & f)
    cycles_exact = (a & e & d) | (b & c & f)
    exact_c = asymmetric & cycles_exact
    exact_t = asymmetric & ~cycles_exact
    result["triads_030C"] = int(exact_c.sum())
    result["triads_030T"] = int(exact_t.sum())

    # Intensita di triadi ESATTE per confronto con il vecchio script.
    if include_exact:
        triad_geo = {}
        for kind, mask in (("030T", exact_t), ("030C", exact_c)):
            inds = np.flatnonzero(mask)
            values = []
            for idx in inds:
                nodes = (int(i[idx]), int(j[idx]), int(k[idx]))
                small = W[np.ix_(nodes, nodes)]
                values.append(float(np.cbrt(np.prod(small[small > 0]))))
            arr = np.asarray(values, dtype=float)
            triad_geo[kind] = (len(arr), float(arr.mean()) if len(arr) else np.nan,
                               float(arr.sum()))
        result["exact_triad_details"] = triad_geo

    # Cicli A->B->C->A: entrambi gli orientamenti possibili per ogni terna
    # non ordinata. Ogni ciclo orientato e contato una volta sola.
    cw1 = W[i, j] * W[j, k] * W[k, i]
    cw2 = W[i, k] * W[k, j] * W[j, i]
    # Prodotti <= 12**3, nessun overflow: W e' float64.
    cycles = np.concatenate((np.cbrt(cw1[cw1 > 0]), np.cbrt(cw2[cw2 > 0])))
    result["all_cycle_count"] = int(len(cycles))
    result["all_cycle_motif_intensity"] = float(cycles.mean()) if len(cycles) else np.nan
    result["all_cycle_motif_total_intensity"] = float(cycles.sum())
    return result


def census(W: np.ndarray):
    graph = nx.from_numpy_array((W > 0).astype(np.int8), create_using=nx.DiGraph)
    return nx.triadic_census(graph)


def draw_lines(rows: list[dict], specs, filename: str, title: str):
    by_key = {(r["year"], r["layer"]): r for r in rows}
    fig, axs = plt.subplots(1, len(specs), figsize=(5.5 * len(specs), 4.6))
    axes = np.atleast_1d(axs)
    for ax, (field, name, ymax) in zip(axes, specs):
        for layer in LAYERS:
            values = [by_key[y, layer][field] for y in YEARS]
            ax.plot(YEARS, values, marker="o", label="Giurie" if layer == "jury" else "Televoto",
                    color=COLORS[layer], linewidth=2)
        ax.set_title(name)
        ax.set_xticks(YEARS[::2])
        ax.set_xlabel("Edizione")
        if ymax is not None:
            ax.set_ylim(0, ymax)
        ax.grid(alpha=0.2)
    axes[0].legend(frameon=False)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(FIGURES / filename, dpi=180)
    plt.close(fig)


def random_ballots(mask: np.ndarray, rng: np.random.Generator):
    n = len(mask)
    W = np.zeros((n, n), dtype=np.int16)
    for source in range(n):
        candidates = np.flatnonzero(mask[source])
        if len(candidates) < 10:
            raise ValueError("Meno di 10 destinatari per una scheda casuale")
        chosen = rng.choice(candidates, size=10, replace=False)
        W[source, chosen] = rng.permutation(BALLOT)
    return W


def compare_null(observed: float, simulated: np.ndarray):
    simulated = simulated[np.isfinite(simulated)]
    if len(simulated) < 2 or not np.isfinite(observed):
        return [observed, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
    mean = float(simulated.mean())
    sd = float(simulated.std(ddof=1))
    z = (observed - mean) / sd if sd > 0 else np.nan
    high = (1 + np.count_nonzero(simulated >= observed)) / (len(simulated) + 1)
    low = (1 + np.count_nonzero(simulated <= observed)) / (len(simulated) + 1)
    two = (1 + np.count_nonzero(np.abs(simulated - mean) >= abs(observed - mean))) / (len(simulated) + 1)
    return [observed, mean, sd, float(np.quantile(simulated, 0.025)),
            float(np.quantile(simulated, 0.975)), z, high, low, two]


def finite_mean(values):
    a = np.asarray(values, dtype=float)
    return float(np.nanmean(a)) if np.isfinite(a).any() else np.nan


def main():
    parser = argparse.ArgumentParser(description="RQ1 completa: analisi binarie, pesate e modelli nulli")
    parser.add_argument("--simulations", type=int, default=1000,
                        help="Repliche nulle per rete, 0 = solo analisi descrittiva (default 1000)")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    if args.simulations < 0:
        parser.error("Il numero di simulazioni non puo essere negativo")
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    rows = []
    census_rows = []
    exact_rows = []
    observed = {}
    simulated = {}
    for year in YEARS:
        reference = None
        for layer in LAYERS:
            W, eligible, countries, finalists = read_matrix(MATRICES / f"{year}_{layer}.csv")
            if reference is None:
                reference = (countries, eligible.copy())
            elif countries != reference[0] or not np.array_equal(eligible, reference[1]):
                raise ValueError(f"{year}: le opportunita di voto jury/public non coincidono")
            indices = np.flatnonzero(finalists)
            WF = W[np.ix_(indices, indices)]
            maskF = eligible[np.ix_(indices, indices)]
            triples = triad_triplets(len(indices))
            stats = score_metrics(WF, triples)
            # Reciprocita sulla rete completa, senza calcolare inutilmente le triadi.
            full_A = W > 0
            full_binary = float((full_A & full_A.T).sum() / full_A.sum())
            full_weighted = float(np.minimum(W, W.T).sum() / W.sum())
            row = {"year": year, "layer": layer, "nodes": len(countries),
                   "finalists": len(indices), "positive_edges_full": int(full_A.sum()),
                   "positive_edges_finalists": int((WF > 0).sum()),
                   "binary_reciprocity_full": full_binary,
                   "binary_reciprocity_finalists": stats["binary_reciprocity"],
                   "weighted_reciprocity_full": full_weighted,
                   "weighted_reciprocity_finalists": stats["weighted_reciprocity"],
                   "directed_two_paths_finalists": stats["two_paths"],
                   "closed_two_paths_finalists": stats["closed_paths"],
                   "directed_transitive_closure_finalists": stats["directed_transitive_closure"],
                   "triads_030T_finalists": stats["triads_030T"],
                   "triads_030C_finalists": stats["triads_030C"],
                   "edges_ge8": stats["edges_ge8"],
                   "reciprocated_edges_ge8": stats["reciprocated_edges_ge8"],
                   "reciprocity_ge8": stats["reciprocity_ge8"],
                   "edges_ge10": stats["edges_ge10"],
                   "reciprocated_edges_ge10": stats["reciprocated_edges_ge10"],
                   "reciprocity_ge10": stats["reciprocity_ge10"],
                   "weighted_closure": stats["weighted_closure"],
                   "all_transitive_motif_count": stats["all_transitive_motif_count"],
                   "all_transitive_motif_intensity": stats["all_transitive_motif_intensity"],
                   "all_transitive_motif_density_weighted": stats["all_transitive_motif_density_weighted"],
                   "all_cycle_count": stats["all_cycle_count"],
                   "all_cycle_motif_intensity": stats["all_cycle_motif_intensity"],
                   "all_cycle_motif_total_intensity": stats["all_cycle_motif_total_intensity"]}
            rows.append(row)
            for kind, count in census(WF).items():
                census_rows.append([year, layer, kind, count])
            for kind, (count, intensity, total) in stats["exact_triad_details"].items():
                exact_rows.append([year, layer, kind, count, intensity, total])
            observed[year, layer] = {metric: float(stats[metric]) for metric in NULL_METRICS}

            if args.simulations:
                trials = np.empty((args.simulations, len(NULL_METRICS)), dtype=np.float64)
                for sim in range(args.simulations):
                    # La scheda include i votanti non finalisti, come nel vero voto.
                    # Poi restringiamo alle reti dei finalisti per le metriche RQ1.
                    random_W = random_ballots(eligible, rng)
                    random_F = random_W[np.ix_(indices, indices)]
                    trial_stats = score_metrics(random_F, triples, include_exact=False)
                    trials[sim, :] = [trial_stats[m] for m in NULL_METRICS]
                simulated[year, layer] = trials
        print(f"{year}: giurie e televoto completati" + (f" ({args.simulations} simulazioni ciascuno)" if args.simulations else ""), flush=True)

    # La struttura di rq1_metrics.csv resta identica alla vecchia per confronto.
    old_fields = ["year", "layer", "nodes", "finalists", "positive_edges_full",
                  "positive_edges_finalists", "binary_reciprocity_full",
                  "binary_reciprocity_finalists", "weighted_reciprocity_full",
                  "weighted_reciprocity_finalists", "directed_two_paths_finalists",
                  "closed_two_paths_finalists", "directed_transitive_closure_finalists",
                  "triads_030T_finalists", "triads_030C_finalists"]
    write_csv(RESULTS / "rq1_metrics.csv", old_fields,
              [[row[x] for x in old_fields] for row in rows])
    write_csv(RESULTS / "rq1_triad_census.csv", ["year", "layer", "triad_type", "count"], census_rows)
    extended_fields = [x for x in rows[0] if x not in old_fields]
    write_csv(RESULTS / "rq1_all_metrics.csv", old_fields + extended_fields,
              [[row[x] for x in old_fields + extended_fields] for row in rows])
    write_csv(RESULTS / "rq1_all_triad_intensity.csv",
              ["year", "layer", "triad_type", "count", "mean_geometric_intensity", "sum_geometric_intensity"], exact_rows)

    # Mantiene anche i due vecchi CSV delle analisi pesate per confronti immediati.
    write_csv(RESULTS / "rq1_weighted_extensions.csv", [
        "year", "layer", "finalists", "binary_reciprocity_finalists", "edges_ge8",
        "reciprocated_edges_ge8", "reciprocity_ge8", "edges_ge10",
        "reciprocated_edges_ge10", "reciprocity_ge10", "two_paths", "closed_paths",
        "binary_closure", "weighted_closure"], [[r[x] for x in [
        "year", "layer", "finalists", "binary_reciprocity_finalists", "edges_ge8",
        "reciprocated_edges_ge8", "reciprocity_ge8", "edges_ge10",
        "reciprocated_edges_ge10", "reciprocity_ge10", "directed_two_paths_finalists",
        "closed_two_paths_finalists", "directed_transitive_closure_finalists", "weighted_closure"]]
        for r in rows])
    write_csv(RESULTS / "rq1_weighted_triads.csv",
              ["year", "layer", "triad_type", "count", "mean_geometric_intensity", "sum_geometric_intensity"], exact_rows)

    draw_lines(rows, [("binary_reciprocity_finalists", "Reciprocita binaria", 1),
                      ("weighted_reciprocity_finalists", "Reciprocita pesata", 1),
                      ("directed_transitive_closure_finalists", "Chiusura transitiva", 1)],
               "rq1_metrics_by_year.png", "RQ1: giurie vs televoto — soli finalisti")
    draw_lines(rows, [("reciprocity_ge8", "Reciprocita voti >=8", 1),
                      ("reciprocity_ge10", "Reciprocita voti >=10", 1),
                      ("weighted_closure", "Chiusura transitiva pesata", 1)],
               "rq1_weighted_extensions.png", "RQ1: intensita del voto")
    draw_lines(rows, [("all_transitive_motif_intensity", "Intensita chiusure transitive", 12),
                      ("all_cycle_motif_intensity", "Intensita cicli diretti", 12),
                      ("all_cycle_count", "Numero di cicli", None)],
               "rq1_all_motifs.png", "RQ1: tutte le strutture (anche con archi aggiuntivi)")
    draw_lines(rows, [("triads_030T_finalists", "Triadi esatte 030T", None),
                      ("triads_030C_finalists", "Triadi esatte 030C", None)],
               "rq1_triad_counts.png", "RQ1: censimento triadi esatte")

    if args.simulations:
        null_columns = ["observed", "null_mean", "null_sd", "null_q025", "null_q975",
                        "z_score", "p_high", "p_low", "p_two_sided"]
        null_rows = []
        for year in YEARS:
            for layer in LAYERS:
                for m_index, metric in enumerate(NULL_METRICS):
                    null_rows.append([year, layer, metric] + compare_null(
                        observed[year, layer][metric], simulated[year, layer][:, m_index]))
        write_csv(RESULTS / "rq1_null_model.csv", ["year", "layer", "metric"] + null_columns, null_rows)

        delta_rows = []
        for year in (*YEARS, "ALL_YEARS_MEAN"):
            for m_index, metric in enumerate(NULL_METRICS):
                if year == "ALL_YEARS_MEAN":
                    actual = finite_mean([observed[y, "public"][metric] - observed[y, "jury"][metric] for y in YEARS])
                    sims = np.nanmean(np.stack([
                        simulated[y, "public"][:, m_index] - simulated[y, "jury"][:, m_index]
                        for y in YEARS], axis=0), axis=0)
                else:
                    actual = observed[year, "public"][metric] - observed[year, "jury"][metric]
                    sims = simulated[year, "public"][:, m_index] - simulated[year, "jury"][:, m_index]
                delta_rows.append([year, metric] + compare_null(actual, sims))
        write_csv(RESULTS / "rq1_null_layer_differences.csv",
                  ["year", "metric"] + null_columns, delta_rows)
        # Grafico osservato / nullo per le tre metriche principali.
        wanted = [("binary_reciprocity", "Reciprocita binaria"),
                  ("directed_transitive_closure", "Chiusura transitiva"),
                  ("weighted_closure", "Chiusura pesata")]
        fig, axes = plt.subplots(1, len(wanted), figsize=(16, 4.5))
        for ax, (metric, label) in zip(axes, wanted):
            idx = NULL_METRICS.index(metric)
            for layer in LAYERS:
                obs_y = [observed[y, layer][metric] for y in YEARS]
                nul_y = [float(np.nanmean(simulated[y, layer][:, idx])) for y in YEARS]
                ax.plot(YEARS, obs_y, marker="o", label=f"{layer} osservato", color=COLORS[layer])
                ax.plot(YEARS, nul_y, linestyle="--", label=f"{layer} nullo", color=COLORS[layer], alpha=.65)
            ax.set_title(label)
            ax.set_xticks(YEARS[::2])
            ax.grid(alpha=.2)
        axes[0].legend(fontsize=8)
        fig.suptitle("RQ1: dati osservati e modello casuale conforme al regolamento")
        fig.tight_layout()
        fig.savefig(FIGURES / "rq1_null_model_comparison.png", dpi=180)
        plt.close(fig)

    print(f"Reti analizzate: {len(rows)}", flush=True)
    print(f"CSV: {RESULTS}", flush=True)
    print(f"Grafici: {FIGURES}", flush=True)
    print("ATTENZIONE: il modello nullo non controlla popolarita, dipendenza temporale o test multipli.")
    print("Le misure 'all_' includono cicli e chiusure anche in triadi con archi aggiuntivi.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, nx.NetworkXException) as error:
        raise SystemExit(f"RQ1 fallita: {error}") from error
