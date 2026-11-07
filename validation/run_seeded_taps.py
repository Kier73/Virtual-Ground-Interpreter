"""Single-build seeded TAPS runner.

This is the default execution path for empirical Builds 13-15 in this
repository.  It wraps the frozen analysis, binds an explicit logged pair salt,
and writes seeded_salt_provenance.json beside the frozen report.

Usage:
    python validation/run_seeded_taps.py --build 14 --root <TAPS_ROOT> --output <OUT> --seed 13
"""
from __future__ import annotations

import argparse
import json

if __package__ in (None, ""):
    from taps_seeded_runner import run_seeded_taps
else:
    from .taps_seeded_runner import run_seeded_taps


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a frozen TAPS build with an explicit logged seed")
    parser.add_argument("--build", type=int, choices=(13, 14, 15), required=True)
    parser.add_argument("--root", required=True, help="TAPS root containing the split directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--split", default="test")
    parser.add_argument("--max-speakers", type=int, default=None)
    parser.add_argument("--max-utterances-per-speaker", type=int, default=None)
    parser.add_argument("--permutations", type=int, default=99)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    result = run_seeded_taps(
        args.build,
        args.root,
        args.output,
        split=args.split,
        max_speakers=args.max_speakers,
        max_utterances_per_speaker=args.max_utterances_per_speaker,
        permutations=args.permutations,
        seed=args.seed,
    )
    print(json.dumps(result["provenance"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
