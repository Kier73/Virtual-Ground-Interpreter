"""Run the GEOMETRY-FIRST-002 finite-domain polynomial lift experiment.

From virtual_ground_interpreter: python examples/run_polynomial_lift.py
"""
from __future__ import annotations

import json
import statistics
import time

from vgi.geometry_first import FiniteGeometry
from vgi.polynomial_lift import (
    PolynomialLiftError, TransitionSnapshot, discover_polynomial_lift,
)


def milliseconds(callable_, repeats=7):
    spans = []
    last = None
    for _ in range(repeats):
        started = time.perf_counter_ns()
        last = callable_()
        spans.append((time.perf_counter_ns() - started) / 1e6)
    return statistics.median(spans), last


def direct(snapshot, start, count):
    state = start
    for _ in range(count):
        state = snapshot.targets[state]
    return state


def run():
    geom = FiniteGeometry(101)
    snapshot = TransitionSnapshot.capture(geom, "epsilon")
    discovery_ms, cert = milliseconds(lambda: discover_polynomial_lift(snapshot), repeats=3)
    long_time = 10**30 + 11
    origin = geom.address((39, 47))
    jump_ms, distant = milliseconds(lambda: cert.state_at(origin, long_time))
    short_time = 250_000
    baseline_ms, baseline_state = milliseconds(lambda: direct(snapshot, origin, short_time), repeats=3)
    short_ms, short_result = milliseconds(lambda: cert.state_at(origin, short_time))
    assert baseline_state == short_result.state
    # This closed form is a separate mathematical control, not part of discovery.
    n = long_time
    sum_squares = n * (n - 1) * (2 * n - 1) // 6
    correct = ((39 + n * 47**2 + 47 * n * (n - 1) + sum_squares) % 101,
               (47 + n) % 101)
    assert distant.coordinates == correct
    degree_one_refused = False
    try:
        discover_polynomial_lift(snapshot, max_degree=1)
    except PolynomialLiftError:
        degree_one_refused = True
    assert degree_one_refused
    result = {
        "experiment": "VGI-GEOMETRY-FIRST-002",
        "source": {"geometry": "finite torus / F_101^2",
                   "action": snapshot.action,
                   "snapshot_fingerprint": snapshot.fingerprint,
                   "observed_edges": len(snapshot.targets)},
        "discovery": {
            "feature_exponents": [list(f) for f in cert.features],
            "affine_matrix": [list(row) for row in cert.transform.matrix],
            "affine_offset": list(cert.transform.offset),
            "fitting_probes": len(cert.fit_probes),
            "exhaustive_edge_checks": len(snapshot.targets),
            "certificate_fingerprint": cert.fingerprint,
            "degree_one_rejected": degree_one_refused,
        },
        "timings_ms": {"discovery_and_certification_median": round(discovery_ms, 5),
                       "verified_distant_navigation_median": round(jump_ms, 5),
                       "direct_250000_steps_median": round(baseline_ms, 5),
                       "navigated_250000_steps_median": round(short_ms, 5)},
        "distant_query": distant.to_dict(),
        "consistency": {"direct_250000_equals_navigated": True,
                        "distant_matches_independent_closed_form": True},
        "scope": "certified finite-field synthetic Ground, logical time not elapsed time",
    }
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))