#!/usr/bin/env python3
"""Run all RQ2 stages in dependency order; never modifies the input data."""
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parent
stages=[
    'validate_data.py', 'make_country_attributes.py',
    'analyze_rq2.py', 'analyze_rq2_opportunity.py',
    'analyze_rq2_partitions.py', 'analyze_rq2_consensus.py',
    'analyze_rq2_modularity_null.py', 'analyze_rq2_language_within.py',
    'analyze_rq2_ballot_null.py', 'analyze_rq2_robustness.py',
]
for s in stages:
    print(f'\n=== {s} ===', flush=True)
    subprocess.run([sys.executable,str(root/'src'/s)],cwd=root,check=True)
print('\nAll RQ2 stages finished.')
