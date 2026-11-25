#!/usr/bin/env python3
"""RQ1b: persistenza di coppie reciproche e motivi orientati negli anni.

Uso: py src/rq1_temporal_persistence_v2.py
Dipende da numpy, matplotlib e da analyze_rq1.py (nella stessa cartella).
Non effettua test di significativita: i risultati sono DESCRITTIVI.

Opportunita di coppia: entrambi i Paesi finalisti nello stesso anno.
Opportunita di triade: tutti e tre finalisti nello stesso anno.
Per tutte le reti si usa la stessa convenzione: W[i,j] = punti i -> j.
Ogni triade ciclica ha due possibili orientamenti; ciascun ciclo e contato
una sola volta. Ogni triade transitiva ha sei possibili ordini diretti.
I motivi sono NON indotti (eventuali archi aggiuntivi non li annullano).
Nessuna affermazione causale o inferenza temporale senza modello nullo.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from itertools import combinations, permutations
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from analyze_rq1 import YEARS, LAYERS, MATRICES, RESULTS, FIGURES, read_matrix


def save_csv(file: Path, fields, rows):
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def key_triads(a,b,c):
    """Due orientamenti ciclici e sei transitivi per ogni terna ordinata a<b<c."""
    v = (a,b,c)
    cycles = [('cycle', (a,b,c)), ('cycle', (a,c,b))]
    trans = [('transitive', p) for p in permutations(v, 3)]
    return cycles + trans


def fmt_years(ys):
    return ';'.join(str(y) for y in sorted(ys))


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    pair_state = defaultdict(lambda: {'op': set(), 'binary': set(), 'high': set(), 'intensities': [], 'all_point_values': [], 'annual': []})
    tri_state = defaultdict(lambda: {'op': set(), 'yes': set(), 'intensities': []})
    year_rows = []
    for layer in LAYERS:
        for year in YEARS:
            W,eligible,countries,finalists = read_matrix(MATRICES / f'{year}_{layer}.csv')
            final_idx = np.flatnonzero(finalists)
            annual_pairs = 0
            annual_high = 0
            annual_cycles = 0
            annual_transitive = 0
            for ii,jj in combinations(final_idx,2):
                a,b = sorted((countries[ii], countries[jj]))
                i,j = (ii,jj) if countries[ii] == a else (jj,ii)
                w1,w2 = int(W[i,j]),int(W[j,i])
                rec = w1>0 and w2>0
                high = w1>=10 and w2>=10
                s = pair_state[(layer,a,b)]
                s['op'].add(year)
                s['annual'].append({'layer':layer,'year':year,'country_a':a,'country_b':b,
                                    'points_a_to_b':w1,'points_b_to_a':w2,
                                    'reciprocal':int(rec),'reciprocal_ge10':int(high),
                                    'reciprocal_strength':min(w1,w2)/12})
                s['all_point_values'].append(min(w1,w2)/12)
                if rec:
                    s['binary'].add(year)
                    s['intensities'].append(min(w1,w2)/12)
                    annual_pairs+=1
                if high:
                    s['high'].add(year)
                    annual_high+=1
            for ii,jj,kk in combinations(final_idx,3):
                # Chiavi per codici Paese indipendenti dall'ordine delle matrici
                names = tuple(sorted((countries[ii],countries[jj],countries[kk])))
                idx = {countries[x]:x for x in (ii,jj,kk)}
                for typ,(a,b,c) in key_triads(*names):
                    if typ == 'cycle':
                        edges=((a,b),(b,c),(c,a))
                    else:
                        edges=((a,b),(b,c),(a,c))
                    weights=[int(W[idx[x],idx[y]]) for x,y in edges]
                    s=tri_state[(layer,typ,a,b,c)]
                    s['op'].add(year)
                    if all(w>0 for w in weights):
                        s['yes'].add(year)
                        s['intensities'].append(float(np.prod(weights,dtype=np.float64)**(1/3)))
                        if typ=='cycle': annual_cycles+=1
                        else: annual_transitive+=1
            year_rows.append({'layer':layer,'year':year,'finalists':len(final_idx),
                              'reciprocal_pairs':annual_pairs,'reciprocal_pairs_ge10':annual_high,
                              'directed_3_cycles':annual_cycles,'directed_transitive_motifs':annual_transitive})
            print(f'{year} {layer}: {len(final_idx)} finalisti, {annual_pairs} coppie reciproche, '
                  f'{annual_cycles} cicli, {annual_transitive} transitive')

    pair_rows=[]; pair_year_rows=[]
    for (layer,a,b),s in sorted(pair_state.items()):
        n=len(s['op']); r=len(s['binary']); high=len(s['high'])
        pair_year_rows.extend(s['annual'])
        pair_rows.append({'layer':layer,'country_a':a,'country_b':b,'opportunity_years':n,
                          'reciprocal_years':r,'reciprocity_frequency':r/n,
                          'high_reciprocal_years':high,'high_reciprocity_frequency':high/n,
                          'mean_reciprocal_strength_all_opportunities':float(np.mean(s['all_point_values'])),
                          'mean_reciprocal_strength_if_present':float(np.mean(s['intensities'])) if r else '',
                          'years_eligible':fmt_years(s['op']),'years_reciprocal':fmt_years(s['binary']),
                          'years_high_reciprocal':fmt_years(s['high'])})

    tri_rows=[]
    tri_observed_rows=[]
    for (layer,typ,a,b,c),s in sorted(tri_state.items()):
        n=len(s['op']); p=len(s['yes'])
        # Conserviamo anche i motivi mai osservati: sono parte del denominatore.
        # L'intensita condizionale e indefinita, non zero, se il motivo e assente.
        row={'layer':layer,'motif':typ,'country_a':a,'country_b':b,'country_c':c,
             'opportunity_years':n,'observed_years':p,'persistence_frequency':p/n,
             'mean_intensity_if_present':float(np.mean(s['intensities'])) if p else '',
             'years_eligible':fmt_years(s['op']), 'years_observed':fmt_years(s['yes'])}
        tri_rows.append(row)
        if p: tri_observed_rows.append(row)
    pair_rows.sort(key=lambda r:(r['layer'],-r['opportunity_years'],-r['reciprocity_frequency'],r['country_a'],r['country_b']))
    tri_rows.sort(key=lambda r:(r['layer'],r['motif'],-r['observed_years'],-r['opportunity_years'],r['country_a'],r['country_b'],r['country_c']))

    save_csv(RESULTS/'rq1_temporal_pair_years.csv',list(pair_year_rows[0]),pair_year_rows)
    save_csv(RESULTS/'rq1_temporal_pairs.csv',list(pair_rows[0]),pair_rows)
    save_csv(RESULTS/'rq1_temporal_motifs.csv',list(tri_rows[0]),tri_rows)
    # Facoltativo: tabella ridotta, soltanto per consultare motivi presenti.
    save_csv(RESULTS/'rq1_temporal_motifs_observed_only.csv',list(tri_rows[0]),tri_observed_rows)

    # Verifiche automatiche di coerenza tra aggregati e dati annuali.
    for r in year_rows:
        layer, year = r['layer'], r['year']
        pairs = [p for p in pair_state.values() for x in p['annual'] if x['layer']==layer and x['year']==year and x['reciprocal']]
        # Il conteggio dei motivi annuali deve coincidere col numero di chiavi attive.
        counts = {typ:sum(year in s['yes'] for (ly,t,*_),s in tri_state.items() if ly==layer and t==typ) for typ in ('cycle','transitive')}
        if len(pairs)!=r['reciprocal_pairs'] or counts['cycle']!=r['directed_3_cycles'] or counts['transitive']!=r['directed_transitive_motifs']:
            raise AssertionError(f'Incoerenza fra conteggi annuali e serie temporali: {year} {layer}')
    save_csv(RESULTS/'rq1_temporal_year_summary.csv',list(year_rows[0]),year_rows)

    # Riepilogo globale con lo stesso universo di opportunita per ogni livello.
    summary=[]
    for layer in LAYERS:
        pset=[p for p in pair_rows if p['layer']==layer and p['opportunity_years']>=3]
        for typ in ('cycle','transitive'):
            tset=[t for t in tri_rows if t['layer']==layer and t['motif']==typ and t['opportunity_years']>=3]
            summary.append({'layer':layer,'unit':typ,'min_opportunity_years':3,
                'eligible_units':len(tset),'ever_observed':sum(t['observed_years']>0 for t in tset),
                'always_observed':sum(t['observed_years']==t['opportunity_years'] for t in tset),
                'frequency_ge75pct':sum(t['persistence_frequency']>=.75 for t in tset),
                'mean_frequency_including_zeros':float(np.mean([t['persistence_frequency'] for t in tset])) if tset else ''})
        summary.append({'layer':layer,'unit':'reciprocal_pair','min_opportunity_years':3,
            'eligible_units':len(pset),'ever_observed':sum(p['reciprocal_years']>0 for p in pset),
            'always_observed':sum(p['reciprocal_years']==p['opportunity_years'] for p in pset),
            'frequency_ge75pct':sum(p['reciprocity_frequency']>=.75 for p in pset),
            'mean_frequency_including_zeros':float(np.mean([p['reciprocity_frequency'] for p in pset])) if pset else ''})
    save_csv(RESULTS/'rq1_temporal_global_summary.csv',list(summary[0]),summary)

    # Plot: tassi per coppie con almeno 3 opportunita (evita classifiche 1/1)
    fig,ax=plt.subplots(1,2,figsize=(14,5),sharex=True)
    for layer,color in [('jury','#28759d'),('public','#d17737')]:
        eligible_pairs=[p for p in pair_rows if p['layer']==layer and p['opportunity_years']>=3]
        for subplot,col,label in [(ax[0],'reciprocity_frequency','Reciprocita'),
                                   (ax[1],'high_reciprocity_frequency','Reciprocita 10/12')]:
            x=list(range(1,11))
            y=[sum(p[col]>=k/10 for p in eligible_pairs)/len(eligible_pairs) if eligible_pairs else np.nan for k in x]
            subplot.plot([k/10 for k in x],y,marker='o',label=layer,color=color)
            subplot.set_title(label+' — coppie con >=3 opportunita')
            subplot.set_xlabel('Soglia di frequenza nelle occasioni ammissibili')
            subplot.set_ylabel('Quota di coppie oltre soglia')
            subplot.grid(alpha=.25)
    ax[0].legend(); ax[1].legend(); fig.tight_layout()
    fig.savefig(FIGURES/'rq1_temporal_persistence.png',dpi=150)
    plt.close(fig)

    print(f'Output CSV: {RESULTS}')
    print(f'Grafico: {FIGURES / "rq1_temporal_persistence.png"}')
    print(f'Motivi candidati (inclusi gli zeri): {len(tri_rows)}; mai osservati: {len(tri_rows)-len(tri_observed_rows)}')
    print('ATTENZIONE: risultati solo descrittivi; nessun test temporale o controllo della popolarita.')


if __name__=='__main__':
    main()
