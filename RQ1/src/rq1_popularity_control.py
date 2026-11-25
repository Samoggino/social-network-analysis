#!/usr/bin/env python3
"""RQ1 - modello nullo degree-preserving.

Riferimento metodologico: appunti Social Network Analysis, capitoli
Research Design / Validity & Reliability, Testing Hypotheses (Permutation
Tests, Whole-network Hypotheses), Data Management e Network Metrics.

Ipotesi nulla CONDIZIONATA: fissati opportunita di voto, identita dei finalisti,
out-degree positivi dei votanti e in-degree positivo dei destinatari (separato
per votanti finalisti e non finalisti), le associazioni votante-destinatario
vengono randomizzate mediante scambi ammissibili. I 10 punteggi Eurovision
rimangono per ogni votante, ma NON si preserva l'in-strength dei destinatari.

La catena di Markov campiona solo la componente di stati raggiungibile dagli
scambi: l'uniformita sull'intero spazio delle reti ammissibili non e dimostrata.
I p-value sono dunque esplorativi e subordinati ai controlli di convergenza.
Gli anni non sono un campione casuale indipendente: i test ALL_YEARS_MEAN
sono test condizionati alle edizioni esaminate, non inferenza causale o
predizione generale su future edizioni.

Esempi:
    py src/rq1_popularity_control.py --simulations 120 --chains 4
    py src/rq1_popularity_control.py --simulations 400 --chains 4 --burnin-per-edge 15 --thin-per-edge 4
    py src/rq1_popularity_control.py --simulations 400 --chains 4 --seed 47 --burnin-per-edge 25 --thin-per-edge 6

I risultati usano il prefisso rq1_popularity_robust_.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from analyze_rq1 import YEARS, LAYERS, MATRICES, RESULTS, FIGURES, read_matrix, triad_triplets, score_metrics

# Piccolo nucleo di metriche: si evita di trattare troppe ipotesi esplorative
# come se fossero tutte pre-specificate.
METRICS = (
    'binary_reciprocity',
    'weighted_reciprocity',
    'reciprocity_ge10',
    'directed_transitive_closure',
    'weighted_closure',
    'all_transitive_motif_count',
    'all_transitive_motif_intensity',
    'all_cycle_count',
    'all_cycle_motif_intensity',
    'triads_030T',
    'triads_030C',
)
PRIMARY = ('reciprocity_ge10', 'directed_transitive_closure', 'weighted_closure')


def write_csv(path: Path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as fh:
        wr = csv.writer(fh)
        wr.writerow(cols)
        wr.writerows(rows)


def initialize_chain(W, eligible, finalists):
    """Copia matrici; non modifica mai i dati originali."""
    return {
        'W': W.copy(),
        'eligible': eligible,
        'group': [np.flatnonzero(finalists), np.flatnonzero(~finalists)],
        'targets': [np.flatnonzero(W[i] > 0).copy() for i in range(len(W))],
        'success': 0, 'attempts': 0,
    }


def swap_steps(chain, target, rng, max_attempt_factor):
    """Due switch reversibili, bilancio dei gradi conservato per categoria.

    Un tentativo sceglie un gruppo, due votanti distinti e un voto positivo
    di ciascuno. Se lo swap e valido si accetta; altrimenti la catena resta
    nello stesso stato (self-loop). La proposta inversa ha stessa probabilita
    a condizione che non cambino i gradi, quindi la transizione e simmetrica.
    Non segue che l'intero spazio ammissibile sia necessariamente connesso.
    """
    groups = [g for g in chain['group'] if len(g) >= 2]
    if not groups:
        raise RuntimeError('Meno di due votanti per gruppo: impossibile effettuare scambi')
    W, eligible, targets = chain['W'], chain['eligible'], chain['targets']
    succeeded = 0
    attempts = 0
    limit = max(1, int(max_attempt_factor * target))
    while succeeded < target and attempts < limit:
        attempts += 1
        g = groups[int(rng.integers(len(groups)))]
        ai = int(rng.integers(len(g)))
        bi = int(rng.integers(len(g) - 1))
        if bi >= ai:
            bi += 1
        a, b = int(g[ai]), int(g[bi])
        ka = int(rng.integers(len(targets[a])))
        kb = int(rng.integers(len(targets[b])))
        x, y = int(targets[a][ka]), int(targets[b][kb])
        if x == y or not eligible[a, y] or not eligible[b, x] or W[a, y] or W[b, x]:
            continue
        pa, pb = int(W[a, x]), int(W[b, y])
        W[a, x] = 0
        W[b, y] = 0
        W[a, y] = pa
        W[b, x] = pb
        targets[a][ka], targets[b][kb] = y, x
        succeeded += 1
    chain['success'] += succeeded
    chain['attempts'] += attempts
    if succeeded < target:
        raise RuntimeError(f'Solo {succeeded}/{target} swap riusciti in {attempts} tentativi; '
                           'controllare ammissibilita/matrice o aumentare --max-attempt-factor')


def verify_state(original, trial, eligible, finalists):
    if np.any(trial[~eligible] != 0):
        raise AssertionError('Archi non ammissibili introdotti')
    if not np.array_equal(np.sort(trial, axis=1), np.sort(original, axis=1)):
        raise AssertionError('Schede Eurovision alterate')
    if not np.array_equal(np.count_nonzero(trial, axis=0), np.count_nonzero(original, axis=0)):
        raise AssertionError('In-degree totale non preservato')
    if not np.array_equal(np.count_nonzero(trial[finalists], axis=0),
                          np.count_nonzero(original[finalists], axis=0)):
        raise AssertionError('In-degree da finalisti non preservato')
    if not np.array_equal(np.count_nonzero(trial[~finalists], axis=0),
                          np.count_nonzero(original[~finalists], axis=0)):
        raise AssertionError('In-degree da non finalisti non preservato')


def rhat(chains):
    """Gelman-Rubin R-hat classico: diagnostica descrittiva, non prova di convergenza."""
    x = np.asarray(chains, dtype=float)
    if x.ndim != 2 or min(x.shape) < 2 or not np.isfinite(x).all():
        return np.nan
    m, n = x.shape
    within = np.mean(np.var(x, axis=1, ddof=1))
    between = n * np.var(np.mean(x, axis=1), ddof=1)
    if within == 0:
        return 1.0 if between == 0 else np.inf
    varhat = (n - 1) / n * within + between / n
    return float(np.sqrt(varhat / within))


def lag1(chains):
    """Autocorrelazione al primo lag delle serie, media sulle catene."""
    values = []
    for x in np.asarray(chains, dtype=float):
        if len(x) < 3 or not np.isfinite(x).all():
            continue
        a, b = x[:-1], x[1:]
        if np.std(a) <= 1e-12 or np.std(b) <= 1e-12:
            continue
        values.append(float(np.corrcoef(a, b)[0, 1]))
    return float(np.mean(values)) if values else np.nan


def stats(obs, sim):
    """Test MC con correzione +1. Bilaterale centrato sulla media nulla.

    Il p-value bilaterale e di tipo Monte Carlo descrittivo; il suo valore
    dipende dalla stima della media nulla e dall'adeguatezza del sampler.
    """
    x = np.asarray(sim, dtype=float)
    x = x[np.isfinite(x)]
    if not np.isfinite(obs) or len(x) < 2:
        return [obs] + [np.nan] * 8 + [len(x)]
    mu = float(np.mean(x))
    sd = float(np.std(x, ddof=1))
    z = (obs - mu) / sd if sd > 0 else np.nan
    high = (1 + np.count_nonzero(x >= obs)) / (len(x) + 1)
    low = (1 + np.count_nonzero(x <= obs)) / (len(x) + 1)
    two = (1 + np.count_nonzero(np.abs(x - mu) >= abs(obs - mu))) / (len(x) + 1)
    return [obs, mu, sd, float(np.quantile(x, .025)), float(np.quantile(x, .975)),
            z, high, low, two, len(x)]


def adjust_p(values, method):
    """Correzioni su famiglia predefinita di test, NaN esclusi."""
    p = np.asarray(values, dtype=float)
    out = np.full(len(p), np.nan)
    ix = np.flatnonzero(np.isfinite(p))
    if not len(ix):
        return out
    order = ix[np.argsort(p[ix])]
    ps = p[order]
    m = len(ps)
    if method == 'holm':
        adj = np.maximum.accumulate((m - np.arange(m)) * ps)
    elif method == 'bh':
        adj = np.minimum.accumulate((ps * m / (np.arange(m) + 1))[::-1])[::-1]
    else:
        raise ValueError('Metodo di correzione sconosciuto')
    out[order] = np.minimum(1., adj)
    return out


def main():
    parser = argparse.ArgumentParser(description='RQ1 modello nullo robusto a in-degree fissati')
    parser.add_argument('--simulations', type=int, default=120, help='Repliche TOTALI per rete (multiplo di --chains)')
    parser.add_argument('--chains', type=int, default=4, help='Catene indipendenti per rete (default 4)')
    parser.add_argument('--burnin-per-edge', type=float, default=12., help='Swap riusciti iniziali per arco e catena')
    parser.add_argument('--thin-per-edge', type=float, default=3., help='Swap riusciti fra due campioni della catena')
    parser.add_argument('--max-attempt-factor', type=int, default=80)
    parser.add_argument('--seed', type=int, default=20261118)
    parser.add_argument('--rhat-threshold', type=float, default=1.1)
    parser.add_argument('--lag1-threshold', type=float, default=0.3)
    args = parser.parse_args()
    if args.chains < 2 or args.simulations < 2 * args.chains or args.simulations % args.chains:
        parser.error('Occorrono almeno 2 catene e >=2 campioni per catena; --simulations multiplo di --chains')
    if min(args.burnin_per_edge, args.thin_per_edge) <= 0 or args.max_attempt_factor <= 0:
        parser.error('Burn-in, thinning e tentativi devono essere positivi')

    per_chain = args.simulations // args.chains
    seed_sequence = np.random.SeedSequence(args.seed)
    child_seeds = iter(seed_sequence.spawn(len(YEARS) * len(LAYERS) * args.chains))
    FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    observed, simulated, chain_stats = {}, {}, {}
    diag_rows = []
    for year in YEARS:
        year_mask = None
        for layer in LAYERS:
            W, eligible, countries, finalists = read_matrix(MATRICES / f'{year}_{layer}.csv')
            if year_mask is None:
                year_mask = (countries, eligible.copy())
            elif countries != year_mask[0] or not np.array_equal(eligible, year_mask[1]):
                raise ValueError(f'{year}: votanti o opportunita diverse fra jury e public')
            fi = np.flatnonzero(finalists)
            triples = triad_triplets(len(fi))
            obs_stat = score_metrics(W[np.ix_(fi, fi)], triples, include_exact=False)
            observed[year, layer] = np.asarray([obs_stat[k] for k in METRICS], dtype=float)
            edges = int(np.count_nonzero(W))
            burn = max(1, int(round(edges * args.burnin_per_edge)))
            thin = max(1, int(round(edges * args.thin_per_edge)))
            chains_data = np.empty((args.chains, per_chain, len(METRICS)))
            changed, acceptance = [], []
            for c in range(args.chains):
                rng = np.random.default_rng(next(child_seeds))
                chain = initialize_chain(W, eligible, finalists)
                swap_steps(chain, burn, rng, args.max_attempt_factor)
                verify_state(W, chain['W'], eligible, finalists)
                for t in range(per_chain):
                    swap_steps(chain, thin, rng, args.max_attempt_factor)
                    verify_state(W, chain['W'], eligible, finalists)
                    m = score_metrics(chain['W'][np.ix_(fi, fi)], triples, include_exact=False)
                    chains_data[c, t] = [m[k] for k in METRICS]
                    changed.append(np.count_nonzero((chain['W'] > 0) != (W > 0)) / max(1, 2 * edges))
                acceptance.append(chain['success'] / chain['attempts'])
            simulated[year, layer] = chains_data.reshape(-1, len(METRICS))
            chain_stats[year, layer] = chains_data
            for j, k in enumerate(METRICS):
                rh, ac = rhat(chains_data[:, :, j]), lag1(chains_data[:, :, j])
                status = ('UNDEFINED' if not np.isfinite(rh) else
                          'CHECK' if rh > args.rhat_threshold or (np.isfinite(ac) and ac > args.lag1_threshold) else 'OK')
                diag_rows.append([year, layer, k, args.chains, per_chain, burn, thin,
                                  round(float(np.mean(acceptance)), 5), round(float(np.mean(changed)), 5),
                                  rh, ac, status])
        print(f'{year}: 2 livelli completati, {args.simulations} campioni/rete, {args.chains} catene', flush=True)

    headings = ['observed', 'null_mean', 'null_sd', 'null_q025', 'null_q975',
                'z_score', 'p_high', 'p_low', 'p_two_sided', 'valid_simulations']
    details = []
    for year in YEARS:
        for layer in LAYERS:
            for j, metric in enumerate(METRICS):
                details.append([year, layer, metric] + stats(observed[year, layer][j], simulated[year, layer][:, j]))
    write_csv(RESULTS / 'rq1_popularity_robust_null_model.csv',
              ['year', 'layer', 'metric'] + headings, details)

    comparisons = []
    for year in [*YEARS, 'ALL_YEARS_MEAN']:
        for j, metric in enumerate(METRICS):
            if year != 'ALL_YEARS_MEAN':
                obs = float(observed[year, 'public'][j] - observed[year, 'jury'][j])
                null = simulated[year, 'public'][:, j] - simulated[year, 'jury'][:, j]
                n_years = 1
            else:
                # Le edizioni vengono considerate condizioni fisse.
                # Medie solo su edizioni con statistiche osservate definite
                # per entrambi i livelli; non si presume indipendenza storica.
                valid_years = [y for y in YEARS if np.isfinite(observed[y, 'public'][j])
                               and np.isfinite(observed[y, 'jury'][j])]
                n_years = len(valid_years)
                if not valid_years:
                    obs, null = np.nan, np.array([])
                else:
                    obs = float(np.mean([observed[y, 'public'][j] - observed[y, 'jury'][j]
                                         for y in valid_years]))
                    null = np.mean(np.stack([
                        simulated[y, 'public'][:, j] - simulated[y, 'jury'][:, j]
                        for y in valid_years], axis=0), axis=0)
            comparisons.append([year, metric, n_years] + stats(obs, null))

    overall = [i for i, r in enumerate(comparisons) if r[0] == 'ALL_YEARS_MEAN']
    overall_p = [comparisons[i][-2] for i in overall]  # ultimo = n, penultimo = p_two_sided
    holm = adjust_p(overall_p, 'holm')
    fdr = adjust_p(overall_p, 'bh')
    adjusted = {idx: (float(holm[k]), float(fdr[k])) for k, idx in enumerate(overall)}
    difference_rows = []
    for i, row in enumerate(comparisons):
        h, f = adjusted.get(i, (np.nan, np.nan))
        difference_rows.append(row + [h, f, 'PRIMARY' if row[1] in PRIMARY else 'EXPLORATORY'])
    write_csv(RESULTS / 'rq1_popularity_robust_layer_differences.csv',
              ['year', 'metric', 'n_years'] + headings + ['p_holm_all_metrics', 'p_fdr_bh_all_metrics', 'role'], difference_rows)
    write_csv(RESULTS / 'rq1_popularity_robust_diagnostics.csv',
              ['year', 'layer', 'metric', 'chains', 'samples_per_chain', 'burnin_swaps',
               'swaps_between_samples', 'acceptance_rate', 'fraction_edges_changed',
               'rhat', 'lag1_autocorrelation', 'status'], diag_rows)

    # Il config va scritto insieme ai CSV e PRIMA del grafico: se il salvataggio
    # del grafico fallisce, il JSON deve comunque descrivere i risultati salvati.
    config = vars(args) | {
        'years': YEARS, 'layers': LAYERS, 'metrics': METRICS, 'primary_metrics': PRIMARY,
        'null_preserves': ['voting eligibility', 'per-voter ballot points',
                           'recipient in-degree by finalist/non-finalist voter strata'],
        'null_does_not_preserve': ['recipient in-strength', 'country affinity',
                                   'historical dependencies'],
        'warnings': ['MCMC mixing diagnostics are not a proof of uniform sampling',
                     'p-values exploratory and conditional on observed contest years',
                     'metric selection is exploratory/post hoc'],
    }
    with (RESULTS / 'rq1_popularity_robust_run_config.json').open('w', encoding='utf-8') as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)

    spec = [('reciprocity_ge10', 'Reciprocita voti 10/12'),
            ('directed_transitive_closure', 'Chiusura transitiva binaria'),
            ('weighted_closure', 'Chiusura transitiva pesata')]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.4))
    for ax, (metric, title) in zip(axes, spec):
        j = METRICS.index(metric)
        for layer, color, label in [('jury', '#246b91', 'Giurie'), ('public', '#cf7135', 'Televoto')]:
            ax.plot(YEARS, [observed[y, layer][j] for y in YEARS], 'o-', color=color,
                    label=f'{label}: osservato')
            ax.plot(YEARS, [np.nanmean(simulated[y, layer][:, j]) for y in YEARS],
                    '--', color=color, alpha=.75, label=f'{label}: nullo')
        ax.set_title(title)
        ax.grid(alpha=.2)
        ax.set_xticks(YEARS[::2])
    axes[0].legend(fontsize=8)
    fig.suptitle('RQ1 - modello nullo condizionato all in-degree (verifiche MCMC)')
    fig.tight_layout()
    try:
        fig.savefig(FIGURES / 'rq1_popularity_robust_comparison.png', dpi=170)
    except OSError as exc:
        print(f'AVVISO: grafico non salvato ({exc}); CSV e JSON sono stati salvati.', flush=True)
    plt.close(fig)

    flagged = [r for r in diag_rows if r[-1] != 'OK']
    print(f'File nuovi in {RESULTS}; grafico in {FIGURES}', flush=True)
    print(f'Diagnostiche da ricontrollare: {len(flagged)}/{len(diag_rows)} (R-hat/lag-1)', flush=True)
    print('I p-value sono ESPLORATIVI: non controllano in-strength o dipendenza temporale.', flush=True)
    if flagged:
        print('ATTENZIONE: non interpretare come conclusivi i p-value con catene non convergenti.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, AssertionError) as exc:
        raise SystemExit(f'ERRORE nel controllo popolarita: {exc}') from exc
