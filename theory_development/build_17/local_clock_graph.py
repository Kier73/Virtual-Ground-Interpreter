#!/usr/bin/env python3
"""Build 15: event-graph comparison across independently timed observers.

No absolute cross-observer timestamps are used by the matcher. Each observer
retains its local event times; event matching is sequence/order based and uses
normalized event-mark and interval-shape descriptors. An affine clock relation
may be estimated *after* matching, but it is diagnostic rather than a matching
prerequisite.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import Iterable, Sequence


@dataclass(frozen=True)
class EventStream:
    observer: str
    local_times_s: tuple[float, ...]
    marks: tuple[float, ...]
    duration_s: float | None = None

    def validate(self) -> None:
        if not self.observer or not isinstance(self.observer, str):
            raise ValueError("observer must be a non-empty string")
        if len(self.local_times_s) != len(self.marks):
            raise ValueError("event times and marks must have equal length")
        if any(not math.isfinite(float(t)) for t in self.local_times_s):
            raise ValueError("event times must be finite")
        if any(b <= a for a, b in zip(self.local_times_s, self.local_times_s[1:])):
            raise ValueError("event times must be strictly increasing")
        if any(not math.isfinite(float(m)) for m in self.marks):
            raise ValueError("event marks must be finite")
        if self.duration_s is not None and (not math.isfinite(self.duration_s) or self.duration_s <= 0):
            raise ValueError("duration_s must be finite and positive")
        if self.duration_s is not None and self.local_times_s:
            if self.duration_s < self.local_times_s[-1] - self.local_times_s[0]:
                raise ValueError("duration_s cannot be shorter than the event span")


def _rank_fraction(values: Sequence[float]) -> list[float]:
    """Average ranks mapped to [0,1], invariant to strictly monotone marks."""
    n = len(values)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: (float(values[i]), i))
    result = [0.0] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and float(values[order[j]]) == float(values[order[i]]):
            j += 1
        average_rank = (i + 1 + j) / 2.0
        frac = (average_rank - 1.0) / max(1, n - 1)
        for k in range(i, j):
            result[order[k]] = frac
        i = j
    return result


def _median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else 0.0


def _interval_features(stream: EventStream) -> list[float]:
    times = stream.local_times_s
    gaps = [b - a for a, b in zip(times, times[1:])]
    if not gaps:
        return [0.0] * len(times)
    med = _median(gaps)
    normalized = [math.log(max(g / med, 1e-12)) for g in gaps]
    # Give endpoints their sole adjacent interval; internal events average
    # adjacent log intervals to avoid privileging either side of a landmark.
    out = [normalized[0]]
    for i in range(1, len(times) - 1):
        out.append(0.5 * (normalized[i - 1] + normalized[i]))
    out.append(normalized[-1])
    return [max(-3.0, min(3.0, x)) for x in out]


def event_features(stream: EventStream) -> list[dict[str, float]]:
    stream.validate()
    ranks = _rank_fraction(stream.marks)
    intervals = _interval_features(stream)
    return [{"mark_rank": ranks[i], "interval_log_shape": intervals[i]}
            for i in range(len(ranks))]


def _match_cost(a: dict[str, float], b: dict[str, float],
                mark_weight: float, interval_weight: float) -> float:
    mark_delta = abs(a["mark_rank"] - b["mark_rank"])
    interval_delta = min(abs(a["interval_log_shape"] - b["interval_log_shape"]) / 2.0, 1.0)
    return mark_weight * mark_delta + interval_weight * interval_delta


def align_event_streams(
    left: EventStream,
    right: EventStream,
    *,
    gap_penalty: float = 0.36,
    mark_weight: float = 0.78,
    interval_weight: float = 0.22,
) -> dict:
    """Monotone sequence alignment without a shared timestamp coordinate.

    A Needleman-Wunsch edit path matches, skips-left, or skips-right events.
    Marks are compared by within-stream rank; intervals by log-ratio shape.
    ``local_times_s`` are never compared directly by this matcher.
    """
    left.validate(); right.validate()
    if gap_penalty <= 0:
        raise ValueError("gap_penalty must be positive")
    if mark_weight < 0 or interval_weight < 0 or abs(mark_weight + interval_weight - 1.0) > 1e-9:
        raise ValueError("feature weights must be nonnegative and sum to one")

    fa, fb = event_features(left), event_features(right)
    n, m = len(fa), len(fb)
    # Full dynamic-programming matrix; audio utterance event counts are expected
    # to be modest. An explicit guard prevents accidental quadratic blowups.
    if n * m > 4_000_000:
        raise ValueError("event alignment exceeds 4,000,000 DP cells")
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    back = [[""] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i * gap_penalty
        back[i][0] = "L"
    for j in range(1, m + 1):
        dp[0][j] = j * gap_penalty
        back[0][j] = "R"

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            mc = _match_cost(fa[i - 1], fb[j - 1], mark_weight, interval_weight)
            options = (
                (dp[i - 1][j - 1] + mc, 0, "M"),
                (dp[i - 1][j] + gap_penalty, 1, "L"),
                (dp[i][j - 1] + gap_penalty, 2, "R"),
            )
            best = min(options, key=lambda z: (z[0], z[1]))
            dp[i][j], _, back[i][j] = best

    i, j = n, m
    matches: list[dict] = []
    skipped_left: list[int] = []
    skipped_right: list[int] = []
    while i or j:
        step = back[i][j]
        if step == "M":
            cost = _match_cost(fa[i - 1], fb[j - 1], mark_weight, interval_weight)
            matches.append({"left_index": i - 1, "right_index": j - 1,
                            "cost": cost, "confidence": 1.0 - cost})
            i -= 1; j -= 1
        elif step == "L":
            skipped_left.append(i - 1); i -= 1
        elif step == "R":
            skipped_right.append(j - 1); j -= 1
        else:
            raise RuntimeError(f"invalid traceback state at {(i, j)}")
    matches.reverse(); skipped_left.reverse(); skipped_right.reverse()

    denom_l, denom_r = max(1, n), max(1, m)
    return {
        "matches": matches,
        "skipped_left": skipped_left,
        "skipped_right": skipped_right,
        "left_count": n,
        "right_count": m,
        "matched_count": len(matches),
        "left_coverage": len(matches) / denom_l if n else 0.0,
        "right_coverage": len(matches) / denom_r if m else 0.0,
        "median_match_cost": _median([x["cost"] for x in matches]),
        "total_alignment_cost": dp[n][m],
        "normalized_alignment_cost": dp[n][m] / max(1, n + m),
        "clock_assumption": "independent_local_clocks; no timestamp synchronization used for matching",
    }


def _theil_sen_clock_relation(left: EventStream, right: EventStream,
                               matches: Sequence[dict]) -> dict:
    """Robustly estimate left_time ~= offset + scale * right_time post-match."""
    points = [(right.local_times_s[x["right_index"]], left.local_times_s[x["left_index"]])
              for x in matches]
    if len(points) < 2:
        return {"status": "insufficient_matches", "matched_points": len(points)}
    slopes = []
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            dx = points[j][0] - points[i][0]
            if abs(dx) > 1e-12:
                slopes.append((points[j][1] - points[i][1]) / dx)
    if not slopes:
        return {"status": "degenerate_local_times", "matched_points": len(points)}
    scale = _median(slopes)
    offset = _median([y - scale * x for x, y in points])
    residuals = [y - (offset + scale * x) for x, y in points]
    return {
        "status": "estimated_from_event_correspondence",
        "matched_points": len(points),
        "left_time_approximately_equals_offset_plus_scale_times_right_time": {
            "offset_s": offset, "scale": scale,
        },
        "median_absolute_residual_s": _median([abs(x) for x in residuals]),
        "max_absolute_residual_s": max((abs(x) for x in residuals), default=0.0),
        "warning": "post-match diagnostic; not used to create the event matches",
    }


def _spearman(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) < 3:
        return 0.0
    rx, ry = _rank_fraction(x), _rank_fraction(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    dx, dy = [v - mx for v in rx], [v - my for v in ry]
    sx, sy = sum(v*v for v in dx), sum(v*v for v in dy)
    if sx <= 1e-15 or sy <= 1e-15:
        return 0.0
    return sum(a*b for a, b in zip(dx, dy)) / math.sqrt(sx * sy)


def _matched_interval_agreement(left: EventStream, right: EventStream,
                                matches: Sequence[dict]) -> dict:
    if len(matches) < 4:
        return {"status": "insufficient_matched_events", "matched_events": len(matches)}
    left_gaps, right_gaps = [], []
    for p, q in zip(matches, matches[1:]):
        li, ri = p["left_index"], q["left_index"]
        lj, rj = p["right_index"], q["right_index"]
        if ri <= li or rj <= lj:
            continue
        left_gaps.append(left.local_times_s[ri] - left.local_times_s[li])
        right_gaps.append(right.local_times_s[rj] - right.local_times_s[lj])
    if len(left_gaps) < 3:
        return {"status": "insufficient_matched_transitions", "matched_transitions": len(left_gaps)}
    med_l, med_r = _median(left_gaps), _median(right_gaps)
    nl = [math.log(max(v / med_l, 1e-12)) for v in left_gaps]
    nr = [math.log(max(v / med_r, 1e-12)) for v in right_gaps]
    return {
        "status": "computed",
        "matched_transitions": len(left_gaps),
        "normalized_interval_spearman": _spearman(nl, nr),
        "median_absolute_log_interval_difference": _median([abs(a-b) for a, b in zip(nl, nr)]),
    }


def _motif_edges(stream: EventStream, tolerance: float = 0.18) -> list[dict]:
    gaps = [b - a for a, b in zip(stream.local_times_s, stream.local_times_s[1:])]
    if len(gaps) < 4:
        return []
    med = _median(gaps)
    motifs = [(math.log(max(gaps[i] / med, 1e-12)),
               math.log(max(gaps[i + 1] / med, 1e-12))) for i in range(len(gaps) - 1)]
    edges = []
    for i in range(len(motifs)):
        for j in range(i + 3, len(motifs)):
            d = math.sqrt((motifs[i][0]-motifs[j][0])**2 + (motifs[i][1]-motifs[j][1])**2)
            if d <= tolerance:
                # Edge links the start events of recurring two-gap motifs.
                edges.append({"source_index": i, "target_index": j, "type": "recurrence",
                              "motif_distance": d})
    return edges


def build_event_graph(left: EventStream, right: EventStream, alignment: dict) -> dict:
    """Build a two-observer temporal graph with local order and correspondence.

    Each observer has a directed successor chain. Recurrence edges connect
    similar two-interval motifs. Cross-observer edges are inferred event matches.
    There are intentionally no cross-observer timestamp-difference edges.
    """
    left.validate(); right.validate()
    nodes = []
    edges = []
    for stream, prefix in ((left, "L"), (right, "R")):
        feats = event_features(stream)
        for i, t in enumerate(stream.local_times_s):
            nodes.append({"id": f"{prefix}:{i}", "observer": stream.observer,
                          "local_index": i, "local_time_s": float(t),
                          "mark_rank": feats[i]["mark_rank"],
                          "interval_log_shape": feats[i]["interval_log_shape"]})
        gaps = [b-a for a, b in zip(stream.local_times_s, stream.local_times_s[1:])]
        med_gap = _median(gaps)
        for i, gap in enumerate(gaps):
            edges.append({"source": f"{prefix}:{i}", "target": f"{prefix}:{i+1}",
                          "type": "successor", "normalized_interval": gap / med_gap if med_gap else 0.0})
        for edge in _motif_edges(stream):
            edges.append({"source": f"{prefix}:{edge['source_index']}",
                          "target": f"{prefix}:{edge['target_index']}",
                          "type": "recurrence", "motif_distance": edge["motif_distance"]})
    for match in alignment["matches"]:
        edges.append({"source": f"L:{match['left_index']}",
                      "target": f"R:{match['right_index']}",
                      "type": "correspondence", "cost": match["cost"],
                      "confidence": match["confidence"]})
    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "successor_edge_count": sum(e["type"] == "successor" for e in edges),
        "recurrence_edge_count": sum(e["type"] == "recurrence" for e in edges),
        "correspondence_edge_count": sum(e["type"] == "correspondence" for e in edges),
        "cross_observer_clock_edges": 0,
        "design_note": "observer-local event order is explicit; absolute cross-clock differences are absent",
    }


def analyze_stream_pair(left: EventStream, right: EventStream) -> dict:
    alignment = align_event_streams(left, right)
    graph = build_event_graph(left, right, alignment)
    clock_relation = _theil_sen_clock_relation(left, right, alignment["matches"])
    interval_agreement = _matched_interval_agreement(left, right, alignment["matches"])
    left_ranks = event_features(left)
    right_ranks = event_features(right)
    mark_corr = _spearman(
        [left_ranks[m["left_index"]]["mark_rank"] for m in alignment["matches"]],
        [right_ranks[m["right_index"]]["mark_rank"] for m in alignment["matches"]],
    )
    return {
        "left_observer": left.observer,
        "right_observer": right.observer,
        "alignment": alignment,
        "interval_agreement": interval_agreement,
        "matched_mark_rank_spearman": mark_corr,
        "post_match_clock_relation": clock_relation,
        "graph": graph,
        "interpretation": "Correspondence is inferred from order and normalized event features; it is not a verified latent-state identity.",
    }


def affine_clock_transform(times: Sequence[float], offset_s: float, scale: float) -> list[float]:
    if not math.isfinite(offset_s) or not math.isfinite(scale) or scale <= 0:
        raise ValueError("offset must be finite and scale must be finite and positive")
    return [offset_s + scale * float(t) for t in times]


def graph_topology_signature(stream: EventStream) -> dict:
    """Single-stream topology summary independent of time origin and clock scale."""
    stream.validate()
    gaps = [b-a for a, b in zip(stream.local_times_s, stream.local_times_s[1:])]
    med = _median(gaps)
    norm = [g/med for g in gaps] if med else []
    motifs = _motif_edges(stream)
    return {
        "event_count": len(stream.local_times_s),
        "successor_edges": max(0, len(stream.local_times_s)-1),
        "recurrence_edges": len(motifs),
        "normalized_interval_cv": (statistics.pstdev(norm) / statistics.mean(norm)
                                    if len(norm) > 1 and statistics.mean(norm) else 0.0),
        "normalized_interval_median": _median(norm),
        "normalized_interval_q25": _quantile(norm, 0.25),
        "normalized_interval_q75": _quantile(norm, 0.75),
        "recurrence_density": len(motifs) / max(1, len(norm)*(len(norm)-1)/2),
    }


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(float(v) for v in values)
    pos = (len(xs)-1)*q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return xs[lo] if lo == hi else xs[lo]*(hi-pos)+xs[hi]*(pos-lo)


def extract_event_stream_from_wav(path: str, observer: str,
                                  *, frame_ms: float = 20.0,
                                  min_gap_ms: float = 80.0) -> EventStream:
    """Use Build 14's measured-envelope event rule on one mono WAV."""
    from pathlib import Path
    import build_14
    import temporal_geometry
    wav = build_14.read_wav(Path(path))
    centered_mean = sum(wav.samples) / len(wav.samples)
    centered = [v - centered_mean for v in wav.samples]
    env = build_14._envelope(centered, wav.sample_rate, frame_ms=frame_ms)
    times, marks = temporal_geometry.detect_envelope_events(
        env, frame_ms=frame_ms, min_gap_ms=min_gap_ms)
    return EventStream(observer=observer, local_times_s=tuple(times), marks=tuple(marks),
                       duration_s=len(wav.samples) / wav.sample_rate)
