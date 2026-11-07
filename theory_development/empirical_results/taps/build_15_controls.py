#!/usr/bin/env python3
"""External controls for the Build 15 TAPS event-graph analysis.

The frozen Build 15 package does not ship these controls.  This script imports
the unmodified build and adds:

  * true utterance pairs versus within-speaker mismatched pairs (a null that
    preserves speaker, language, sentence style and approximate duration);
  * combined, mark-only and interval-only matching costs;
  * shuffled-mark streams (same times and mark distribution, wrong mark-to-event
    assignment);
  * an optional event-detector frame/min-gap sweep on a subset.

Only aggregate results are written.  Speaker identifiers, utterance identifiers,
transcripts, demographics and per-utterance rows are never exported.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BUILD_ROOT = HERE.parents[2] / "build_15"
sys.path.insert(0, str(BUILD_ROOT))

import build_14  # noqa: E402
from local_clock_graph import (  # noqa: E402
    EventStream,
    _matched_interval_agreement,
    _spearman,
    _theil_sen_clock_relation,
    align_event_streams,
    event_features,
    extract_event_stream_from_wav,
)


def _median(values):
    return statistics.median(values) if values else None


def _quantile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def _bootstrap_ci(values, n_boot=2000, seed=15):
    if len(values) < 2:
        return [None, None]
    rng = random.Random(seed)
    medians = []
    n = len(values)
    for _ in range(n_boot):
        medians.append(statistics.median(rng.choice(values) for _ in range(n)))
    medians.sort()
    return [medians[int(0.025 * (len(medians) - 1))],
            medians[int(0.975 * (len(medians) - 1))]]


def _speaker_summary(rows, key):
    """Median of within-speaker medians, with a speaker bootstrap interval."""
    groups = {}
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        groups.setdefault(row["speaker"], []).append(float(value))
    speaker_values = [statistics.median(values) for values in groups.values() if values]
    return {
        "speaker_groups": len(speaker_values),
        "median": _median(speaker_values),
        "bootstrap_95pct_ci": _bootstrap_ci(speaker_values),
        "min": min(speaker_values) if speaker_values else None,
        "max": max(speaker_values) if speaker_values else None,
    }


def _pair_metrics(left, right, *, mark_weight, interval_weight):
    alignment = align_event_streams(
        left, right, mark_weight=mark_weight, interval_weight=interval_weight)
    interval = _matched_interval_agreement(left, right, alignment["matches"])
    clock = _theil_sen_clock_relation(left, right, alignment["matches"])
    lf, rf = event_features(left), event_features(right)
    mark_corr = _spearman(
        [lf[m["left_index"]]["mark_rank"] for m in alignment["matches"]],
        [rf[m["right_index"]]["mark_rank"] for m in alignment["matches"]],
    )
    scale = clock.get("left_time_approximately_equals_offset_plus_scale_times_right_time", {})
    return {
        "left_count": alignment["left_count"],
        "right_count": alignment["right_count"],
        "matched_count": alignment["matched_count"],
        "left_coverage": alignment["left_coverage"],
        "right_coverage": alignment["right_coverage"],
        "median_match_cost": alignment["median_match_cost"],
        "mark_rank_spearman": mark_corr,
        "interval_spearman": interval.get("normalized_interval_spearman"),
        "interval_log_error": interval.get("median_absolute_log_interval_difference"),
        "clock_scale": scale.get("scale"),
        "clock_offset_s": scale.get("offset_s"),
        "clock_residual_s": clock.get("median_absolute_residual_s"),
    }


def _shuffle_marks(stream, rng):
    marks = list(stream.marks)
    rng.shuffle(marks)
    return EventStream(
        observer=stream.observer,
        local_times_s=stream.local_times_s,
        marks=tuple(marks),
        duration_s=stream.duration_s,
    )


def _shuffle_gap_order(stream, rng):
    """Preserve event count, start time and gap multiset; destroy gap order."""
    times = list(stream.local_times_s)
    if len(times) < 2:
        return stream
    gaps = [b - a for a, b in zip(times, times[1:])]
    rng.shuffle(gaps)
    new_times = [times[0]]
    for gap in gaps:
        new_times.append(new_times[-1] + gap)
    return EventStream(
        observer=stream.observer,
        local_times_s=tuple(new_times),
        marks=stream.marks,
        duration_s=stream.duration_s,
    )


def _summarize_condition(rows, label):
    keys = [
        "left_count",
        "right_count",
        "matched_count",
        "left_coverage",
        "right_coverage",
        "median_match_cost",
        "mark_rank_spearman",
        "interval_spearman",
        "interval_log_error",
        "clock_scale",
        "clock_offset_s",
        "clock_residual_s",
    ]
    return {
        "condition": label,
        "pairs": len(rows),
        "metrics": {key: _speaker_summary(rows, key) for key in keys},
    }


def run_controls(root, output, *, split="test", max_speakers=None,
                 max_utterances_per_speaker=None, null_shifts=(1, 37, 73),
                 frame_ms=20.0, min_gap_ms=80.0, seed=15):
    pairs = build_14.discover_pairs(root, split=split)
    by_speaker = {}
    for pair in pairs:
        by_speaker.setdefault(pair["speaker_internal"], []).append(pair)
    speakers = sorted(by_speaker)
    if max_speakers is not None:
        speakers = speakers[:max_speakers]
    selected = []
    for speaker in speakers:
        items = sorted(by_speaker[speaker], key=lambda p: p["pair_key"])
        if max_utterances_per_speaker is not None:
            items = items[:max_utterances_per_speaker]
        selected.append((speaker, items))

    conditions = {name: [] for name in (
        "true_combined", "true_mark_only", "true_interval_only",
        "true_shuffled_marks", "true_shuffled_interval_order",
        "true_shuffled_interval_order_interval_only")}
    for shift in null_shifts:
        conditions[f"mismatched_shift_{shift}"] = []

    rng = random.Random(seed)
    for speaker, items in selected:
        streams = []
        for pair in items:
            left = extract_event_stream_from_wav(
                str(pair["throat_path"]), "throat",
                frame_ms=frame_ms, min_gap_ms=min_gap_ms)
            right = extract_event_stream_from_wav(
                str(pair["acoustic_path"]), "acoustic",
                frame_ms=frame_ms, min_gap_ms=min_gap_ms)
            streams.append((left, right))
        n = len(streams)
        for index, (left, right) in enumerate(streams):
            base = {"speaker": speaker}
            base.update(_pair_metrics(
                left, right, mark_weight=0.78, interval_weight=0.22))
            conditions["true_combined"].append(dict(base))

            conditions["true_mark_only"].append(dict(
                {"speaker": speaker},
                **_pair_metrics(left, right, mark_weight=1.0, interval_weight=0.0)))
            conditions["true_interval_only"].append(dict(
                {"speaker": speaker},
                **_pair_metrics(left, right, mark_weight=0.0, interval_weight=1.0)))

            shuffled_left = _shuffle_marks(left, rng)
            shuffled_right = _shuffle_marks(right, rng)
            conditions["true_shuffled_marks"].append(dict(
                {"speaker": speaker},
                **_pair_metrics(
                    shuffled_left, shuffled_right,
                    mark_weight=0.78, interval_weight=0.22)))

            order_left = _shuffle_gap_order(left, rng)
            order_right = _shuffle_gap_order(right, rng)
            conditions["true_shuffled_interval_order"].append(dict(
                {"speaker": speaker},
                **_pair_metrics(
                    order_left, order_right,
                    mark_weight=0.78, interval_weight=0.22)))
            conditions["true_shuffled_interval_order_interval_only"].append(dict(
                {"speaker": speaker},
                **_pair_metrics(
                    order_left, order_right,
                    mark_weight=0.0, interval_weight=1.0)))

            for shift in null_shifts:
                other = streams[(index + shift) % n][1]
                conditions[f"mismatched_shift_{shift}"].append(dict(
                    {"speaker": speaker},
                    **_pair_metrics(
                        left, other, mark_weight=0.78, interval_weight=0.22)))

    report = {
        "build": 15,
        "dataset": "TAPS paired throat-vibration / acoustic speech corpus",
        "split": split,
        "analysis_status": "external_controls_complete",
        "control_design": {
            "true_pairs": "same utterance, throat versus acoustic",
            "mismatched_pairs": "throat utterance i versus acoustic utterance i+shift within speaker; preserves speaker and approximate duration, breaks utterance identity",
            "null_shifts": list(null_shifts),
            "mark_only": "mark_weight=1.0, interval_weight=0.0",
            "interval_only": "mark_weight=0.0, interval_weight=1.0",
            "combined": "mark_weight=0.78, interval_weight=0.22 (frozen Build 15 setting)",
            "shuffled_marks": "marks permuted within each stream; times and mark marginal distribution preserved",
            "shuffled_interval_order": "inter-event gaps permuted within each stream; preserves first event time, gap multiset, event count, mark sequence and total duration",
            "shuffled_interval_order_interval_only": "shuffled interval order with mark_weight=0.0 and interval_weight=1.0; isolates whether the temporal-order sequence carries the signal",
            "bootstrap": "within-speaker medians, 2000 speaker resamples, fixed seed 15",
        },
        "event_observer": {"frame_ms": frame_ms, "min_gap_ms": min_gap_ms},
        "speakers_analyzed": len(selected),
        "utterances_per_speaker_cap": max_utterances_per_speaker,
        "conditions": [_summarize_condition(rows, name)
                       for name, rows in conditions.items()],
        "privacy": {
            "raw_speaker_ids_exported": False,
            "utterance_ids_exported": False,
            "transcripts_exported": False,
            "demographics_exported": False,
            "per_utterance_results_exported": False,
            "raw_audio_copied": False,
        },
        "interpretation_limits": [
            "Mismatched pairs are a within-speaker null, not a universal null.",
            "A high matched-event count can reflect permissive monotone alignment even when correspondence is wrong.",
            "The frozen Build 15 report does not include these controls; read both files together.",
            "Detector-threshold stability is not tested by this run unless a sweep is also reported.",
        ],
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "build_15_controls.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    return report


def run_sweep(root, output, *, split="test", max_speakers=2,
              max_utterances_per_speaker=50, configs=None, seed=15):
    if configs is None:
        configs = [
            (10.0, 80.0),
            (20.0, 40.0),
            (20.0, 80.0),
            (20.0, 160.0),
            (40.0, 80.0),
        ]
    pairs = build_14.discover_pairs(root, split=split)
    by_speaker = {}
    for pair in pairs:
        by_speaker.setdefault(pair["speaker_internal"], []).append(pair)
    speakers = sorted(by_speaker)[:max_speakers]
    selected = []
    for speaker in speakers:
        items = sorted(by_speaker[speaker], key=lambda p: p["pair_key"])
        selected.append((speaker, items[:max_utterances_per_speaker]))

    results = []
    for frame_ms, min_gap_ms in configs:
        rows = []
        for speaker, items in selected:
            for pair in items:
                left = extract_event_stream_from_wav(
                    str(pair["throat_path"]), "throat",
                    frame_ms=frame_ms, min_gap_ms=min_gap_ms)
                right = extract_event_stream_from_wav(
                    str(pair["acoustic_path"]), "acoustic",
                    frame_ms=frame_ms, min_gap_ms=min_gap_ms)
                rows.append(dict(
                    {"speaker": speaker},
                    **_pair_metrics(
                        left, right, mark_weight=0.78, interval_weight=0.22)))
        summary = _summarize_condition(rows, f"frame_{frame_ms:g}ms_gap_{min_gap_ms:g}ms")
        summary["config"] = {"frame_ms": frame_ms, "min_gap_ms": min_gap_ms}
        results.append(summary)

    report = {
        "build": 15,
        "dataset": "TAPS paired throat-vibration / acoustic speech corpus",
        "split": split,
        "analysis_status": "detector_sweep_complete",
        "speakers_analyzed": len(selected),
        "utterances_per_speaker_cap": max_utterances_per_speaker,
        "pairs_per_config": sum(len(items) for _, items in selected),
        "configs": results,
        "privacy": {
            "raw_speaker_ids_exported": False,
            "utterance_ids_exported": False,
            "per_utterance_results_exported": False,
        },
        "interpretation_limits": [
            "The sweep uses a bounded subset, not the full held-out split.",
            "Detector settings change both event counts and matching difficulty; a stable metric across settings is stronger than a single best setting.",
        ],
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "build_15_detector_sweep.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="External controls for Build 15 TAPS")
    parser.add_argument("--root", required=True)
    parser.add_argument("--split", default="test", choices=("train", "dev", "test"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-speakers", type=int, default=None)
    parser.add_argument("--max-utterances-per-speaker", type=int, default=None)
    parser.add_argument("--null-shifts", type=int, nargs="+", default=[1, 37, 73])
    parser.add_argument("--frame-ms", type=float, default=20.0)
    parser.add_argument("--min-gap-ms", type=float, default=80.0)
    parser.add_argument("--mode", choices=("controls", "sweep", "both"), default="controls")
    args = parser.parse_args()
    payload = {}
    if args.mode in ("controls", "both"):
        payload["controls"] = run_controls(
            args.root, args.output, split=args.split,
            max_speakers=args.max_speakers,
            max_utterances_per_speaker=args.max_utterances_per_speaker,
            null_shifts=tuple(args.null_shifts),
            frame_ms=args.frame_ms, min_gap_ms=args.min_gap_ms)
    if args.mode in ("sweep", "both"):
        payload["sweep"] = run_sweep(
            args.root, args.output, split=args.split,
            max_speakers=args.max_speakers or 2,
            max_utterances_per_speaker=args.max_utterances_per_speaker or 50)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
