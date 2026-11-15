"""Reproducible GEOMETRY-FIRST-005 reference benchmark, no external packages."""
from __future__ import annotations

import json
import random
import statistics
import time

from vgi.typed_operator_navigation import (
    DenseMap, DiagonalMap, FiniteSpace, OperatorChain, OperatorDemand,
    PreparedTemporalOperator, PreparedDiagonalTemporalOperator, TypedVector,
    fulfill, verify_receipt, verify_temporal_receipt,
    verify_structured_temporal_receipt,
)


def median_ms(function, samples=9):
    function()  # warmed separately
    times = []
    for _ in range(samples):
        start = time.perf_counter_ns()
        function()
        times.append((time.perf_counter_ns()-start)/1e6)
    return round(statistics.median(times), 6)


def dense_reference(left, right, modulus):
    return tuple(tuple(sum(left[i][k]*right[k][j] for k in range(len(right)))%modulus
                       for j in range(len(right[0]))) for i in range(len(left)))


def run() -> dict:
    rng = random.Random(20261115)
    modulus, n = 97, 48
    input_space, middle, output_space = (FiniteSpace(name, n, modulus)
                                        for name in ('input-frame', 'middle-frame', 'output-frame'))
    left = DenseMap('dynamic-left-v1', middle, output_space,
                    tuple(tuple(rng.randrange(modulus) for _ in range(n)) for _ in range(n)))
    right = DenseMap('dynamic-right-v1', input_space, middle,
                     tuple(tuple(rng.randrange(modulus) for _ in range(n)) for _ in range(n)))
    chain = OperatorChain((left, right))
    vector = TypedVector(input_space, tuple(rng.randrange(modulus) for _ in range(n)))
    entry_demand = OperatorDemand('entry', row=17, column=23)
    vector_demand = OperatorDemand('vector', vector=vector)
    dense_demand = OperatorDemand('dense')
    # Independent conventional control, deliberately a dense triple loop.
    reference = dense_reference(left.rows, right.rows, modulus)
    assert chain.materialize() == reference
    assert fulfill(chain, entry_demand).result_value == reference[17][23]
    expected_vector = tuple(sum(row[k]*vector.values[k] for k in range(n))%modulus for row in reference)
    assert fulfill(chain, vector_demand).result_value == expected_vector
    receipts = {kind: fulfill(chain, req) for kind, req in
                (('entry', entry_demand), ('vector', vector_demand), ('dense', dense_demand))}
    assert all(verify_receipt(chain, req, receipts[kind]) for kind, req in
               (('entry', entry_demand), ('vector', vector_demand), ('dense', dense_demand)))
    rebinding = chain.rebind(1, DenseMap('dynamic-right-v2', input_space, middle,
                                        tuple(tuple((v + (i==0 and j==0))%modulus
                                                    for j,v in enumerate(row)) for i,row in enumerate(right.rows))))
    assert rebinding.fingerprint != chain.fingerprint
    assert not verify_receipt(rebinding, vector_demand, receipts['vector'])
    benchmark = {
        'entry_on_demand_ms': median_ms(lambda: fulfill(chain, entry_demand)),
        'vector_on_demand_ms': median_ms(lambda: fulfill(chain, vector_demand)),
        'whole_dense_via_basis_ms': median_ms(lambda: fulfill(chain, dense_demand)),
        'conventional_dense_product_ms': median_ms(lambda: dense_reference(left.rows, right.rows, modulus)),
    }
    # A separate closed-frame 3x3 example tests huge logical-time composition.
    state = FiniteSpace('state', 3, 101)
    # A dynamically supplied pure-linear phase/gain operator; second factor is
    # separate, and both are bound to one exact graph fingerprint.
    shift = DenseMap('phase-shear', state, state, ((1, 1, 0), (0, 1, 0), (0, 0, 1)))
    gain = DiagonalMap('runtime-gain', state, state, (1, 1, 1))
    temporal_chain = OperatorChain((shift, gain))
    temporal = PreparedTemporalOperator.from_chain(temporal_chain)
    origin = TypedVector(state, (39,47,1))
    tick = 10**30+11
    result = temporal.state_at(origin, tick)
    assert result.result.values == ((39 + tick*47)%101, 47, 1)
    assert verify_temporal_receipt(temporal, result)
    benchmark['temporal_dense_preparation_ms'] = median_ms(lambda: PreparedTemporalOperator.from_chain(temporal_chain))
    benchmark['temporal_huge_query_ms'] = median_ms(lambda: temporal.state_at(origin, tick))
    # A structure-discovered diagonal semigroup needs no dense temporal map.
    other_space = FiniteSpace('diag-middle', n, modulus)
    middle_space = FiniteSpace('diag-other', n, modulus)
    input_state = FiniteSpace('diag-state', n, modulus)
    diagonal_factors = (
        DiagonalMap('dynamic-d0', other_space, input_state,
                    tuple(rng.randrange(modulus) for _ in range(n))),
        DiagonalMap('dynamic-d1', middle_space, other_space,
                    tuple(rng.randrange(modulus) for _ in range(n))),
        DiagonalMap('dynamic-d2', input_state, middle_space,
                    tuple(rng.randrange(modulus) for _ in range(n))),
    )
    diagonal_chain = OperatorChain(diagonal_factors)
    structured = PreparedDiagonalTemporalOperator.from_chain(diagonal_chain)
    diagonal_seed = TypedVector(input_state, tuple(rng.randrange(modulus) for _ in range(n)))
    structured_result = structured.state_at(diagonal_seed, tick)
    assert verify_structured_temporal_receipt(structured, structured_result)
    assert structured_result.result.values == tuple(
        x * pow(d, tick, modulus) % modulus
        for x, d in zip(diagonal_seed.values, structured.diagonal)
    )
    assert not structured_result.composite_dense_materialized
    benchmark['structured_diagonal_preparation_ms'] = median_ms(
        lambda: PreparedDiagonalTemporalOperator.from_chain(diagonal_chain))
    benchmark['structured_diagonal_huge_query_ms'] = median_ms(
        lambda: structured.state_at(diagonal_seed, tick))
    benchmark['same_diagonal_chain_dense_preparation_ms'] = median_ms(
        lambda: PreparedTemporalOperator.from_chain(diagonal_chain), samples=5)
    return {
        'format': 'GEOMETRY-FIRST-005-reference-1',
        'provenance': 'isolated Python compatibility harness: real E-CPU host not exercised',
        'modulus': modulus,
        'dense_dimension': n,
        'matrix_chain_length': len(chain.factors),
        'graph_fingerprint': chain.fingerprint,
        'dynamic_rebind_fingerprint_changed': chain.fingerprint != rebinding.fingerprint,
        'stale_receipt_refused': not verify_receipt(rebinding, vector_demand, receipts['vector']),
        'outputs_match_independent_reference': True,
        'single_entry': receipts['entry'].result_value,
        'single_entry_materializes_full_product': receipts['entry'].composite_dense_materialized,
        'one_vector_materializes_full_product': receipts['vector'].composite_dense_materialized,
        'full_matrix_demand_materializes_full_product': receipts['dense'].composite_dense_materialized,
        'vector_leaf_applications': receipts['vector'].leaf_applications,
        'dense_leaf_applications': receipts['dense'].leaf_applications,
        'vector_estimated_scalar_products': receipts['vector'].estimated_scalar_products,
        'dense_estimated_scalar_products': receipts['dense'].estimated_scalar_products,
        'structured_temporal': {'kind': 'certified_diagonal', 'tick': str(tick),
                                'dimension': n, 'factors': len(diagonal_factors),
                                'result_fingerprint': structured.fingerprint,
                                'output_matches_independent_per_coordinate_modular_power': True,
                                'composite_dense_materialized': structured_result.composite_dense_materialized,
                                'intermediate_logical_states_materialized': 0},
        'temporal': {'tick': str(tick), 'initial': list(origin.values),
                     'result': list(result.result.values),
                     'certificate_fingerprint': temporal.fingerprint,
                     'exponent_bits': result.exponent_bits,
                     'intermediate_logical_states_materialized': result.intermediate_logical_states_materialized,
                     'dense_operator_prepared_before_query': True},
        'timings': benchmark,
        'timing_note': 'median single-threaded Python perf_counter_ns; reference workload only; separate preparation and query; not a hardware speedup claim',
    }


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, sort_keys=True))