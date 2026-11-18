#!/usr/bin/env python3
"""Controlli replicabili sui dati generati prima delle Research Questions."""
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parent
M = ROOT / 'processed_data' / 'matrices'
T = ROOT / 'processed_data' / 'tables'
YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
POINTS = sorted((1, 2, 3, 4, 5, 6, 7, 8, 10, 12))

def rows(path):
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def check():
    files = [M / f'{y}_{layer}.csv' for y in YEARS for layer in ('jury', 'public')]
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        raise ValueError('Matrici mancanti: ' + ', '.join(missing))
    count_eligible = 0
    countries_all = set()
    for p in files:
        rs = rows(p)
        if not rs:
            raise ValueError(f'{p.name}: file vuoto')
        headers = list(rs[0].keys())
        if headers[0] != 'country' or len(rs) != len(headers)-1:
            raise ValueError(f'{p.name}: intestazione o dimensione non corretta')
        countries = headers[1:]
        if {r['country'] for r in rs} != set(countries):
            raise ValueError(f'{p.name}: etichette righe e colonne diverse')
        countries_all.update(countries)
        for r in rs:
            vals = [r[c].strip() for c in countries if r[c].strip()]
            if vals:
                if sorted(int(x) for x in vals if int(x)>0) != POINTS:
                    raise ValueError(f"{p.name}: scheda voto non valida per {r['country']}")
                count_eligible += len(vals)
    master = rows(T / 'votes_master.csv')
    nodes = rows(T / 'nodes.csv')
    if len(master) != count_eligible:
        raise ValueError('votes_master.csv non corrisponde alle matrici')
    if {r['country'] for r in nodes} != countries_all:
        raise ValueError('nodes.csv non corrisponde alle matrici')
    print('VERIFICA RIUSCITA')
    print(f'Matrici: {len(files)}')
    print(f'Voti ammissibili: {len(master)} (atteso con lo snapshot originario: 19698)')
    print(f'Paesi: {len(nodes)} (atteso con lo snapshot originario: 45)')
    print('Attenzione: verifica interna, non confronto con risultati ufficiali EBU.')
    if (len(master), len(nodes)) != (19698, 45):
        print('AVVISO: il repository GitHub potrebbe essere cambiato o i dati potrebbero differire dallo snapshot originale.')

if __name__=='__main__':
    try:
        check()
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f'ERRORE VERIFICA: {e}', file=sys.stderr)
        sys.exit(1)
