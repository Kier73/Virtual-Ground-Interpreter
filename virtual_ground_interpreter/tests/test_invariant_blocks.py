"""Independent correctness and refusal controls for GEOMETRY-FIRST-006."""
import random
from dataclasses import replace
import unittest

from vgi.invariant_blocks import (
    CertifiedInvariantBlocks, infer_coordinate_blocks, verify_block_receipt,
)
from vgi.typed_operator_navigation import (
    DenseMap, DiagonalMap, FiniteSpace, OperatorChain, PreparedTemporalOperator,
    PreparedDiagonalTemporalOperator, TypedOperatorError, TypedVector,
)


def sample_graph(modulus=101):
    """Three mixed blocks with interleaved coordinates, nowhere declared as blocks."""
    size = 8
    space = FiniteSpace("hidden", size, modulus)
    blocks = ((0, 3, 7), (1, 5), (2, 4, 6))
    rng = random.Random(7026)
    leaves = []
    for k in range(3):
        rows = [[0] * size for _ in range(size)]
        for b in blocks:
            for i in b:
                for j in b:
                    rows[i][j] = rng.randrange(-30, 31)
            # An unambiguous chain within each block for connected support.
            for i, j in zip(b, b[1:]):
                rows[i][j] = 1 + k
        leaves.append(DenseMap(f"opaque-{k}", space, space, rows))
    return OperatorChain(tuple(leaves)), blocks


