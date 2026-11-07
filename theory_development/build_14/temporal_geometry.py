#!/usr/bin/env python3
"""Temporal-emission descriptors for Build 14.

A state/process is not assumed to emit physical time. Instead, an observer
extracts event-like landmarks from a measured signal and studies their timing
relationships. In this build, landmarks are local maxima of a short-time RMS
amplitude envelope; they are proxies, not known hidden-state transitions.
"""
from __future__ import annotations

import math
import statistics
from typing import Sequence


def percentile(values: Sequence[float], q: float) -> float:
    xs = sorted(float(v) for v in values if math.isfinite(float(v)))
    if not xs:
        return 0.0
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def detect_envelope_events(
    envelope: Sequence[float], frame_ms: float = 20.0, min_gap_ms: float = 80.0
) -> tuple[list[float], list[float]]:
    """Return selected local-maximum times and normalized envelope marks.

    Selection threshold is the larger of the 60th percentile and median plus
    0.5 MAD. Candidates are greedily separated by min_gap_ms, preferring the
    largest peak in each local interval. This is a reproducible landmark rule,
    not a phoneme detector or a claim that every peak denotes a state change.
    """
    if frame_ms <= 0 or min_gap_ms < 0:
        raise ValueError("frame_ms must be positive and min_gap_ms nonnegative")
    x = [max(0.0, float(v)) for v in envelope]
    if any(not math.isfinite(v) for v in x):
        raise ValueError("envelope contains non-finite values")
    if len(x) < 3 or max(x, default=0.0) <= 0:
        return [], []
    med = statistics.median(x)
    mad = statistics.median(abs(v - med) for v in x)
    threshold = max(percentile(x, 0.60), med + 0.5 * mad)
    candidates = [
        i for i in range(1, len(x) - 1)
        if x[i] >= threshold and x[i] >= x[i - 1] and x[i] > x[i + 1]
    ]
    min_gap_frames = max(1, int(math.ceil(min_gap_ms / frame_ms)))
    chosen: list[int] = []
    for idx in sorted(candidates, key=lambda i: (-x[i], i)):
        if all(abs(idx - prev) >= min_gap_frames for prev in chosen):
            chosen.append(idx)
    chosen.sort()
    times = [i * frame_ms / 1000.0 for i in chosen]
    peak = max(x)
    marks = [x[i] / peak for i in chosen]
    return times, marks


def event_time_signature(
    event_times_s: Sequence[float],
    event_marks: Sequence[float] | None = None,
    duration_s: float | None = None,
) -> dict:
    """Summarize event timing with absolute-rate and affine-invariant parts.

    Translation of the time origin leaves all outputs unchanged. Multiplying
    all times and duration by c>0 preserves normalized interval descriptors
    while dividing rate by c. Event marks are normalized by their own maximum.
    """
    times = [float(t) for t in event_times_s]
    if any(not math.isfinite(t) for t in times):
        raise ValueError("event_times_s contains non-finite values")
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("event times must be strictly increasing")
    if duration_s is not None and (not math.isfinite(duration_s) or duration_s <= 0):
        raise ValueError("duration_s must be finite and positive")
    marks = list(event_marks) if event_marks is not None else [1.0] * len(times)
    if len(marks) != len(times):
        raise ValueError("event_marks length must match event_times_s")
    if any(not math.isfinite(float(m)) or float(m) < 0 for m in marks):
        raise ValueError("event marks must be finite and nonnegative")

    intervals = [b - a for a, b in zip(times, times[1:])]
    med_i = statistics.median(intervals) if intervals else 0.0
    normalized = [round(v / med_i, 10) for v in intervals] if med_i > 0 else []
    mean_i = statistics.mean(intervals) if intervals else 0.0
    sd_i = statistics.pstdev(intervals) if len(intervals) > 1 else 0.0
    bins = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, math.inf)
    entropy = 0.0
    if normalized:
        counts = [0] * (len(bins) - 1)
        for value in normalized:
            for j in range(len(bins) - 1):
                if bins[j] <= value < bins[j + 1]:
                    counts[j] += 1
                    break
        n = len(normalized)
        probs = [c / n for c in counts if c]
        entropy = -sum(p * math.log(p) for p in probs) / math.log(len(bins) - 1)

    norm_marks: list[float] = []
    if marks:
        mark_max = max(float(m) for m in marks)
        norm_marks = [float(m) / mark_max for m in marks] if mark_max > 0 else [0.0] * len(marks)
    mark_mean = statistics.mean(norm_marks) if norm_marks else 0.0
    mark_cv = (statistics.pstdev(norm_marks) / mark_mean
               if len(norm_marks) > 1 and mark_mean > 0 else 0.0)
    duration = float(duration_s) if duration_s is not None else (times[-1] - times[0] if len(times) > 1 else 0.0)
    rate = len(times) / duration if duration > 0 else 0.0

    return {
        "event_count": float(len(times)),
        "event_rate_hz": rate,
        "event_interval_median_s": med_i,
        "event_interval_cv": sd_i / mean_i if mean_i > 0 else 0.0,
        "event_interval_entropy": entropy,
        "event_interval_q10_norm": percentile(normalized, 0.10),
        "event_interval_q25_norm": percentile(normalized, 0.25),
        "event_interval_q50_norm": percentile(normalized, 0.50),
        "event_interval_q75_norm": percentile(normalized, 0.75),
        "event_interval_q90_norm": percentile(normalized, 0.90),
        "event_mark_cv_norm": mark_cv,
    }


def summarize_envelope(
    envelope: Sequence[float], frame_ms: float = 20.0, duration_s: float | None = None,
    min_gap_ms: float = 80.0,
) -> dict:
    times, marks = detect_envelope_events(envelope, frame_ms=frame_ms, min_gap_ms=min_gap_ms)
    if duration_s is None:
        duration_s = len(envelope) * frame_ms / 1000.0
    return event_time_signature(times, marks, duration_s=duration_s)


def affine_invariance_probe(event_times_s: Sequence[float], event_marks: Sequence[float] | None = None) -> dict:
    """Numerically check origin/gain/time-scale behavior on a supplied event set."""
    if len(event_times_s) < 3:
        raise ValueError("at least three event times are needed")
    duration = max(event_times_s[-1] + 0.5, 1.0)
    base = event_time_signature(event_times_s, event_marks, duration)
    offset = 17.25
    shifted = event_time_signature([t + offset for t in event_times_s], event_marks, duration)
    scale = 3.5
    dilated = event_time_signature([t * scale for t in event_times_s], event_marks, duration * scale)
    shape_keys = (
        "event_interval_cv", "event_interval_entropy", "event_interval_q10_norm",
        "event_interval_q25_norm", "event_interval_q50_norm",
        "event_interval_q75_norm", "event_interval_q90_norm", "event_mark_cv_norm",
    )
    shift_error = max(abs(base[k] - shifted[k]) for k in shape_keys)
    dilation_error = max(abs(base[k] - dilated[k]) for k in shape_keys)
    expected_rate = base["event_rate_hz"] / scale
    rate_scale_error = abs(dilated["event_rate_hz"] - expected_rate)
    return {
        "time_origin_invariance_max_abs_error": shift_error,
        "clock_scale_shape_invariance_max_abs_error": dilation_error,
        "clock_scale_rate_relation_abs_error": rate_scale_error,
        "clock_scale": scale,
        "expected_rate_after_scale_hz": expected_rate,
        "observed_rate_after_scale_hz": dilated["event_rate_hz"],
        "status": "passed" if max(shift_error, dilation_error, rate_scale_error) < 1e-10 else "failed",
    }
