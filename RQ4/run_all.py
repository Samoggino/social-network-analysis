"""Run both RQ4 analyses and record their complete shared configuration."""

import hashlib
import json
import platform
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import matplotlib
import numpy as np

import analyze_rq4_layer_similarity as annual
import analyze_rq4_temporal_stability as temporal
from rq4_common import BATCH_SIZE, LAYERS, PRIMARY, SEED, YEARS, load_editions, parser


def main() -> None:
    cli = parser(__doc__, SEED)
    args = cli.parse_args()
    if args.permutations < 1:
        cli.error("--permutations must be positive")

    names = [f"{year}_{layer}.csv" for year in YEARS for layer in LAYERS]

    def fingerprints():
        return {name: hashlib.sha256((args.matrices / name).read_bytes()).hexdigest()
                for name in names}

    source_hashes = fingerprints()
    editions = load_editions(args.matrices)
    print("Within-edition analysis", flush=True)
    annual.run(editions, args.output_dir, args.permutations, args.seed)
    print("Temporal analysis and sensitivity checks", flush=True)
    temporal.run(editions, args.output_dir, args.permutations, args.seed + 1)
    if source_hashes != fingerprints():
        raise RuntimeError("Input matrices changed during the analysis")

    recipes = {
        "years": YEARS,
        "layers": LAYERS,
        "permutations": args.permutations,
        "batch_size": BATCH_SIZE,
        "random_generator": "NumPy PCG64",
        "seeds": {"within_edition": args.seed, "temporal": args.seed + 1},
        "primary_statistic": PRIMARY,
        "primary_lag": 1,
        "temporal_pair_weights": "equal by edition pair",
        "permutation_strata": ["finalists", "non-finalists"],
        "p_value": "two-sided equal tails, Monte Carlo +1",
        "holm_families": {"within_edition": list(YEARS), "temporal_lag_1": ["jury", "public", "public_minus_jury"]},
        "matrix_sha256": source_hashes,
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "matplotlib": matplotlib.__version__},
    }
    destination = args.output_dir / "results" / "rq4" / "rq4_run_config.json"
    destination.write_text(json.dumps(recipes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("RQ4 complete", flush=True)


if __name__ == "__main__":
    main()
