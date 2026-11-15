"""GEOMETRY-FIRST-008: reusable similarity Ground across independent observers."""
from __future__ import annotations

import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
from time import perf_counter_ns

from vgi.invariant_blocks import infer_coordinate_blocks
from vgi.similarity_blocks import CertifiedSimilarityBlocks
from vgi.structural_memory import (
    admit_similarity_memory, export_similarity_memory,
    verify_portable_similarity_receipt,
)
from vgi.typed_operator_navigation import DenseMap, PreparedTemporalOperator, TypedVector
from examples.run_similarity_blocks import make_hidden_graph


def median_ms(fn, count=5):
    samples=[]
    for _ in range(count):
        start=perf_counter_ns()
        fn()
        samples.append((perf_counter_ns()-start)/1e6)
    return round(statistics.median(samples), 4)


def main() -> dict:
    graph=make_hidden_graph()
    original=CertifiedSimilarityBlocks.discover(graph)
    payload=export_similarity_memory(original)
    producer=admit_similarity_memory(payload,expected_graph_fingerprint=graph.fingerprint)
    receiver=admit_similarity_memory(payload, expected_graph_fingerprint=graph.fingerprint,
                                      expected_memory_sha256=producer.memory_sha256)
    assert producer.certificate is not receiver.certificate
    assert producer.certificate.fingerprint==receiver.certificate.fingerprint
    assert receiver.memory_sha256==producer.memory_sha256
    assert receiver.certificate.block_sizes == (4,4,4)
    initial=TypedVector(graph.domain,tuple((k*k+17*k+3)%graph.domain.modulus
                                          for k in range(graph.domain.dimension)))
    reference=PreparedTemporalOperator.from_chain(graph)
    tick=10**30+11
    answer=receiver.state_at(initial,tick)
    assert verify_portable_similarity_receipt(receiver,answer)
    assert answer.inner.result==reference.state_at(initial,tick).result

    # A new operand can reuse the established basis only after ALL proof checks.
    first=graph.factors[0]
    rows=tuple(tuple((entry+int(i==j))%graph.domain.modulus
                     for j,entry in enumerate(row)) for i,row in enumerate(first.rows))
    changed=graph.rebind(0,DenseMap('rebound-operand',first.domain,first.codomain,rows))
    updated=receiver.rebind(changed)
    assert updated.memory_sha256!=receiver.memory_sha256
    assert updated.certificate.basis==receiver.certificate.basis
    assert updated.state_at(initial,tick).inner.result==\
        PreparedTemporalOperator.from_chain(changed).state_at(initial,tick).result
    assert not verify_portable_similarity_receipt(updated,answer)

    # A real fresh Python process uses only a content-addressed record and
    # externally anchored digests, not any in-process cached search result.
    with tempfile.TemporaryDirectory(prefix='vgi-mem-') as tmp:
        path=Path(tmp)/'basis-memory.json'
        path.write_bytes(payload)
        cmd=[sys.executable,'-m','examples.verify_basis_memory',
             '--memory',str(path),'--graph-sha256',graph.fingerprint,
             '--memory-sha256',receiver.memory_sha256,
             '--tick',str(tick),'--vector',','.join(map(str,initial.values))]
        execution=subprocess.run(cmd,cwd=Path(__file__).resolve().parents[1],
                                 capture_output=True,text=True,check=True,timeout=30)
        cross_process=json.loads(execution.stdout)
        assert cross_process['receipt_verified'] is True
        assert cross_process['rediscovered_basis'] is False
        assert cross_process['result']==list(answer.inner.result.values)

    output={
        'experiment':'GEOMETRY-FIRST-008',
        'source':'independent finite-field simulation with prior VGI API-compatible modules',
        'claim':'portable independently checked mathematical structural memory, not E-CPU authority',
        'modulus':graph.domain.modulus,
        'dimension':graph.domain.dimension,
        'factors':len(graph.factors),
        'coordinate_partition_before':[list(v) for v in infer_coordinate_blocks(graph)],
        'block_sizes_after':list(receiver.certificate.block_sizes),
        'graph_fingerprint':graph.fingerprint,
        'memory_sha256':receiver.memory_sha256,
        'certificate_fingerprint':receiver.certificate.fingerprint,
        'serialized_record_bytes':len(payload),
        'logical_tick':str(tick),
        'initial':list(initial.values),
        'result':list(answer.inner.result.values),
        'different_process':cross_process,
        'same_graph_reconstruction_without_discovery':True,
        'changed_operand_reverified_same_basis':True,
        'new_digest_after_operand_change':updated.memory_sha256,
        'old_receipt_invalid_after_change':True,
        'dense_reference_matches':True,
        'timings_ms_median':{
            'original_discovery_and_certification':median_ms(lambda:CertifiedSimilarityBlocks.discover(graph),3),
            'serialization':median_ms(lambda:export_similarity_memory(original)),
            'fresh_observer_admission':median_ms(lambda:admit_similarity_memory(
                payload,expected_graph_fingerprint=graph.fingerprint,
                expected_memory_sha256=receiver.memory_sha256)),
            'valid_operand_rebind_and_reverification':median_ms(lambda:receiver.rebind(changed)),
            'query_huge_time_after_admission':median_ms(lambda:receiver.state_at(initial,tick)),
        },
        'limitations':[
           'The original mathematical Ground is assumed to be a faithful description of the intended computation.',
           'Memory carries full factor snapshot; O(L n^2) bytes not reduced by this protocol.',
           'Verifier checks all input factors; it only avoids the expensive centralizer/eigenspace candidate search.',
           'Digest anchors are external trust inputs, not signatures; attacker-controlled reference digests confer no authority.',
           'Changed operands must retain the exact commutant witness and eigenspace certificate, otherwise rebind refuses.',
           'No E-CPU host, transport, hypervisor or official CI integration is claimed.',
        ],
    }
    target=Path(__file__).resolve().parents[1]/'reports'/'geometry_first_008_reference.json'
    target.write_text(json.dumps(output,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return output


if __name__=='__main__':
    print(json.dumps(main(),indent=2,sort_keys=True))