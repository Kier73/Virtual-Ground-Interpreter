"""Run seeded TAPS wrapper and speaker/sentence cross-validation.

Usage:
    python validation/run_taps_cv.py --root <TAPS_ROOT> --split test
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ in (None, ""):
    from taps_seeded_runner import run_seeded_taps, sentence_cross_validation, speaker_cross_validation
else:
    from .taps_seeded_runner import run_seeded_taps, sentence_cross_validation, speaker_cross_validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run seeded TAPS validation and group CV")
    parser.add_argument("--root", required=True, help="TAPS root containing the split directory")
    parser.add_argument("--split", default="test")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--max-utterances", type=int, default=30)
    parser.add_argument("--sentence-max-utterances", type=int, default=None)
    parser.add_argument("--permutations", type=int, default=29)
    parser.add_argument("--out", default="validation/taps_cv_results.json")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    smoke_dir = here / "taps_seeded_smoke"
    smoke = run_seeded_taps(
        14,
        args.root,
        smoke_dir,
        split=args.split,
        max_speakers=2,
        max_utterances_per_speaker=8,
        permutations=5,
        seed=args.seed,
    )
    smoke_provenance = dict(smoke["provenance"])
    smoke_provenance["root"] = "<external TAPS root>"
    smoke_provenance["output_dir"] = "validation/taps_seeded_smoke"
    speaker_cv = speaker_cross_validation(
        args.root,
        split=args.split,
        seed=args.seed,
        folds=5,
        permutations=args.permutations,
        max_utterances_per_speaker=args.max_utterances,
    )
    sentence_cv = sentence_cross_validation(
        args.root,
        split=args.split,
        seed=args.seed,
        folds=5,
        permutations=args.permutations,
        max_utterances_per_speaker=args.sentence_max_utterances,
    )
    report = {
        "seed": args.seed,
        "root": "<external TAPS root>",
        "split": args.split,
        "seeded_smoke": {
            "pairs_analyzed": smoke["report"].get("pairs_analyzed"),
            "speakers_analyzed": smoke["report"].get("speakers_analyzed"),
            "provenance": smoke_provenance,
        },
        "speaker_cv": speaker_cv,
        "sentence_cv": sentence_cv,
    }
    out = Path(args.out)
    if not out.is_absolute():
        out = Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
