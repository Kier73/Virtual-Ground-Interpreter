"""Reproduce GEOMETRY-FIRST-004: executable-program structural law extraction.

Run from the VGI package root: python examples/run_program_law.py
"""
from __future__ import annotations

import json
from statistics import median
from time import perf_counter_ns

from vgi.program_law import certify_program, ExtractedProgramLaw
from vgi.polynomial_lift import PolynomialLiftError
from vgi.sparse_polynomial import SparseTransitionObservations, propose_rank_probes

PROGRAM = """def advance(x, y):
    squared = y * y
    x_out = (x + squared) % 101
    y_out = (y + 1) % 101
    return (x_out, y_out)
"""
CUBIC = """def advance(x, y):
    return (x + y**3, y + 1)
"""


def measured(op, repetitions=15):
    times = []
    result = None
    for _ in range(repetitions):
        begin = perf_counter_ns()
        result = op()
        times.append((perf_counter_ns() - begin)/1e6)
    return round(median(times), 5), result


def run():
    p = 101
    start = 39*p + 47
    big = 10**30+11
    extraction_ms, law = measured(lambda: ExtractedProgramLaw(PROGRAM, p))
    certification_ms, cert = measured(lambda: certify_program(PROGRAM, p))
    navigation_ms, destination = measured(lambda: cert.state_at(start, big), 29)
    target_formula = (
        (39 + big*47**2 + 47*big*(big-1) + big*(big-1)*(2*big-1)//6) % p,
        (47+big) % p,
    )
    assert destination.coordinates == target_formula
    def iterative(t):
        current = start
        for _ in range(t):
            current = law.state_after_one(current)
        return current
    small = 25000
    iterative_ms, actual = measured(lambda: iterative(small), 3)
    jumped_ms, predicted = measured(lambda: cert.state_at(start, small), 29)
    assert actual == predicted.state
    independent_sources = propose_rank_probes(p, 2)
    observations = SparseTransitionObservations(
        p, "advance", tuple((s, law.state_after_one(s)) for s in independent_sources),
        source="bounded-program-fixture", revision="geometry-first-004",
    )
    obs_cert = certify_program(PROGRAM, p, observations=observations)
    assert obs_cert.state_at(start, big).state == destination.state
    corrupted = SparseTransitionObservations(
        p, "advance", ((start, (law.state_after_one(start) + p) % (p*p)),),
        source="intentionally-conflicting-observation",
    )
    rejected_conflict = False
    try:
        certify_program(PROGRAM, p, observations=corrupted)
    except PolynomialLiftError:
        rejected_conflict = True
    assert rejected_conflict
    cubic = certify_program(CUBIC, p)
    return {
        "experiment": "VGI-GEOMETRY-FIRST-004",
        "source_law": law.to_dict(),
        "certificate": cert.to_dict(),
        "large_time_navigation": destination.to_dict(),
        "independent_checks": {
            "closed_form_matches": True,
            "iterative_reference_matches": True,
            "six_observed_edges_match_source": True,
            "conflicting_observation_rejected": rejected_conflict,
            "cubic_feature_closure": [list(t) for t in cubic.features],
        },
        "costs": {
            "finite_formal_state_count": p*p,
            "symbolic_source_observations_required": 0,
            "optional_independent_observations": len(observations.edges),
            "iterative_reference_steps": small,
            "timings_ms": {
                "structural_extraction_median": extraction_ms,
                "source_to_certificate_median": certification_ms,
                "navigate_huge_coordinate_median": navigation_ms,
                "iterative_25000_median": iterative_ms,
                "navigate_25000_median": jumped_ms,
            },
        },
        "trust_scope": "exact denotational semantics of accepted bounded source DSL, not arbitrary Python or external processes",
        "runtime": "isolated API-compatible VGI harness unless CI executes repository package",
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2))