class InvariantBlockTests(unittest.TestCase):
    def test_discovers_hidden_interleaved_blocks_without_leaf_annotations(self):
        graph, blocks = sample_graph()
        self.assertEqual(infer_coordinate_blocks(graph), blocks)
        cert = CertifiedInvariantBlocks.discover(graph)
        self.assertEqual(cert.blocks, blocks)
        self.assertEqual(cert.block_sizes, (3, 2, 3))
        self.assertLess(cert.power_cost_proxy, graph.domain.dimension ** 3)
        self.assertEqual(cert.power_cost_proxy, 62)

    def test_differential_against_independent_repeated_graph(self):
        rng = random.Random(7033)
        for modulus in (8, 97, 101):
            graph, _ = sample_graph(modulus)
            cert = CertifiedInvariantBlocks.discover(graph)
            for _ in range(16):
                start = TypedVector(graph.domain, tuple(rng.randrange(modulus) for _ in range(8)))
                tick = rng.randrange(75)
                truth = start
                for _ in range(tick):
                    truth = graph.apply(truth)
                receipt = cert.state_at(start, tick)
                self.assertEqual(receipt.result, truth)
                self.assertEqual(receipt.full_composite_materializations_during_query, 0)
                self.assertTrue(verify_block_receipt(cert, receipt))

    def test_extreme_time_agrees_with_independent_dense_power(self):
        graph, _ = sample_graph()
        cert = CertifiedInvariantBlocks.discover(graph)
        baseline = PreparedTemporalOperator.from_chain(graph)
        start = TypedVector(graph.domain, (99, 3, 12, 56, 44, 8, 22, 10))
        t = 10**30 + 11
        self.assertEqual(cert.state_at(start, t).result, baseline.state_at(start, t).result)
        self.assertEqual(cert.state_at(start, t + 71).result,
                         _apply_after(cert.state_at(start, t).result, cert, 71))

    def test_dense_diagonal_discovery_without_prior_diagonal_type(self):
        space = FiniteSpace("dense-opaque", 12, 97)
        rows = tuple(tuple((i + 3) if i == j else 0 for j in range(12)) for i in range(12))
        graph = OperatorChain((DenseMap("not-declared-diagonal", space, space, rows),))
        with self.assertRaises(TypedOperatorError):
            PreparedDiagonalTemporalOperator.from_chain(graph)
        cert = CertifiedInvariantBlocks.discover(graph)
        self.assertEqual(cert.block_sizes, (1,) * 12)
        start = TypedVector(space, tuple(range(12)))
        tick = 10**50 + 31
        expected = tuple(pow(i + 3, tick, 97) * i % 97 for i in range(12))
        self.assertEqual(cert.state_at(start, tick).result.values, expected)

    def test_mixed_diagonal_and_dense_leaves_preserve_blocks(self):
        graph, blocks = sample_graph()
        m = graph.domain.modulus
        diagonal = DiagonalMap("scale", graph.domain, graph.domain, tuple(range(1, 9)))
        mixed = OperatorChain((diagonal,) + graph.factors)
        self.assertEqual(infer_coordinate_blocks(mixed), blocks)
        cert = CertifiedInvariantBlocks.discover(mixed)
        start = TypedVector(mixed.domain, tuple(range(8)))
        self.assertEqual(cert.state_at(start, 1).result, mixed.apply(start))

    def test_noncommuting_operators_still_navigate_correctly(self):
        s = FiniteSpace("noncommuting", 4, 17)
        a = DenseMap("a", s, s, ((1, 1, 0, 0), (0, 1, 0, 0), (0, 0, 2, 1), (0, 0, 0, 1)))
        b = DenseMap("b", s, s, ((2, 0, 0, 0), (1, 1, 0, 0), (0, 0, 1, 0), (0, 0, 1, 3)))
        chain = OperatorChain((a, b))
        self.assertNotEqual(a.apply(b.apply(TypedVector(s, (1, 2, 3, 4)))),
                            b.apply(a.apply(TypedVector(s, (1, 2, 3, 4)))))
        cert = CertifiedInvariantBlocks.discover(chain)
        start = TypedVector(s, (7, 3, 2, 1))
        repeated = start
        for t in range(34):
            self.assertEqual(cert.state_at(start, t).result, repeated)
            repeated = chain.apply(repeated)

    def test_single_offblock_coefficient_merges_connected_components(self):
        graph, original = sample_graph()
        rows = [list(row) for row in graph.factors[1].rows]
        rows[0][1] = 1
        changed = graph.rebind(1, DenseMap("opaque-1", graph.domain, graph.domain, rows))
        new = infer_coordinate_blocks(changed)
        self.assertNotEqual(new, original)
        self.assertEqual(new, ((0, 1, 3, 5, 7), (2, 4, 6)))
        oldcert = CertifiedInvariantBlocks.discover(graph)
        newcert = CertifiedInvariantBlocks.discover(changed)
        start = TypedVector(graph.domain, (1,) * 8)
        receipt = oldcert.state_at(start, 49)
        self.assertNotEqual(oldcert.fingerprint, newcert.fingerprint)
        self.assertFalse(verify_block_receipt(newcert, receipt))
        self.assertEqual(newcert.state_at(start, 5).result,
                         _repeated(changed, start, 5))

    def test_forged_partitions_and_local_products_refused(self):
        graph, blocks = sample_graph()
        cert = CertifiedInvariantBlocks.discover(graph)
        altered = list(cert.local_composites)
        first = [list(row) for row in altered[0]]
        first[0][0] = (first[0][0] + 1) % graph.domain.modulus
        altered[0] = tuple(map(tuple, first))
        with self.assertRaises(TypedOperatorError):
            CertifiedInvariantBlocks(graph, blocks, tuple(altered))
        with self.assertRaises(TypedOperatorError):
            CertifiedInvariantBlocks(graph, ((0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,)),
                                     cert.local_composites)
        with self.assertRaises(TypedOperatorError):
            CertifiedInvariantBlocks(graph, tuple(reversed(blocks)), cert.local_composites)

    def test_receipt_forgery_refused(self):
        graph, _ = sample_graph()
        cert = CertifiedInvariantBlocks.discover(graph)
        start = TypedVector(graph.domain, (2,) * 8)
        r = cert.state_at(start, 17)
        self.assertTrue(verify_block_receipt(cert, r))
        for edited in (replace(r, exponent_bits=0),
                       replace(r, full_composite_materializations_during_query=9),
                       replace(r, method="unverified"),
                       replace(r, result=start)):
            self.assertFalse(verify_block_receipt(cert, edited))

    def test_rejects_no_proper_blocks_even_if_product_cancels(self):
        s = FiniteSpace("cancel", 2, 101)
        a = DenseMap("dense", s, s, ((1, 1), (0, 1)))
        inverse = DenseMap("inverse", s, s, ((1, -1), (0, 1)))
        graph = OperatorChain((a, inverse))
        self.assertEqual(graph.materialize(), ((1, 0), (0, 1)))
        self.assertEqual(infer_coordinate_blocks(graph), ((0, 1),))
        with self.assertRaises(TypedOperatorError):
            CertifiedInvariantBlocks.discover(graph)

    def test_refuses_open_chains_and_varying_internal_dimensions(self):
        s = FiniteSpace("s", 2, 97)
        t = FiniteSpace("t", 3, 97)
        open_chain = OperatorChain((DenseMap("open", s, t, ((1, 0), (0, 1), (1, 1))),))
        with self.assertRaises(TypedOperatorError):
            infer_coordinate_blocks(open_chain)
        first = DenseMap("first", t, s, ((1, 0, 0), (0, 1, 0)))
        last = DenseMap("last", s, t, ((1, 0), (0, 1), (1, 1)))
        loop = OperatorChain((first, last))
        self.assertEqual(loop.domain, loop.codomain)
        with self.assertRaises(TypedOperatorError):
            CertifiedInvariantBlocks.discover(loop)
        with self.assertRaises(TypedOperatorError):
            infer_coordinate_blocks("not-an-operator")

    def test_ring_normalization_and_timestamp_type_guards(self):
        s = FiniteSpace("ring-8", 3, 8)
        graph = OperatorChain((DenseMap("diag", s, s,
                         ((1, 8, 0), (0, 3, 16), (24, 0, 5))),))
        cert = CertifiedInvariantBlocks.discover(graph)
        self.assertEqual(cert.block_sizes, (1, 1, 1))
        start = TypedVector(s, (4, 5, 6))
        for invalid in (-1, 2.2, True):
            with self.assertRaises(TypedOperatorError):
                cert.state_at(start, invalid)
        with self.assertRaises(TypedOperatorError):
            cert.state_at(TypedVector(FiniteSpace("wrong", 3, 8), (4, 5, 6)), 5)
        self.assertEqual(cert.state_at(start, 0).result, start)


def _repeated(graph, initial, tick):
    state = initial
    for _ in range(tick):
        state = graph.apply(state)
    return state


def _apply_after(state, certificate, ticks):
    return certificate.state_at(state, ticks).result


if __name__ == "__main__":
    unittest.main()