#!/usr/bin/env python3
"""Check all 20 matrices, ballot rules and 19,698 eligible directed opportunities."""
from __future__ import annotations
import csv
from pathlib import Path
from analyze_rq2_partitions import YEARS, LAYERS

ROOT = Path(__file__).resolve().parent.parent
BALLOT = sorted([1,2,3,4,5,6,7,8,10,12])


def main():
    all_countries = set()
    total_voter_years = 0
    total_opportunities = 0
    for year in YEARS:
        summaries=[]
        for layer in LAYERS:
            path = ROOT / 'processed_data' / 'matrices' / f'{year}_{layer}.csv'
            with path.open(encoding='utf-8-sig',newline='') as f:
                data=list(csv.reader(f))
            header = data[0]; columns = header[1:]; rows = data[1:]
            assert len(set(columns)) == len(columns), path
            assert len(rows) == len(columns), (year,layer, 'square matrix')
            assert set(r[0] for r in rows) == set(columns), path
            assert all(len(r)==len(header) for r in rows), path
            finalists={c for j,c in enumerate(columns) if any(r[j+1] != '' for r in rows)}
            for r in rows:
                source=r[0]
                actual=[int(x) for x in r[1:] if x != '' and int(x)>0]
                assert sorted(actual)==BALLOT, (year,layer,source,'ballot',sorted(actual))
                for target, raw in zip(columns,r[1:]):
                    eligible = target in finalists and target != source
                    assert (raw != '') == eligible, (year,layer,source,target,'eligibility')
                    if raw != '': assert int(raw) in BALLOT+[0], (year,layer,source,target,raw)
            summaries.append((columns,finalists))
            all_countries.update(columns)
            total_opportunities += len(columns)*len(finalists)-len(finalists)
        assert summaries[0]==summaries[1], (year,'jury/public eligibility mismatch')
        total_voter_years+=len(summaries[0][0])
        print(year,len(summaries[0][0]),len(summaries[0][1]),'OK')
    assert total_opportunities == 19698, total_opportunities
    assert total_voter_years == 393, total_voter_years
    assert len(all_countries) == 45, len(all_countries)
    print(f'OK: 20 networks; {len(all_countries)} countries; {total_voter_years} voter-editions; {total_opportunities} opportunities; {total_voter_years*20} positive arcs')

if __name__=='__main__': main()
