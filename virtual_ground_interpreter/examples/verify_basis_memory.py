"""Independent-process basis-memory verifier with out-of-band identity anchors.

This script only reads bounded JSON mathematical data. It never executes a
program contained in the record and never performs basis-discovery search.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from vgi.structural_memory import (
    MAX_BYTES, admit_similarity_memory, verify_portable_similarity_receipt,
)
from vgi.typed_operator_navigation import TypedVector


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--memory',required=True)
    parser.add_argument('--graph-sha256',required=True)
    parser.add_argument('--memory-sha256',required=True)
    parser.add_argument('--tick',type=int,required=True)
    parser.add_argument('--vector',required=True,help='comma-separated integer coordinates')
    args=parser.parse_args()
    with Path(args.memory).open('rb') as stream:
        data=stream.read(MAX_BYTES+1)
    admitted=admit_similarity_memory(data,
              expected_graph_fingerprint=args.graph_sha256,
              expected_memory_sha256=args.memory_sha256)
    initial=TypedVector(admitted.graph.domain,tuple(int(v) for v in args.vector.split(',')))
    receipt=admitted.state_at(initial,args.tick)
    print(json.dumps({
       'format':'VGI-IndependentBasisMemoryVerification-1',
       'graph_sha256':admitted.graph_fingerprint,
       'memory_sha256':admitted.memory_sha256,
       'certificate_fingerprint':admitted.certificate.fingerprint,
       'block_sizes':admitted.certificate.block_sizes,
       'logical_tick':args.tick,
       'result':receipt.inner.result.values,
       'receipt_verified':verify_portable_similarity_receipt(admitted,receipt),
       'rediscovered_basis':False,
       'host_authority':'not_claimed',
    },sort_keys=True))


if __name__=='__main__':
    main()