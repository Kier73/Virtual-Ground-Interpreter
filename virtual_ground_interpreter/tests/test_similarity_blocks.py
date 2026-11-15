"""Independent differential and adversarial controls for GEOMETRY-FIRST-007."""
from dataclasses import replace
import random
import unittest

from vgi.similarity_blocks import (
    CertifiedSimilarityBlocks, _inverse, _mul, _eye, _mat,
    _commutant_basis, discover_similarity_blocks, verify_similarity_receipt,
)
from vgi.invariant_blocks import CertifiedInvariantBlocks, infer_coordinate_blocks
from vgi.typed_operator_navigation import (
    DenseMap, FiniteSpace, OperatorChain, PreparedTemporalOperator,
    TypedOperatorError, TypedVector,
)


def hidden_graph(seed: int = 2077, nblocks: tuple[int,...] = (3,2,3), p: int = 101,
                 count: int = 3):
    """Conjugate previously unannotated, noncommuting independent factors."""
    rng = random.Random(seed)
    n=sum(nblocks)
    frame=FiniteSpace("hidden-similarity",n,p)
    # Repeated elementary similarity shears have an exact invertible result.
    basis=[list(row) for row in _eye(n)]
    for k in range(6*n):
        a,b=rng.sample(range(n),2)
        scale=rng.randrange(1,p)
        basis[a]=[(v+scale*w)%p for v,w in zip(basis[a],basis[b])]
    basis=tuple(tuple(row) for row in basis)
    inverse=_inverse(basis,p)
    factors=[]
    for t in range(count):
        block=[[0]*n for _ in range(n)]
        cursor=0
        for size in nblocks:
            indices=range(cursor,cursor+size)
            for i in indices:
                for j in indices:
                    block[i][j]=rng.randrange(p)
            cursor+=size
        matrix=_mul(_mul(basis,tuple(map(tuple,block)),p),inverse,p)
        factors.append(DenseMap(f"opaque-{t}",frame,frame,matrix))
    return OperatorChain(tuple(factors)),basis,inverse


def repeated(graph, initial, ticks):
    result=initial
    for _ in range(ticks):
        result=graph.apply(result)
    return result


class SimilarityBlocksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph,cls.hidden_basis,cls.hidden_inverse=hidden_graph()
        cls.cert=CertifiedSimilarityBlocks.discover(cls.graph)

    def test_discovers_hidden_blocks_in_opaque_dense_matrices(self):
        self.assertEqual(infer_coordinate_blocks(self.graph),(tuple(range(8)),))
        with self.assertRaises(TypedOperatorError):
            CertifiedInvariantBlocks.discover(self.graph)
        self.assertEqual(sorted(self.cert.block_sizes),[2,3,3])
        self.assertNotEqual(self.cert.basis,_eye(8))
        self.assertEqual(_mul(self.cert.inverse_basis,self.cert.basis,101),_eye(8))
        self.assertEqual(sum(d**3 for d in self.cert.block_sizes),62)
        self.assertEqual(len(_commutant_basis(self.graph)),3)

    def test_factors_need_not_commute_with_each_other(self):
        a,b=(_mat(leaf) for leaf in self.graph.factors[:2])
        self.assertNotEqual(_mul(a,b,101),_mul(b,a,101))
        self.assertTrue(all(_mul(self.cert.centralizer_witness,_mat(f),101)==
                            _mul(_mat(f),self.cert.centralizer_witness,101)
                            for f in self.graph.factors))

    def test_differential_repeated_execution_random_starts(self):
        rng=random.Random(2735)
        for _ in range(10):
            initial=TypedVector(self.graph.domain,tuple(rng.randrange(101) for _ in range(8)))
            steps=rng.randrange(70)
            result=self.cert.state_at(initial,steps)
            self.assertEqual(result.result,repeated(self.graph,initial,steps))
            self.assertTrue(verify_similarity_receipt(self.cert,result))
            self.assertEqual(result.dense_composites_during_query,0)

    def test_huge_timestamp_independent_dense_reference(self):
        initial=TypedVector(self.graph.domain,(37,44,7,2,5,99,14,56))
        dense=PreparedTemporalOperator.from_chain(self.graph)
        t=10**30+11
        self.assertEqual(self.cert.state_at(initial,t).result,dense.state_at(initial,t).result)
        evolved=self.cert.state_at(initial,t).result
        self.assertEqual(self.cert.state_at(initial,t+63).result,
                         self.cert.state_at(evolved,63).result)

    def test_invalid_basis_or_inverse_refused(self):
        cert=self.cert
        fake=[list(r) for r in cert.basis]
        fake[0][0]=(fake[0][0]+1)%101
        with self.assertRaises(TypedOperatorError):
            replace(cert,basis=tuple(map(tuple,fake)))
        with self.assertRaises(TypedOperatorError):
            replace(cert,inverse_basis=cert.basis)
        with self.assertRaises(TypedOperatorError):
            replace(cert,eigenvalues=tuple((i+1)%101 for i in cert.eigenvalues))
        with self.assertRaises(TypedOperatorError):
            replace(cert,blocks=((0,),(1,2,3,4,5,6,7)))

    def test_forged_witness_or_local_composite_refused(self):
        cert=self.cert
        fake=[list(r) for r in cert.centralizer_witness]
        fake[0][0]=(fake[0][0]+1)%101
        with self.assertRaises(TypedOperatorError):
            replace(cert,centralizer_witness=tuple(map(tuple,fake)))
        matrices=list(cert.local_composites)
        changed=[list(r) for r in matrices[0]]
        changed[0][0]=(changed[0][0]+1)%101
        matrices[0]=tuple(map(tuple,changed))
        with self.assertRaises(TypedOperatorError):
            replace(cert,local_composites=tuple(matrices))

    def test_rebind_invalidates_receipt_and_can_collapse_split(self):
        old=self.cert
        initial=TypedVector(self.graph.domain,(1,2,3,4,5,6,7,8))
        receipt=old.state_at(initial,19)
        new_factors=list(self.graph.factors)
        rows=[list(row) for row in new_factors[0].rows]
        rows[0][0]=(rows[0][0]+1)%101
        changed=self.graph.rebind(0,DenseMap("updated",self.graph.domain,
                                             self.graph.codomain,tuple(map(tuple,rows))))
        self.assertNotEqual(changed.fingerprint,self.graph.fingerprint)
        self.assertFalse(verify_similarity_receipt(old,replace(receipt,certificate_fingerprint="changed")))
        self.assertFalse(verify_similarity_receipt(old,replace(receipt,result=initial)))
        try:
            updated=CertifiedSimilarityBlocks.discover(changed)
        except TypedOperatorError:
            pass  # a generic cross-block update destroys the common split
        else:
            self.assertNotEqual(updated.fingerprint,old.fingerprint)
            self.assertFalse(verify_similarity_receipt(updated,receipt))

    def test_scalar_commutant_refuses_common_split(self):
        s=FiniteSpace("full-matrix-algebra",2,101)
        a=DenseMap("upper",s,s,((1,1),(0,1)))
        b=DenseMap("lower",s,s,((1,0),(1,1)))
        graph=OperatorChain((a,b))
        self.assertEqual(len(_commutant_basis(graph)),1)
        with self.assertRaises(TypedOperatorError):
            CertifiedSimilarityBlocks.discover(graph)

    def test_composite_ring_refused(self):
        s=FiniteSpace("composite",2,8)
        graph=OperatorChain((DenseMap("factor",s,s,((1,2),(3,4))),))
        with self.assertRaises(TypedOperatorError):
            CertifiedSimilarityBlocks.discover(graph)

    def test_nonsplit_commutant_does_not_issue_certificate(self):
        # On F_3, x^2+1 has no roots; the rotation's non-scalar
        # centralizer has no fully splitting witness.
        s=FiniteSpace("nonsplit",2,3)
        graph=OperatorChain((DenseMap("rotation",s,s,((0,-1),(1,0))),))
        with self.assertRaises(TypedOperatorError):
            CertifiedSimilarityBlocks.discover(graph)

    def test_candidate_budget_is_bounded(self):
        with self.assertRaises(TypedOperatorError):
            CertifiedSimilarityBlocks.discover(self.graph,max_candidates=0)
        with self.assertRaises(TypedOperatorError):
            CertifiedSimilarityBlocks.discover(self.graph,max_candidates=257)

    def test_typed_frames_and_negative_ticks_refused(self):
        initial=TypedVector(self.graph.domain,tuple(range(8)))
        for tick in (-1,1.5,True):
            with self.assertRaises(TypedOperatorError):
                self.cert.state_at(initial,tick)
        wrong=TypedVector(FiniteSpace("other-frame",8,101),initial.values)
        with self.assertRaises(TypedOperatorError):
            self.cert.state_at(wrong,5)
        self.assertEqual(self.cert.state_at(initial,0).result,initial)

    def test_receipt_metadata_mutations_rejected(self):
        x=TypedVector(self.graph.domain,(7,)*8)
        receipt=self.cert.state_at(x,61)
        for variant in (replace(receipt,local_powers=0),
                        replace(receipt,method="unsupported"),
                        replace(receipt,exponent_bits=0),
                        replace(receipt,dense_composites_during_query=3)):
            self.assertFalse(verify_similarity_receipt(self.cert,variant))


if __name__ == "__main__":
    unittest.main()