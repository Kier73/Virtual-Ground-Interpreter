"""Reproducible geometry-first discovery, time, placement and matrix probe."""
import json
import random
from statistics import median
from time import perf_counter

from vgi.geometry_first import (
    CertifiedGeometryNavigator, CodonRequirement, DeferredMatrixProduct,
    FiniteGeometry, GeometryError, bind_registry, discover_commutations,
    naive_product, place_dependency_graph,
)


def measured(call, repeats=5):
    elapsed = []
    result = None
    for _ in range(repeats):
        start = perf_counter()
        result = call()
        elapsed.append((perf_counter() - start) * 1000)
    return result, round(median(elapsed), 5)


def run():
    geometry = FiniteGeometry(100)  # 10,000 independently addressable points
    certificate, preprocessing_ms = measured(lambda: CertifiedGeometryNavigator(geometry), 3)
    labels = [geometry.opaque_addresses(seed) for seed in ("A", "B", "C")]
    laws = {law.action: law for law in certificate.laws}
    first_registry = (
        CodonRequirement("increment_first", True, displacement=(1, 0)),
        CodonRequirement("increment_second", True, displacement=(0, 1)),
        CodonRequirement("erase_first", False, idempotent=True),
    )
    second_registry = (
        CodonRequirement("row", True, displacement=(1, 0)),
        CodonRequirement("column", True, displacement=(0, 1)),
        CodonRequirement("collapse", False, idempotent=True),
    )
    deps = [()] + [(i - 1,) if i % 4 else (i - 1, i - 3)
                   for i in range(1, 48)]
    (random_positions, random_cost), random_placement_ms = measured(
        lambda: place_dependency_graph(geometry, deps, seed=1001, guided=False))
    (guided_positions, guided_cost), guided_placement_ms = measured(
        lambda: place_dependency_graph(geometry, deps, seed=1001, guided=True))

    big = 10**30 + 11
    (target, time_query_ms) = measured(
        lambda: certificate.state_at("delta", 1234, big), 7)
    try:
        certificate.state_at("epsilon", 1234, big)
        nonlinear_status = "incorrectly_admitted"
    except GeometryError:
        nonlinear_status = "unresolved_no_verified_shortcut"

    rng = random.Random(20261114)
    size, modulus = 48, 97
    a = [[rng.randrange(modulus) for _ in range(size)] for __ in range(size)]
    b = [[rng.randrange(modulus) for _ in range(size)] for __ in range(size)]
    vector = [rng.randrange(modulus) for _ in range(size)]
    deferred, admission_ms = measured(
        lambda: DeferredMatrixProduct.from_operands(a, b, modulus), 5)
    one_entry, entry_ms = measured(lambda: deferred.entry(10, 17), 7)
    vector_answer, vector_ms = measured(lambda: deferred.apply_vector(vector), 7)
    dense_answer, dense_ms = measured(
        lambda: naive_product(deferred.left, deferred.right, modulus), 5)
    _, full_lazy_ms = measured(lambda: deferred.materialize(), 3)
    assert deferred.materialize() == dense_answer
    assert one_entry == dense_answer[10][17]
    assert vector_answer == tuple(sum(row[k] * vector[k] for k in range(size)) % modulus
                                  for row in dense_answer)

    return {
        "experiment": "VGI-GEOMETRY-FIRST-001",
        "reproduction": {"geometry_side": geometry.side, "points": 10000,
                         "matrix_dimension": size, "modulus": modulus,
                         "rng_seed": 20261114, "benchmark_unit": "milliseconds_median",
                         "benchmark_note": "Python reference runtime only; no cross-machine speed claim"},
        "geometry": {
            "fingerprint": geometry.fingerprint,
            "certificate_fingerprint": certificate.certificate_fingerprint,
            "checked_edges": sum(l.complete_edges_checked for l in certificate.laws),
            "preprocessing_ms": preprocessing_ms,
            "opaque_label_sets": len(labels),
            "all_label_sets_distinct": all(labels[i][p] != labels[j][p]
                                            for p in range(10000)
                                            for i in range(3) for j in range(i + 1, 3)),
            "registry_a_bindings": bind_registry(laws, first_registry),
            "registry_b_bindings": bind_registry(laws, second_registry),
            "observed_laws": [
                {"action": law.action,
                 "bijective": law.bijective,
                 "idempotent": law.idempotent,
                 "uniform_displacement": law.uniform_displacement,
                 "period": law.orbit_period,
                 "affine_matrix": law.affine_matrix,
                 "affine_offset": law.affine_offset,
                 "checked_points": law.complete_edges_checked}
                for law in certificate.laws
            ],
            "commutations": {f"{a},{b}": result for (a, b), result
                             in discover_commutations(geometry).items()},
        },
        "placement": {
            "codons": len(deps), "dependencies": sum(map(len, deps)),
            "random_total_edge_distance": random_cost,
            "guided_total_edge_distance": guided_cost,
            "random_ms": random_placement_ms,
            "guided_ms": guided_placement_ms,
            "same_number_of_distinct_positions": len(set(random_positions)) == len(set(guided_positions)) == len(deps),
            "important": "This improves only declared geometric locality, not computational result correctness"
        },
        "logical_time": {"action": "delta", "tick": str(big),
                         "starting_point": 1234, "target_point": target,
                         "query_ms_after_certification": time_query_ms,
                         "nonlinear_control": nonlinear_status,
                         "materialized_intermediate_states": 0},
        "dynamic_matrix": {"dimension": size, "modulus": modulus,
                           "deferred_context_fingerprint": deferred.context_fingerprint,
                           "operand_admission_ms": admission_ms,
                           "one_entry_ms": entry_ms,
                           "one_vector_ms": vector_ms,
                           "dense_AB_reference_ms": dense_ms,
                           "deferred_full_materialization_ms": full_lazy_ms,
                           "all_answers_match_independent_dense_reference": True,
                           "cost_notes": "One entry O(n), vector O(n^2), full AB O(n^3), plus O(n^2) operand admission"}
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))