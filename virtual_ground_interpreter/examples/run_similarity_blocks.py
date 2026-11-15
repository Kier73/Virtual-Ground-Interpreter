"""GEOMETRY-FIRST-007 reproducible experiment: unknown similarity basis."""
from __future__ import annotations

import json
import random
import statistics
from pathlib import Path
from time import perf_counter_ns

from vgi.invariant_blocks import infer_coordinate_blocks
from vgi.similarity_blocks import CertifiedSimilarityBlocks, _eye, _inverse, _mul, verify_similarity_receipt
from vgi.typed_operator_navigation import (
    DenseMap, FiniteSpace, OperatorChain, PreparedTemporalOperator, TypedVector,
)


def make_hidden_graph(seed: int = 2077, sizes: tuple[int, ...] = (4,4,4),
                      modulus: int = 101, factors: int = 3) -> OperatorChain:
    rng = random.Random(seed)
    n=sum(sizes)
    frame=FiniteSpace("opaque-computational-ground",n,modulus)
    p=[list(row) for row in _eye(n)]
    for _ in range(6*n):
        i,j=rng.sample(range(n),2)
        a=rng.randrange(1,modulus)
        p[i]=[(x+a*y)%modulus for x,y in zip(p[i],p[j])]
    p=tuple(map(tuple,p))
    inv=_inverse(p,modulus)
    leaves=[]
    for leaf_num in range(factors):
        hidden=[[0]*n for _ in range(n)]
        start=0
        for size in sizes:
            for i in range(start,start+size):
                for j in range(start,start+size):
                    hidden[i][j]=rng.randrange(modulus)
            start+=size
        visible=_mul(_mul(p,tuple(map(tuple,hidden)),modulus),inv,modulus)
        leaves.append(DenseMap("opaque-factor-"+str(leaf_num),frame,frame,visible))
    return OperatorChain(tuple(leaves))


def median_ms(work, repeats: int = 5) -> float:
    samples=[]
    for _ in range(repeats):
        start=perf_counter_ns()
        work()
        samples.append((perf_counter_ns()-start)/1e6)
    return round(statistics.median(samples),4)


def main() -> dict:
    graph=make_hidden_graph()
    n=graph.domain.dimension
    certificate=CertifiedSimilarityBlocks.discover(graph)
    initial=TypedVector(graph.domain,tuple((k*k+17*k+3)%graph.domain.modulus for k in range(n)))
    tick=4096
    dense=PreparedTemporalOperator.from_chain(graph)
    actual=certificate.state_at(initial,tick)
    expected=dense.state_at(initial,tick)
    assert actual.result==expected.result
    assert verify_similarity_receipt(certificate,actual)
    huge=10**30+11
    large=certificate.state_at(initial,huge)
    assert large.result==dense.state_at(initial,huge).result
    assert certificate.state_at(initial,huge+123).result==certificate.state_at(large.result,123).result
    direct=initial
    for t in range(65):
        if t in (0,1,4,13,64):
            assert certificate.state_at(initial,t).result==direct
        direct=graph.apply(direct)
    output={
       "experiment":"GEOMETRY-FIRST-007",
       "method":"exact_finite_field_common_commutant_eigenspace_similarity",
       "environment":"isolated Python with API-compatible VGI affine harness",
       "modulus":graph.domain.modulus,
       "dimension":n,
       "leaf_count":len(graph.factors),
       "ordinary_coordinate_support_partition":list(map(list,infer_coordinate_blocks(graph))),
       "recovered_similarity_block_sizes":list(certificate.block_sizes),
       "commutant_witness": [list(row) for row in certificate.centralizer_witness],
       "certificate_fingerprint":certificate.fingerprint,
       "input_graph_fingerprint":graph.fingerprint,
       "cubic_cost_proxy":{
           "ambient_n_cubed":n**3,
           "block_sum_cubed":certificate.cost_proxy,
           "reduction_ratio":round(n**3/certificate.cost_proxy,3)
       },
       "correctness":{
           "same_tick":tick,
           "same_tick_result":list(actual.result.values),
           "huge_tick":str(huge),
           "huge_tick_result":list(large.result.values),
           "same_as_dense_reference":True,
           "checked_ordinary_iterative_times":[0,1,4,13,64],
           "huge_tick_semigroup_consistency":True,
           "no_full_ambient_composite_during_similarity_query":True,
       },
       "timings":{
           "discover_and_certify_ms_median":median_ms(lambda:CertifiedSimilarityBlocks.discover(graph),3),
           "dense_prepare_ms_median":median_ms(lambda:PreparedTemporalOperator.from_chain(graph),5),
           "similarity_query_4096_ms_median":median_ms(lambda:certificate.state_at(initial,tick),5),
           "dense_query_4096_ms_median":median_ms(lambda:dense.state_at(initial,tick),5),
           "similarity_query_huge_ms_median":median_ms(lambda:certificate.state_at(initial,huge),5),
       },
       "limitations":[
          "discoverable only when bounded commutant search finds a fully split witness over the base prime field",
          "complete commutant by exact nullspace elimination may cost O(L*n^6) arithmetic",
          "does not certify all abstract invariant subspaces or extension-field decompositions",
          "discovery and certificate admission cost excluded from subsequent query latency",
          "full input operands still have O(L*n^2) coefficient storage",
          "SHA-256 fingerprints are context identities, not evidence of host authority",
          "local Python API-compatible test harness, not actual GitHub CI or E-CPU substrate",
       ]
    }
    target=Path(__file__).resolve().parents[1]/"reports"/"geometry_first_007_reference.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(output,indent=2)+"\n")
    return output


if __name__=="__main__":
    print(json.dumps(main(),indent=2))