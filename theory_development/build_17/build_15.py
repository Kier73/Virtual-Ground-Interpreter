#!/usr/bin/env python3
"""Build 15: local-clock event graphs for paired observer streams."""
from __future__ import annotations
import argparse
import json
import math
import random
import statistics
from pathlib import Path
from typing import Sequence

import build_14
from local_clock_graph import EventStream, analyze_stream_pair, extract_event_stream_from_wav


def _median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else 0.0


def _quantile(values: Sequence[float], q: float) -> float:
    if not values: return 0.0
    xs = sorted(values)
    pos = (len(xs)-1)*q
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] if lo == hi else xs[lo]*(hi-pos)+xs[hi]*(pos-lo)


def _bootstrap_speaker_medians(rows: list[dict], key: str, n_boot: int = 1000, seed: int = 15) -> dict:
    by_speaker: dict[str, list[float]] = {}
    for row in rows:
        val = row.get(key)
        if val is not None:
            by_speaker.setdefault(row["speaker_internal"], []).append(float(val))
    speaker_values = [_median(v) for v in by_speaker.values() if v]
    if not speaker_values:
        return {"speaker_groups": 0, "median": 0.0, "bootstrap_95_ci": [0.0, 0.0]}
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [speaker_values[rng.randrange(len(speaker_values))] for _ in speaker_values]
        boots.append(_median(sample))
    return {"speaker_groups": len(speaker_values), "median": _median(speaker_values),
            "bootstrap_95_ci": [_quantile(boots, 0.025), _quantile(boots, 0.975)]}


