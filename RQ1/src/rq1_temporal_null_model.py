#!/usr/bin/env python3
"""RQ1b — test Monte Carlo della PERSISTENZA temporale, con controllo in-degree.

Collocare in eurovision-sna/src/, accanto a:
  analyze_rq1.py, rq1_popularity_control.py, rq1_temporal_persistence_v2.py
Prima eseguire rq1_temporal_persistence_v2.py (produce i CSV descrittivi).

Esempi:
  py src/rq1_temporal_null_model.py --histories 20 --chains 4
  py src/rq1_temporal_null_model.py --histories 200 --chains 4 --burnin-per-edge 15 --thin-per-edge 4

Ipotesi nulla CONDIZIONATA: ogni anno e ogni livello e' randomizzato
indipendentemente mediante scambi di archi, preservando i votanti, i
finalisti, il numero di schede attribuite da ciascun votante e gli in-degree
per destinatario divisi per votanti finalisti/non finalisti. NON preserva
in-strength, affinità geografiche, dipendenze temporali, né una distribuzione
uniforme sullo spazio globale degli stati (non dimostrata).

I confronti principali sono GLOBALI: quante coppie (con >=3 opportunita')
sono sempre reciproche, quante sono reciproche almeno nel 75% e quante si
scambiano 10/12 punti in almeno due edizioni. Ulteriori metriche sui motivi
sono esplorative. Le opportunita' e gli zeri provengono dall'analisi corretta
RQ1b; ogni storia simulata usa una rete per ciascuna delle 20 combinazioni
(anno, livello) e la stessa lista di opportunita' dei dati osservati.

Dipendenze: numpy, networkx, matplotlib (installate dagli script precedenti).
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from analyze_rq1 import YEARS, LAYERS, MATRICES, RESULTS, FIGURES, read_matrix
from rq1_popularity_control import initialize_chain, swap_steps, verify_state, rhat, lag1, adjust_p

PAIRS = RESULTS / 'rq1_temporal_pairs.csv'
MOTIFS = RESULTS / 'rq1_temporal_motifs.csv'
PREFIX = 'rq1_temporal_null_'
METRICS = (
    'pairs_always_reciprocal', 'pairs_reciprocal_ge75', 'pairs_high_ge2',
    'cycles_always', 'cycles_ge75', 'transitive_always', 'transitive_ge75',
)
PRIMARY = METRICS[:3]


def read_rows(path):
    if not path.exists():
        raise FileNotFoundError(f'Manca {path}. Esegui prima rq1_temporal_persistence_v2.py')
    with path.open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def save_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def p_values(observed, simulated):
    v = np.asarray(simulated, dtype=float)
    mu = float(np.mean(v))
    sd = float(np.std(v, ddof=1)) if len(v) > 1 else float('nan')
    p_above = (1 + int(np.count_nonzero(v >= observed))) / (len(v) + 1)
    p_below = (1 + int(np.count_nonzero(v <= observed))) / (len(v) + 1)
    p_two = (1 + int(np.count_nonzero(np.abs(v - mu) >= abs(observed - mu) - 1e-12))) / (len(v) + 1)
    return (mu, sd, float(np.quantile(v, .025)), float(np.quantile(v, .975)),
            p_above, p_below, p_two)


def years_set(field):
    return set(int(s) for s in field.split(';') if s.strip())


@dataclass
class Schedule:
    year: int
    layer: str
    W: np.ndarray
    eligible: np.ndarray
    finalists: np.ndarray
    pair_ids: np.ndarray
    pair_i: np.ndarray
    pair_j: np.ndarray
    motif_ids: np.ndarray
    m1: np.ndarray
    m2: np.ndarray
    m3: np.ndarray
    edges: int


def build_schedule(pair_rows, motif_rows):
    """Precompila indici numpy per ogni anno: le valutazioni sono vettoriali."""
    pair_by_layer = {}
    motif_by_layer = {}
    for layer in LAYERS:
        pr = [r for r in pair_rows if r['layer'] == layer and int(r['opportunity_years']) >= 3]
        tr = [r for r in motif_rows if r['layer'] == layer and int(r['opportunity_years']) >= 3]
        pair_by_layer[layer] = pr
        motif_by_layer[layer] = tr

    schedules = {}
    for layer in LAYERS:
        pr = pair_by_layer[layer]
        tr = motif_by_layer[layer]
        for year in YEARS:
            W, eligible, countries, finalists = read_matrix(MATRICES / f'{year}_{layer}.csv')
            lookup = {c:i for i,c in enumerate(countries)}
            pids, pi, pj = [], [], []
            for index, row in enumerate(pr):
                if year not in years_set(row['years_eligible']):
                    continue
                a, b = row['country_a'], row['country_b']
                if a not in lookup or b not in lookup or not (finalists[lookup[a]] and finalists[lookup[b]]):
                    raise ValueError(f'Incongruenza opportunita coppia {year} {layer} {a}-{b}')
                pids.append(index); pi.append(lookup[a]); pj.append(lookup[b])
            tids, src1, src2, src3 = [], [], [], []
            for index, row in enumerate(tr):
                if year not in years_set(row['years_eligible']):
                    continue
                a,b,c = row['country_a'],row['country_b'],row['country_c']
                if not all(k in lookup and finalists[lookup[k]] for k in (a,b,c)):
                    raise ValueError(f'Incongruenza opportunita motivo {year} {layer} {a}-{b}-{c}')
                # Gli orientamenti sono quelli di rq1_temporal_persistence_v2.py.
                edges = ((a,b),(b,c),(c,a)) if row['motif']=='cycle' else ((a,b),(b,c),(a,c))
                tids.append(index)
                for target, (x,y) in zip((src1,src2,src3),edges):
                    target.append((lookup[x], lookup[y]))
            def pairindex(x):
                arr = np.asarray(x, dtype=int)
                return arr.reshape((-1, 2))
            schedules[year,layer] = Schedule(
                year,layer,W,eligible,finalists,
                np.asarray(pids,dtype=int), np.asarray(pi,dtype=int),np.asarray(pj,dtype=int),
                np.asarray(tids,dtype=int),pairindex(src1),pairindex(src2),pairindex(src3),
                int(np.count_nonzero(W)))
        print(f'Preparati {len(pr)} coppie e {len(tr)} motivi eleggibili (>=3 anni): {layer}',flush=True)
    return schedules,pair_by_layer,motif_by_layer


def stats_of_history(networks, schedules, pair_by_layer, motif_by_layer):
    """Una storia = 10 reti jury + 10 public; stessi denominatori storici."""
    result = {}
    for layer in LAYERS:
        prs = pair_by_layer[layer]
        trs = motif_by_layer[layer]
        p_binary = np.zeros(len(prs), dtype=np.int16)
        p_high = np.zeros(len(prs), dtype=np.int16)
        t_found = np.zeros(len(trs), dtype=np.int16)
        for year in YEARS:
            s = schedules[year,layer]
            W = networks[year,layer]
            if len(s.pair_ids):
                a = W[s.pair_i,s.pair_j]
                b = W[s.pair_j,s.pair_i]
                p_binary[s.pair_ids] += ((a>0)&(b>0)).astype(np.int16)
                p_high[s.pair_ids] += ((a>=10)&(b>=10)).astype(np.int16)
            if len(s.motif_ids):
                on = ((W[s.m1[:,0],s.m1[:,1]]>0) &
                      (W[s.m2[:,0],s.m2[:,1]]>0) &
                      (W[s.m3[:,0],s.m3[:,1]]>0))
                t_found[s.motif_ids] += on.astype(np.int16)
        opportunities_p = np.array([int(r['opportunity_years']) for r in prs])
        opportunities_t = np.array([int(r['opportunity_years']) for r in trs])
        cycle_mask = np.array([r['motif']=='cycle' for r in trs],dtype=bool)
        trans_mask = ~cycle_mask
        p_freq = p_binary/opportunities_p
        t_freq = t_found/opportunities_t
        result[layer] = np.array([
            int(np.count_nonzero(p_binary==opportunities_p)),
            int(np.count_nonzero(p_freq>=.75)),
            int(np.count_nonzero(p_high>=2)),
            int(np.count_nonzero(cycle_mask & (t_found==opportunities_t))),
            int(np.count_nonzero(cycle_mask & (t_freq>=.75))),
            int(np.count_nonzero(trans_mask & (t_found==opportunities_t))),
            int(np.count_nonzero(trans_mask & (t_freq>=.75))),
        ],dtype=float)
    return result


def check_observed(sums, rows):
    # Confronto obbligatorio contro il report RQ1b corretto: evita risultati errati silenziosi.
    lookup = {(r['layer'],r['unit']):r for r in rows}
    for layer in LAYERS:
        for j,key in enumerate(METRICS):
            unit = ('reciprocal_pair' if j<3 else 'cycle' if j<5 else 'transitive')
            row = lookup.get((layer,unit))
            if not row:
                raise ValueError(f'Manca voce summary per {layer} {unit}')
            if j in (0,3,5):
                expected = int(row['always_observed'])
            elif j in (1,4,6):
                expected = int(row['frequency_ge75pct'])
            else:
                continue  # numero di scambi massimi ripetuti: controllo sui CSV delle coppie
            if int(sums[layer][j])!=expected:
                raise AssertionError(f'{layer} {key}: calcolato {sums[layer][j]}, precedente {expected}')



def draw_publication_figure(simulated_differences, observed_differences):
    """Crea la figura del paper, senza alterare le statistiche."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    titles = (
        'Always-reciprocal dyads',
        'Reciprocal in >=75% of eligible editions',
        'Repeated reciprocal high-score dyads',
    )
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.7), constrained_layout=True)
    for j, ax in enumerate(axes):
        arr = np.asarray(simulated_differences[j], dtype=float)
        observed = float(observed_differences[j])
        if arr.size == 0 or not np.isfinite(arr).all():
            raise ValueError(f'Distribuzione nulla mancante per {PRIMARY[j]}')
        ax.hist(arr, bins=min(20, max(5, int(np.sqrt(len(arr))))),
                color='#90a9bd', edgecolor='white', label='Null distribution')
        ax.axvline(observed, color='#bf612e', lw=2.4, label='Observed difference')
        ax.axvline(float(arr.mean()), color='#335a78', lw=2, ls='--', label='Null mean')
        ax.set_title(titles[j], fontsize=11)
        ax.set_xlabel('Difference (public - jury)', fontsize=10)
        ax.set_ylabel('Frequency', fontsize=10)
        ax.grid(alpha=.15)
        ax.legend(fontsize=8, loc='upper left')
    for extension in ('png', 'pdf'):
        fig.savefig(FIGURES / (PREFIX + 'comparison.' + extension),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Figura aggiornata: {FIGURES / (PREFIX + "comparison.png")}', flush=True)


def plot_from_saved_csv():
    """Rigenera SOLO il grafico dai risultati gia salvati, senza nuove simulazioni."""
    histories_path = RESULTS / (PREFIX + 'simulated_histories.csv')
    differences_path = RESULTS / (PREFIX + 'layer_differences.csv')
    history_rows = read_rows(histories_path)
    difference_rows = read_rows(differences_path)
    observed_lookup = {row['statistic']: float(row['observed']) for row in difference_rows}
    histories = {}
    for row in history_rows:
        key = (row['chain'], row['history'])
        histories.setdefault(key, {})[row['layer']] = row
    paired_rows = [layers for layers in histories.values()
                   if 'jury' in layers and 'public' in layers]
    if not paired_rows:
        raise ValueError('Non sono presenti storie simulate appaiate nel CSV.')
    arrays = [np.asarray([float(pair['public'][metric]) - float(pair['jury'][metric])
                          for pair in paired_rows], dtype=float) for metric in PRIMARY]
    observed = [observed_lookup[metric] for metric in PRIMARY]
    draw_publication_figure(arrays, observed)


def main():
    parser = argparse.ArgumentParser(description='RQ1b: modello nullo TEMPORALE in-degree-preserving')
    parser.add_argument('--histories', type=int, default=80, help='Storie complete totali (multiplo di chains)')
    parser.add_argument('--chains', type=int, default=4)
    parser.add_argument('--burnin-per-edge', type=float, default=12.)
    parser.add_argument('--thin-per-edge', type=float, default=3.)
    parser.add_argument('--max-attempt-factor', type=int, default=80)
    parser.add_argument('--seed', type=int, default=20261118)
    parser.add_argument('--plot-only', action='store_true',
                        help='Rigenera solo PNG e PDF usando i CSV gia salvati')
    args = parser.parse_args()
    if args.plot_only:
        plot_from_saved_csv()
        return
    del args.plot_only
    if args.chains < 2 or args.histories < 2*args.chains or args.histories % args.chains:
        parser.error('--histories deve essere multiplo di --chains, con >=2 storie per catena')
    if min(args.burnin_per_edge,args.thin_per_edge)<=0:
        parser.error('Burn-in e thinning devono essere >0')

    pair_rows = read_rows(PAIRS)
    motif_rows = read_rows(MOTIFS)
    summary_rows = read_rows(RESULTS/'rq1_temporal_global_summary.csv')
    schedules,prs,trs = build_schedule(pair_rows,motif_rows)
    observed = stats_of_history({key:s.W for key,s in schedules.items()},schedules,prs,trs)
    check_observed(observed,summary_rows)
    print('Valori osservati: controllati contro rq1_temporal_global_summary.csv',flush=True)

    simulations = {layer:np.zeros((args.histories,len(METRICS))) for layer in LAYERS}
    chain_acceptance = []
    streams = np.random.SeedSequence(args.seed).spawn(args.chains*len(schedules))
    stream_idx = 0
    per_chain = args.histories//args.chains
    for chain_id in range(args.chains):
        chains = {}; randoms = {}
        for key,s in schedules.items():
            rng = np.random.default_rng(streams[stream_idx]); stream_idx+=1
            ch = initialize_chain(s.W,s.eligible,s.finalists)
            swap_steps(ch,max(1,round(s.edges*args.burnin_per_edge)),rng,args.max_attempt_factor)
            verify_state(s.W,ch['W'],s.eligible,s.finalists)
            chains[key] = ch; randoms[key] = rng
        for t in range(per_chain):
            for key,s in schedules.items():
                ch=chains[key]
                swap_steps(ch,max(1,round(s.edges*args.thin_per_edge)),randoms[key],args.max_attempt_factor)
                verify_state(s.W,ch['W'],s.eligible,s.finalists)
            story = stats_of_history({key:ch['W'] for key,ch in chains.items()},schedules,prs,trs)
            for layer in LAYERS:
                simulations[layer][chain_id*per_chain+t] = story[layer]
        chain_acceptance.append(float(np.mean([ch['success']/ch['attempts'] for ch in chains.values()])))
        print(f'Catena {chain_id+1}/{args.chains}: {per_chain} storie complete',flush=True)

    headers=['statistic','observed','null_mean','null_sd','null_q025','null_q975','p_high','p_low','p_two_sided',
             'p_holm_primary','p_bh_primary','role']
    rows=[]; comps=[]
    for j,k in enumerate(METRICS):
        a=float(observed['jury'][j]); b=float(observed['public'][j]);
        ad=simulations['jury'][:,j]; bd=simulations['public'][:,j]
        for layer,obs,sim in [('jury',a,ad),('public',b,bd)]:
            rows.append([layer,k,obs,*p_values(obs,sim)])
        diff=b-a; simulated_diff=bd-ad
        comps.append([k,diff,*p_values(diff,simulated_diff)])
    prim_p=[comps[j][-1] for j in range(len(PRIMARY))]
    corrected_holm=adjust_p(prim_p,'holm')
    corrected_bh=adjust_p(prim_p,'bh')
    for j,(k,obs,*st) in enumerate(comps):
        cols=([float(corrected_holm[j]),float(corrected_bh[j])] if j<len(PRIMARY) else ['', ''])
        rows_comp=comps[j]+cols+['PRIMARY_POST_HOC' if j<len(PRIMARY) else 'EXPLORATORY']
        comps[j]=rows_comp

    save_csv(RESULTS/(PREFIX+'per_layer.csv'),['layer']+headers[:-3], rows)
    save_csv(RESULTS/(PREFIX+'layer_differences.csv'),headers,comps)

    diag=[]
    for layer in LAYERS:
        for j,k in enumerate(METRICS):
            x=simulations[layer][:,j].reshape(args.chains,per_chain)
            diag.append([layer,k,rhat(x),lag1(x),args.chains,per_chain,
                         'LOW_SAMPLES' if per_chain<20 else 'CHECK' if not np.isfinite(rhat(x)) or rhat(x)>1.1 or (np.isfinite(lag1(x)) and abs(lag1(x))>.3) else 'OK'])
    save_csv(RESULTS/(PREFIX+'diagnostics.csv'),
             ['layer','metric','rhat','lag1_autocorrelation','chains','histories_per_chain','status'],diag)
    save_csv(RESULTS/(PREFIX+'simulated_histories.csv'),
             ['history','chain','layer']+list(METRICS),
             [[i+1,i//per_chain+1,layer]+list(map(float,simulations[layer][i]))
              for i in range(args.histories) for layer in LAYERS])
    config={**vars(args),'years':list(YEARS),'metrics':METRICS,'primary_metrics':PRIMARY,
            'per_chain':per_chain,'mean_chain_acceptance':float(np.mean(chain_acceptance)),
            'null_preserves':'annual eligibility; fixed voting ballots; recipient in-degree stratified by finalist status',
            'null_does_not_preserve':'recipient in-strength; historical dependence; cultural affinities',
            'method':'20 independent annual MCMC streams within each history; 4+ chains; pair/triad universes fixed by opportunity years',
            'warnings':['Null distribution only approximate; uniform sampling not proved',
                        'MCMC and multiple historical observations not equivalent to iid data',
                        'Three primary metrics were selected after inspecting data; adjusted p-values exploratory',
                        'Selected individual pairs must not be tested without correcting selection']}
    (RESULTS/(PREFIX+'config.json')).write_text(json.dumps(config,indent=2,ensure_ascii=False),encoding='utf-8')

    # Tutti i CSV sono gia stati salvati: la figura usa gli stessi campioni.
    try:
        arrays = [simulations['public'][:, j] - simulations['jury'][:, j]
                  for j in range(len(PRIMARY))]
        obs_differences = [observed['public'][j] - observed['jury'][j]
                           for j in range(len(PRIMARY))]
        draw_publication_figure(arrays, obs_differences)
    except OSError as exc:
        print(f'AVVISO: grafico non salvato ({exc}); CSV e JSON salvati.', flush=True)
    print('Output:',RESULTS,flush=True)
    print('I p-value sono esplorativi e condizionati al modello di in-degree; controllare le diagnostiche.',flush=True)


if __name__=='__main__':
    try:
        main()
    except (ValueError,FileNotFoundError,AssertionError,RuntimeError,OSError) as exc:
        raise SystemExit(f'ERRORE RQ1b modello nullo temporale: {exc}') from exc
