#!/usr/bin/env python3
"""Leave-one-edition-out sensitivity of principal jury/public differences.

This is sensitivity analysis, not a time-series-adjusted significance test.
"""
from __future__ import annotations
import csv
from pathlib import Path
import numpy as np
from analyze_rq2_partitions import YEARS, sign_flip_test
ROOT=Path(__file__).resolve().parent.parent
R=ROOT/'results'/'rq2'

def read(name):
    with (R/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    specs=[
      ('rq2_opportunity.csv','share_points_region','same-subregion point share'),
      ('rq2_opportunity.csv','share_slots_region','same-subregion choice share'),
      ('rq2_consensus.csv','ari_region','consensus geographic ARI'),
      ('rq2_language_within.csv','share_slots','cross-region shared-language choice share'),
      ('rq2_language_within.csv','share_points','cross-region shared-language point share'),
    ]
    rows=[]
    for file,key,label in specs:
        data=read(file)
        if file=='rq2_consensus.csv':data=[r for r in data if r['scope']=='all']
        yearly={}
        for r in data:
            yearly.setdefault(int(r['year']),{})[r['layer']]=float(r[key])
        assert set(yearly)==set(YEARS),(file,key,'missing years')
        diffs=np.array([yearly[y]['public']-yearly[y]['jury'] for y in YEARS])
        full=float(diffs.mean())
        for i,y in enumerate(YEARS):
            others=np.delete(diffs,i)
            # an exact sign-flip test on the remaining 9 annual differences
            from itertools import product
            observed=float(others.mean())
            permutations=[float(np.mean(others*np.array(signs))) for signs in product((1,-1),repeat=len(others))]
            p=float(np.mean(np.abs(permutations)>=abs(observed)-1e-12))
            rows.append((label,key,y,full,observed,p,int(np.sign(full)==np.sign(observed))))
    R.mkdir(parents=True,exist_ok=True)
    with (R/'rq2_leave_one_year_out.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['metric','key','excluded_year','difference_all_years','difference_without_year','paired_p_without_year','same_sign']);w.writerows(rows)
    print('Leave-one-year-out output:',len(rows),'rows')
if __name__=='__main__':main()
