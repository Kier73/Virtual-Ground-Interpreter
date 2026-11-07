#!/usr/bin/env python3
"""Build 15 synthetic event-graph stress test; no human data is generated."""
from __future__ import annotations
import json, math, random, statistics, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_clock_graph import EventStream, affine_clock_transform, analyze_stream_pair


def median(xs): return statistics.median(xs) if xs else 0.0

def quantile(xs, q):
    if not xs: return 0.0
    ys = sorted(xs); p = (len(ys)-1)*q; lo=math.floor(p); hi=math.ceil(p)
    return ys[lo] if lo == hi else ys[lo]*(hi-p)+ys[hi]*(p-lo)


def make_trial(seed: int, n: int = 50):
    rng = random.Random(seed + 500)
    times = [0.0]
    for _ in range(n-1): times.append(times[-1] + rng.uniform(0.22, 0.91))
    marks = [0.2 + 0.8*rng.random() for _ in times]
    left = EventStream("observer_A", tuple(times), tuple(marks), times[-1] + 1.0)
    offset, scale = 17.0, 2.75
    retained = [(t, m, i) for i, (t, m) in enumerate(zip(times, marks)) if rng.random() > 0.10]
    right_rows = [(offset + scale*t + rng.gauss(0, 0.003),
                   1.7 + 3.1*m + rng.gauss(0, 0.01), i)
                  for t, m, i in retained]
    for _ in range(5):
        false_t = rng.uniform(times[0], times[-1])
        right_rows.append((offset + scale*false_t, 1.7 + 3.1*rng.random(), None))
    right_rows.sort(key=lambda row: row[0])
    right = EventStream("observer_B", tuple(x[0] for x in right_rows),
                        tuple(x[1] for x in right_rows),
                        offset + scale * (times[-1] + 1.0))
    result = analyze_stream_pair(left, right)
    predicted = {(m["left_index"], m["right_index"]) for m in result["alignment"]["matches"]}
    truth = {(original, j) for j, (_, _, original) in enumerate(right_rows) if original is not None}
    tp = len(predicted & truth); fp = len(predicted - truth); fn = len(truth - predicted)
    precision = tp / max(1, tp + fp); recall = tp / max(1, tp + fn)
    f1 = 2*precision*recall/max(1e-12, precision+recall)
    fit = result["post_match_clock_relation"]
    relation = fit.get("left_time_approximately_equals_offset_plus_scale_times_right_time", {})
    return {
        "precision": precision, "recall": recall, "f1": f1,
        "left_coverage": result["alignment"]["left_coverage"],
        "right_coverage": result["alignment"]["right_coverage"],
        "post_match_inverse_clock_scale_estimate": relation.get("scale"),
        "post_match_clock_median_absolute_residual_s": fit.get("median_absolute_residual_s"),
        "expected_inverse_clock_scale": 1.0/scale,
        "event_count_A": len(times), "event_count_B": len(right_rows),
        "dropout_fraction": 0.10, "false_events": 5,
    }


def main():
    trials = [make_trial(i) for i in range(30)]
    summary = {}
    for key in ("precision", "recall", "f1", "left_coverage", "right_coverage",
                "post_match_inverse_clock_scale_estimate",
                "post_match_clock_median_absolute_residual_s"):
        vals = [float(t[key]) for t in trials if t[key] is not None]
        summary[key] = {"mean": statistics.mean(vals) if vals else 0.0,
                        "median": median(vals),
                        "q10": quantile(vals, 0.10), "q90": quantile(vals, 0.90)}
    report = {
        "build": 15,
        "provenance": "synthetic_event_fixture_only",
        "trials": len(trials),
        "scenario": {
            "latent_events_per_trial": 50,
            "observer_B_clock": "17.0 + 2.75 * latent_time + Gaussian_jitter(sd=0.003s)",
            "mark_transform_B": "1.7 + 3.1 * latent_mark + Gaussian_noise(sd=0.01)",
            "event_dropout_probability": 0.10,
            "false_events_per_trial": 5,
            "matching_uses_absolute_cross_clock_times": False,
            "ground_truth_available_for_metrics": True,
        },
        "aggregate": summary,
        "trial_results": trials,
        "interpretation": [
            "Synthetic ground truth allows precision/recall calculation; this is a controlled software check, not an empirical sensor result.",
            "The matcher relies on monotone event order and sufficiently informative relative event marks.",
            "The affine clock relation is estimated only after event matching.",
        ],
    }
    out = ROOT / "reports" / "synthetic_local_clock_stress.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"trials":len(trials),"f1_mean":summary["f1"]["mean"],
                      "precision_mean":summary["precision"]["mean"],
                      "recall_mean":summary["recall"]["mean"],
                      "clock_residual_median_s":summary["post_match_clock_median_absolute_residual_s"]["median"],
                      "report":str(out)}, indent=2))

if __name__ == "__main__": main()
