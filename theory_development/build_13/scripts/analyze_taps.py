#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_13


def main():
    ap = argparse.ArgumentParser(description="Analyze paired TAPS speech sensor recordings")
    ap.add_argument("--root", required=True, help="Extracted split root containing speaker/utterance directories")
    ap.add_argument("--split", choices=("train", "dev", "test"), default="test")
    ap.add_argument("--output", default="reports/taps_test")
    ap.add_argument("--max-speakers", type=int, default=10)
    ap.add_argument("--max-utterances-per-speaker", type=int, default=20)
    ap.add_argument("--permutations", type=int, default=99)
    ap.add_argument("--write-pair-features", action="store_true")
    args = ap.parse_args()
    result = build_13.run_analysis(args.root, args.output, args.split,
                                   args.max_speakers, args.max_utterances_per_speaker,
                                   args.permutations, write_pair_features=args.write_pair_features)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
