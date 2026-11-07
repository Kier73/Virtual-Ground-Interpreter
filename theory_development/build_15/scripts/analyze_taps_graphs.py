#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_15 import run_taps_graph_analysis


def main():
    ap = argparse.ArgumentParser(description="Analyze TAPS with local-clock event graphs")
    ap.add_argument("--root", required=True, help="Extracted split root containing paired WAVs")
    ap.add_argument("--split", default="test", choices=("train", "dev", "test"))
    ap.add_argument("--output", default="reports/taps_test_build15")
    ap.add_argument("--max-speakers", type=int, default=None)
    ap.add_argument("--max-utterances-per-speaker", type=int, default=None)
    ap.add_argument("--frame-ms", type=float, default=20.0)
    ap.add_argument("--min-gap-ms", type=float, default=80.0)
    args = ap.parse_args()
    report = run_taps_graph_analysis(args.root, args.output, split=args.split,
        max_speakers=args.max_speakers,
        max_utterances_per_speaker=args.max_utterances_per_speaker,
        frame_ms=args.frame_ms, min_gap_ms=args.min_gap_ms)
    print(json.dumps(report, indent=2))

if __name__ == "__main__": main()