def run_taps_graph_analysis(root: str | Path, output: str | Path, *, split: str = "test",
                            max_speakers: int | None = None,
                            max_utterances_per_speaker: int | None = None,
                            frame_ms: float = 20.0, min_gap_ms: float = 80.0) -> dict:
    """Analyze paired TAPS WAVs; only aggregate outputs are written by default."""
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    pairs = build_14.discover_pairs(root, split=split)
    # Apply caps to the internally grouped split without exporting speaker identifiers.
    by_speaker: dict[str, list[dict]] = {}
    for p in pairs:
        by_speaker.setdefault(p["speaker_internal"], []).append(p)
    speakers = sorted(by_speaker)
    if max_speakers is not None:
        if max_speakers < 1: raise ValueError("max_speakers must be >= 1")
        speakers = speakers[:max_speakers]
    selected = []
    for s in speakers:
        items = sorted(by_speaker[s], key=lambda x: x["pair_key"])
        if max_utterances_per_speaker is not None:
            if max_utterances_per_speaker < 1: raise ValueError("max_utterances_per_speaker must be >= 1")
            items = items[:max_utterances_per_speaker]
        selected.extend(items)

    rows = []
    skip_reasons: dict[str, int] = {}
    for pair in selected:
        try:
            left = extract_event_stream_from_wav(str(pair["throat_path"]), "throat",
                                                 frame_ms=frame_ms, min_gap_ms=min_gap_ms)
            right = extract_event_stream_from_wav(str(pair["acoustic_path"]), "acoustic",
                                                  frame_ms=frame_ms, min_gap_ms=min_gap_ms)
            result = analyze_stream_pair(left, right)
            a = result["alignment"]
            ia = result["interval_agreement"]
            cr = result["post_match_clock_relation"]
            row = {
                "speaker_internal": pair["speaker_internal"],
                "left_count": a["left_count"], "right_count": a["right_count"],
                "matched_count": a["matched_count"],
                "left_coverage": a["left_coverage"], "right_coverage": a["right_coverage"],
                "median_match_cost": a["median_match_cost"],
                "mark_rank_spearman": result["matched_mark_rank_spearman"],
                "interval_spearman": ia.get("normalized_interval_spearman"),
                "interval_log_error": ia.get("median_absolute_log_interval_difference"),
                "clock_scale_estimate": cr.get("left_time_approximately_equals_offset_plus_scale_times_right_time", {}).get("scale"),
                "clock_offset_estimate_s": cr.get("left_time_approximately_equals_offset_plus_scale_times_right_time", {}).get("offset_s"),
                "clock_residual_s": cr.get("median_absolute_residual_s"),
            }
            rows.append(row)
        except (ValueError, OSError) as exc:
            reason = type(exc).__name__
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    def numeric(key: str) -> list[float]:
        return [float(r[key]) for r in rows if r.get(key) is not None]

    report = {
        "build": 15,
        "dataset": "TAPS paired throat-vibration / acoustic speech corpus",
        "split": split,
        "analysis_status": "empirical_audio_analyzed" if rows else "no_pairs_analyzed",
        "pairs_discovered": len(pairs),
        "pairs_selected": len(selected),
        "pairs_analyzed": len(rows),
        "pairs_skipped": sum(skip_reasons.values()),
        "skip_reasons_by_exception_type": skip_reasons,
        "event_observer": {"frame_ms": frame_ms, "min_gap_ms": min_gap_ms,
                           "peak_rule": "Build 14 RMS-envelope local maxima"},
        "matching": {"algorithm": "monotone dynamic-programming sequence alignment",
                     "features": "within-stream mark rank + median-normalized log interval shape",
                     "absolute_timestamps_compared": False,
                     "cross_stream_clock_required": False},
        "aggregate": {
            "matched_events_per_pair_median": _median(numeric("matched_count")),
            "throat_event_coverage": _bootstrap_speaker_medians(rows, "left_coverage"),
            "acoustic_event_coverage": _bootstrap_speaker_medians(rows, "right_coverage"),
            "median_match_cost": _median(numeric("median_match_cost")),
            "matched_mark_rank_spearman": _median(numeric("mark_rank_spearman")),
            "matched_interval_spearman": _median(numeric("interval_spearman")),
            "matched_interval_log_error": _median(numeric("interval_log_error")),
            "post_match_clock_scale_estimate": _median(numeric("clock_scale_estimate")),
            "post_match_clock_offset_estimate_s": _median(numeric("clock_offset_estimate_s")),
            "post_match_clock_residual_s": _median(numeric("clock_residual_s")),
        },
        "privacy": {"raw_speaker_ids_exported": False, "utterance_ids_exported": False,
                    "transcripts_exported": False, "demographics_exported": False,
                    "raw_audio_copied": False, "per_utterance_results_exported": False},
        "interpretation_limits": [
            "Matched envelope landmarks are inferred correspondences, not verified latent-state identities.",
            "No shared timestamp coordinate is used by the matching algorithm.",
            "Clock offset and scale are estimated only after event matching and are diagnostics, not proof of clock synchronization.",
            "Sensor transfer functions and the Build 14 event detector may produce observer-specific missed or extra landmarks.",
            "An empirical result on TAPS does not establish a universal invariant or generalize automatically to other sensor domains.",
        ],
    }
    (output / "build_15_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Build 15 local-clock event-graph analysis")
    ap.add_argument("--root", required=True, help="TAPS split root containing speaker/utterance paired WAVs")
    ap.add_argument("--split", choices=("train", "dev", "test"), default="test")
    ap.add_argument("--output", default="reports/taps_test_build15")
    ap.add_argument("--max-speakers", type=int, default=None)
    ap.add_argument("--max-utterances-per-speaker", type=int, default=None)
    ap.add_argument("--frame-ms", type=float, default=20.0)
    ap.add_argument("--min-gap-ms", type=float, default=80.0)
    args = ap.parse_args()
    result = run_taps_graph_analysis(args.root, args.output, split=args.split,
                                     max_speakers=args.max_speakers,
                                     max_utterances_per_speaker=args.max_utterances_per_speaker,
                                     frame_ms=args.frame_ms, min_gap_ms=args.min_gap_ms)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
