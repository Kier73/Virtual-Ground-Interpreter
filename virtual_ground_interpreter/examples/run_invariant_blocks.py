"""Deterministic reference experiment for GEOMETRY-FIRST-006.

Run from virtual_ground_interpreter/: python -m examples.run_invariant_blocks
"""
from __future__ import annotations

import json
import random
import statistics
import time
from pathlib import Path

from vgi.invariant_blocks import CertifiedInvariantBlocks, infer_coordinate_blocks, verify_block_receipt
from vgi.typed_operator_navigation import (
    DenseMap, FiniteSpace, OperatorChain, PreparedTemporalOperator, TypedVector,
)


def build_graph(size=48, block_size=6, factors=4, modulus=97, seed=606):
    """Opaque dense matrices with shuffled, previously unknown block positions."""
    rng = random.Random(seed)
    if size % block_size:
        raise ValueError("block size must divide the dimension")
    space = FiniteSpace("dynamically-supplied", size, modulus)
    permutation = list(range(size))
    rng.shuffle(permutation)
    blocks = tuple(tuple(sorted(permutation[i:i + block_size]))
                   for i in range(0, size, block_size))
    result = []
    for k in range(factors):
        rows = [[0] * size for _ in range(size)]
        for block in blocks:
            for i in block:
                for j in block:
                    rows[i][j] = rng.randrange(modulus)
            for i, j in zip(block, block[1:]):
                rows[i][j] = 1 + k
        result.append(DenseMap(f"dynamic-{k}", space, space, rows))
    return OperatorChain(tuple(result)), blocks


def elapsed_ms(fn, repetitions=7):
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - start) / 1e6)
    return round(statistics.median(samples), 4)


def main():
    chain, expected = build_graph()
    observed = infer_coordinate_blocks(chain)
    certified = CertifiedInvariantBlocks.discover(chain)
    assert observed == tuple(sorted(expected, key=lambda block: block[0]))
    rng = random.Random(77)
    initial = TypedVector(chain.domain, tuple(rng.randrange(chain.domain.modulus)
                                              for _ in range(chain.domain.dimension)))
    tick = 2048
    baseline = PreparedTemporalOperator.from_chain(chain)
    observed_result = certified.state_at(initial, tick)
    assert observed_result.result == baseline.state_at(initial, tick).result
    assert verify_block_receipt(certified, observed_result)
    huge = 10**30 + 11
    far = certified.state_at(initial, huge)
    assert certified.state_at(far.result, 13).result == certified.state_at(initial, huge + 13).result

    new_rows = [list(row) for row in chain.factors[0].rows]
    one, two = observed[0], observed[1]
    new_rows[one[0]][two[0]] = 1
    revised = chain.rebind(0, DenseMap("dynamic-0", chain.domain, chain.codomain, new_rows))
    revised_cert = CertifiedInvariantBlocks.discover(revised)
    assert len(revised_cert.blocks) == len(certified.blocks) - 1
    assert not verify_block_receipt(revised_cert, far)

    timings = {
        "discover_and_certify_ms_median": elapsed_ms(lambda: CertifiedInvariantBlocks.discover(chain)),
        "dense_prepare_ms_median": elapsed_ms(lambda: PreparedTemporalOperator.from_chain(chain), 3),
        "block_query_2048_ms_median": elapsed_ms(lambda: certified.state_at(initial, tick)),
        "dense_query_2048_ms_median": elapsed_ms(lambda: baseline.state_at(initial, tick), 3),
        "block_query_huge_ms_median": elapsed_ms(lambda: certified.state_at(initial, huge)),
    }
    report = {
        "experiment": "GEOMETRY-FIRST-006",
        "method": "exact_common_coordinate_block_discovery",
        "environment": "isolated local Python with API-compatible VGI affine test harness",
        "modulus": chain.domain.modulus,
        "dimension": chain.domain.dimension,
        "leaf_count": len(chain.factors),
        "opaque_dense_input_coefficients_inspected_per_discovery":
            len(chain.factors) * chain.domain.dimension**2,
        "observed_block_sizes": certified.block_sizes,
        "blocks": certified.blocks,
        "block_count": len(certified.blocks),
        "ambient_cubic_cost_proxy": chain.domain.dimension**3,
        "block_cubic_cost_proxy": certified.power_cost_proxy,
        "cubic_proxy_ratio": round(chain.domain.dimension**3 / certified.power_cost_proxy, 2),
        "dense_composite_created_in_block_preparation": False,
        "correctness": {
            "same_tick_dense_reference": tick,
            "same_tick_result": observed_result.result.values,
            "huge_tick": str(huge),
            "huge_tick_result": far.result.values,
            "huge_tick_semigroup_consistency": True,
            "one_cross_block_operand_update_merges_two_blocks": True,
            "stale_receipt_rejected": True,
        },
        "timings": timings,
        "limitations": [
            "only coordinate-aligned common reducing blocks of individual factors",
            "does not find arbitrary similarity-transformed invariant subspaces",
            "dense input operands still cost O(L*n^2) to inspect",
            "dense preparation cost separate from query cost",
            "fingerprints are reproducibility identities, not trusted external attestation",
            "timings from a local API-compatible harness, not full-repository CI or E-CPU",
        ],
    }
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()