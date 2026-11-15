"""Independent replay, tamper and rebind controls for GEOMETRY-FIRST-008."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from vgi.similarity_blocks import _eye, _mat, _mul, CertifiedSimilarityBlocks
from vgi.structural_memory import (
    AdmittedSimilarityMemory, MAX_BYTES,
    admit_similarity_memory, export_similarity_memory,
    verify_portable_similarity_receipt,
)
from vgi.typed_operator_navigation import (
    DenseMap, FiniteSpace, OperatorChain, PreparedTemporalOperator,
    TypedOperatorError, TypedVector,
)
from test_similarity_blocks import hidden_graph


def canonical(record):
    return json.dumps(record,sort_keys=True,separators=(',',':')).encode()


def rehash(record):
    from vgi.typed_operator_navigation import _digest
    result = dict(record)
    result['sha256'] = _digest({k:v for k,v in result.items() if k != 'sha256'})
    return result


class StructuralMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph, _, _ = hidden_graph(seed=2077)
        cls.producer = CertifiedSimilarityBlocks.discover(cls.graph)
        cls.blob = export_similarity_memory(cls.producer)
        cls.memory = admit_similarity_memory(cls.blob,
                     expected_graph_fingerprint=cls.graph.fingerprint)

    def test_fresh_observer_reconstructs_without_discovery_search(self):
        with patch('vgi.similarity_blocks._commutant_basis',side_effect=AssertionError('search forbidden')):
            decoded = admit_similarity_memory(self.blob, expected_graph_fingerprint=self.graph.fingerprint,
                                              expected_memory_sha256=self.memory.memory_sha256)
            self.assertIsInstance(decoded,AdmittedSimilarityMemory)
            self.assertEqual(decoded.certificate.fingerprint, self.producer.fingerprint)
            self.assertEqual(decoded.graph.fingerprint,self.graph.fingerprint)
            self.assertEqual(export_similarity_memory(decoded.certificate),self.blob)

    def test_portable_navigation_matches_independent_iterative_reference(self):
        for tick in (0,1,2,5,17,49):
            state=TypedVector(self.graph.domain,(3,11,5,17,2,39,47,10))
            receipt=self.memory.state_at(state,tick)
            expected=state
            for _ in range(tick): expected=self.graph.apply(expected)
            self.assertEqual(receipt.inner.result,expected)
            self.assertTrue(verify_portable_similarity_receipt(self.memory,receipt))
            self.assertEqual(receipt.inner.dense_composites_during_query,0)
        huge=10**30+11
        original=TypedVector(self.graph.domain,(3,11,5,17,2,39,47,10))
        dense=PreparedTemporalOperator.from_chain(self.graph).state_at(original,huge)
        self.assertEqual(self.memory.state_at(original,huge).inner.result,dense.result)

    def test_portable_record_is_deterministic_immutable_self_contained(self):
        self.assertLess(len(self.blob),MAX_BYTES)
        self.assertEqual(self.blob,export_similarity_memory(self.producer))
        self.assertIn(b'centralizer_witness',self.blob)
        self.assertIn(b'opaque-0',self.blob)
        self.assertNotIn(b'python-source',self.blob)
        receiver=admit_similarity_memory(json.loads(self.blob))
        self.assertEqual(receiver.memory_sha256,self.memory.memory_sha256)

    def test_trusted_graph_and_content_anchor_are_distinct(self):
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(self.blob, expected_graph_fingerprint='0'*64)
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(self.blob,expected_memory_sha256='f'*64)
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(self.blob,expected_memory_sha256='invalid')
        self.assertEqual(self.memory.memory_sha256,json.loads(self.blob)['sha256'])

    def test_changed_operand_same_basis_rebinds_only_after_reverification(self):
        factor=self.graph.factors[0]
        rows=tuple(tuple((v+int(i==j))%101 for j,v in enumerate(row))
                   for i,row in enumerate(factor.rows))
        rebound=self.graph.rebind(0,DenseMap('opaque-updated',self.graph.domain,
                                                self.graph.domain,rows))
        with patch('vgi.similarity_blocks._commutant_basis',side_effect=AssertionError('discovery forbidden')):
            new=self.memory.rebind(rebound)
        self.assertNotEqual(new.memory_sha256,self.memory.memory_sha256)
        self.assertNotEqual(new.graph_fingerprint,self.memory.graph_fingerprint)
        initial=TypedVector(self.graph.domain,(11,)*8)
        old_receipt=self.memory.state_at(initial,37)
        self.assertFalse(verify_portable_similarity_receipt(new,old_receipt))
        actual=new.state_at(initial,37)
        self.assertEqual(actual.inner.result,
                        PreparedTemporalOperator.from_chain(rebound).state_at(initial,37).result)
        self.assertTrue(verify_portable_similarity_receipt(new,actual))
        self.assertEqual(admit_similarity_memory(export_similarity_memory(new.certificate)).memory_sha256,
                         new.memory_sha256)
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(self.blob,expected_graph_fingerprint=rebound.fingerprint)

    def test_updated_operand_crosses_old_blocks_and_refuses(self):
        f=self.graph.factors[0]
        rows=[list(row) for row in f.rows]
        rows[0][0]=(rows[0][0]+1)%101
        changed=self.graph.rebind(0,DenseMap('cross-block',f.domain,f.codomain,rows))
        with self.assertRaises(TypedOperatorError):
            self.memory.rebind(changed)
        with self.assertRaises(TypedOperatorError):
            self.memory.rebind('not-an-operator-graph')
        with self.assertRaises(TypedOperatorError):
            self.memory.rebind(OperatorChain(self.graph.factors[:2]))

    def test_unanchored_rehashed_bad_witness_still_refuses(self):
        record=json.loads(self.blob)
        record['proof']['basis'][0][0]=(record['proof']['basis'][0][0]+1)%101
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(rehash(record))
        record=json.loads(self.blob)
        record['proof']['local_composites'][0][0][0]=(record['proof']['local_composites'][0][0][0]+1)%101
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(rehash(record))

    def test_changed_graph_payload_cannot_claim_old_certificate(self):
        record=json.loads(self.blob)
        record['graph']['factors'][0]['rows'][0][0] += 1
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(rehash(record))
        record=json.loads(self.blob)
        record['graph']['factors'][0]['rows'][0][0] = (record['graph']['factors'][0]['rows'][0][0]+1)%101
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(rehash(record))

    def test_tamper_even_one_byte_refuses(self):
        record=json.loads(self.blob)
        record['proof']['eigenvalues'][0]=(record['proof']['eigenvalues'][0]+1)%101
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(canonical(record))

    def test_duplicate_unknown_noncanonical_json_refused(self):
        with self.assertRaises(TypedOperatorError):
            admit_similarity_memory(b'{"schema":1,"schema":2}')
        for modification in ('extra','noncanonical','bad-ring'):
            record=json.loads(self.blob)
            if modification=='extra':record['unexpected']='field'
            elif modification=='noncanonical': record['graph']['factors'][0]['rows'][0][0]+=101
            else:record['graph']['factors'][0]['domain']['ring']='floating-point'
            with self.assertRaises(TypedOperatorError):
                admit_similarity_memory(rehash(record))
        for bad in (b'\xff',b'null',b'[]',b'{}',b'x'*(MAX_BYTES+1),b'{"a":NaN}'):
            with self.assertRaises(TypedOperatorError):
                admit_similarity_memory(bad)

    def test_bad_eigenvalues_blocks_or_witness_refused_even_rehashed(self):
        for member in ('blocks','eigenvalues','centralizer_witness','inverse_basis'):
            record=json.loads(self.blob)
            if member=='blocks': record['proof'][member][0]=[1,2]
            elif member=='eigenvalues': record['proof'][member][0]=1.5
            else: record['proof'][member][0][0]=(record['proof'][member][0][0]+1)%101
            with self.assertRaises((TypedOperatorError,ValueError,TypeError)):
                admit_similarity_memory(rehash(record))

    def test_receipt_forgery_and_invalid_demand_refused(self):
        original=TypedVector(self.graph.domain,(1,2,3,4,5,6,7,8))
        receipt=self.memory.state_at(original,19)
        for variant in (replace(receipt,memory_sha256='a'*64),
                        replace(receipt,graph_fingerprint='b'*64),
                        replace(receipt,certificate_fingerprint='c'*64),
                        replace(receipt,inner=replace(receipt.inner,logical_tick=20)),
                        replace(receipt,inner=replace(receipt.inner,method='claimed_fast_path'))):
            self.assertFalse(verify_portable_similarity_receipt(self.memory,variant))
        for bad in (-1,True,1.2,1<<4096):
            with self.assertRaises(TypedOperatorError):
                self.memory.state_at(original,bad)
        with self.assertRaises(TypedOperatorError):
            self.memory.state_at(TypedVector(FiniteSpace('wrong',8,101),original.values),5)

    def test_independent_process_load_and_recompute(self):
        original=TypedVector(self.graph.domain,(1,2,3,4,5,6,7,8))
        target=self.memory.state_at(original,10**30+11)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'portable.json'
            path.write_bytes(self.blob)
            command=[sys.executable,'-m','examples.verify_basis_memory',
                     '--memory',str(path), '--graph-sha256',self.graph.fingerprint,
                     '--memory-sha256',self.memory.memory_sha256,
                     '--tick',str(10**30+11), '--vector',','.join(map(str,original.values))]
            process=subprocess.run(command,capture_output=True,text=True,timeout=30,cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(process.returncode,0,process.stderr)
            report=json.loads(process.stdout)
            self.assertEqual(report['result'],list(target.inner.result.values))
            self.assertTrue(report['receipt_verified'])
            self.assertFalse(report['rediscovered_basis'])


if __name__=='__main__':
    unittest.main()