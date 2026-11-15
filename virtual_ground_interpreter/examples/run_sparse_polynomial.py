"""GEOMETRY-FIRST-003: query-efficient observation vs algebraic model proof.

Run from virtual_ground_interpreter: python examples/run_sparse_polynomial.py
"""
from __future__ import annotations
import json
from statistics import median
from time import perf_counter_ns

from vgi.geometry_first import FiniteGeometry
from vgi.polynomial_lift import TransitionSnapshot, discover_polynomial_lift, PolynomialLiftError
from vgi.sparse_polynomial import (
    SparseTransitionObservations, DeclaredPolynomialGround, certify_declared_model,
    fit_sparse_hypothesis, propose_rank_probes,
)


def measured(fn, count=7):
    samples = []
    result = None
    for _ in range(count):
        start = perf_counter_ns()
        result = fn()
        samples.append((perf_counter_ns() - start) / 1_000_000)
    return round(median(samples), 5), result


def run():
    p = 101
    geom = FiniteGeometry(p)
    declared = DeclaredPolynomialGround(
        p, "epsilon", 2,
        (((0, 2), 1), ((1, 0), 1)),
        (((0, 0), 1), ((0, 1), 1)),
        "synthetic-mathematical-ground",
    )
    queries = propose_rank_probes(p, 2)
    heldouts = (19*p+35, 79*p+16)
    selected = queries + heldouts
    observed = SparseTransitionObservations(
        p, "epsilon", tuple((q, geom.step(q, "epsilon")) for q in selected),
        source="synthetic-fixture", revision="geometry-first-003",
    )
    fit_ms, hypothesis = measured(lambda: fit_sparse_hypothesis(observed))
    symbolic_ms, cert = measured(lambda: certify_declared_model(hypothesis, declared))
    big = 10**30+11
    start_state = 39*p + 47
    jump_ms, destination = measured(lambda: cert.state_at(start_state,big))
    n=big
    expected = ((39 + n*47*47 + 47*n*(n-1) + n*(n-1)*(2*n-1)//6)%p,
                (47+n)%p)
    assert destination.coordinates == expected
    full_snapshot = TransitionSnapshot.capture(geom,"epsilon")
    full_ms, full_cert = measured(lambda: discover_polynomial_lift(full_snapshot,2), count=3)
    assert destination.state == full_cert.state_at(start_state,big).state
    # Perturb an unobserved state and exhibit observational ambiguity.
    unobserved = 50*p + 50
    assert unobserved not in selected
    tampered = (geom.step(unobserved,"epsilon") + p)%(p*p)
    rejected = False
    try:
        fit_sparse_hypothesis(SparseTransitionObservations(
            p,"epsilon", (*observed.edges,(unobserved,tampered)),
            source="synthetic-fixture",revision="geometry-first-003",
        ))
    except PolynomialLiftError:
        rejected=True
    assert rejected
    return {
        "experiment": "VGI-GEOMETRY-FIRST-003",
        "hypothesis": hypothesis.to_dict(),
        "certificate": cert.to_dict(),
        "large_time_result": destination.to_dict(),
        "algebra": {"independently_checked_destination":list(expected),
                    "matches_full_observation_certificate": True,
                    "outside_probe_counterexample_detected_when_observed": rejected},
        "costs": {
            "total_ground_states":p*p,
            "fit_samples":len(queries),
            "heldout_observations":len(heldouts),
            "partial_edges_observed":len(selected),
            "full_edges_observed":len(full_snapshot.targets),
            "observation_count_reduction":round(len(full_snapshot.targets)/len(selected),3),
            "timings_ms": {
                "sparse_fit_median":fit_ms,
                "symbolic_model_certificate_median":symbolic_ms,
                "sparse_certified_distant_query_median":jump_ms,
                "fully_observed_certificate_median":full_ms,
            },
        },
        "trust_scope": "only the declared mathematical polynomial Ground; samples cannot certify any unobserved external system",
        "status": "sample_hypothesis_plus_exact_symbolic_model_identity",
    }


if __name__ == "__main__":
    print(json.dumps(run(),sort_keys=True,indent=2))