"""Independent finite-ring controls for typed operator composition and demand navigation."""
import random
from dataclasses import replace
import unittest

from vgi.typed_operator_navigation import (
    DenseMap, DiagonalMap, FiniteSpace, OperatorChain, OperatorDemand,
    PreparedTemporalOperator, TypedOperatorError, TypedVector, fulfill,
    verify_receipt, verify_temporal_receipt,
    homogeneous_affine_map, project_homogeneous_vector,
)


def golden_product(left, right, modulus):
    """Independent triple-loop matrix multiplication, supports rectangular factors."""
    assert len(left[0]) == len(right)
    return tuple(tuple(sum(left[i][k] * right[k][j] for k in range(len(right))) % modulus
                       for j in range(len(right[0]))) for i in range(len(left)))


def golden_matvec(rows, vector, modulus):
    return tuple(sum(row[k] * vector[k] for k in range(len(vector))) % modulus for row in rows)


class TypedOperatorNavigationTests(unittest.TestCase):
    def test_dynamic_rectangular_composition_matches_independent_full_product(self):
        rng = random.Random(20261115)
        for modulus in (8, 97):
            a, b, c, d = (FiniteSpace(name, dim, modulus)
                          for name, dim in (("output", 3), ("inner1", 4),
                                            ("inner2", 2), ("input", 5)))
            raw1 = [[rng.randrange(-50, 50) for _ in range(4)] for __ in range(3)]
            raw2 = [[rng.randrange(-50, 50) for _ in range(2)] for __ in range(4)]
            raw3 = [[rng.randrange(-50, 50) for _ in range(5)] for __ in range(2)]
            operators = (DenseMap("L", b, a, raw1), DenseMap("M", c, b, raw2),
                         DenseMap("R", d, c, raw3))
            chain = OperatorChain(operators)
            expected = golden_product(golden_product(operators[0].rows, operators[1].rows, modulus),
                                      operators[2].rows, modulus)
            self.assertEqual(chain.materialize(), expected)
            self.assertEqual(chain.domain, d)
            self.assertEqual(chain.codomain, a)
            for _ in range(15):
                vector = TypedVector(d, tuple(rng.randrange(modulus) for _ in range(d.dimension)))
                self.assertEqual(chain.apply(vector).values, golden_matvec(expected, vector.values, modulus))
            for i in range(a.dimension):
                for j in range(d.dimension):
                    self.assertEqual(chain.entry(i, j), expected[i][j])
            # Change the caller-owned source lists: admitted matrix is copied/canonical.
            raw1[0][0] += 1
            self.assertEqual(chain.materialize(), expected)

    def test_sparse_diagonal_and_dense_composition_without_dense_intermediates(self):
        p, q, r = (FiniteSpace(s, 3, 17) for s in ("p", "q", "r"))
        scaling = DiagonalMap("scale", q, p, (2, 5, 11))
        mixing = DenseMap("mix", r, q, ((1, 2, 3), (4, 5, 6), (7, 8, 9)))
        chain = OperatorChain((scaling, mixing))
        vector = TypedVector(r, (3, 4, 5))
        receipt = fulfill(chain, OperatorDemand("vector", vector))
        self.assertEqual(receipt.result_value, chain.apply(vector).values)
        self.assertEqual(receipt.leaf_applications, 2)
        self.assertEqual(receipt.estimated_scalar_products, 3 + 9)
        self.assertFalse(receipt.composite_dense_materialized)
        self.assertTrue(verify_receipt(chain, OperatorDemand("vector", vector), receipt))
        entry = fulfill(chain, OperatorDemand("entry", row=1, column=2))
        self.assertEqual(entry.result_value, chain.materialize()[1][2])
        self.assertFalse(entry.composite_dense_materialized)
        dense = fulfill(chain, OperatorDemand("dense"))
        self.assertTrue(dense.composite_dense_materialized)
        self.assertEqual(dense.result_value, chain.materialize())
        self.assertEqual(dense.leaf_applications, 6)
        self.assertEqual(dense.estimated_scalar_products, 36)

    def test_dynamic_rebind_changes_identity_and_refuses_stale_receipts(self):
        a = FiniteSpace("A", 2, 101)
        b = FiniteSpace("B", 2, 101)
        c = FiniteSpace("C", 2, 101)
        left = DenseMap("L", b, a, ((1, 2), (3, 4)))
        old_right = DenseMap("R", c, b, ((5, 6), (7, 8)))
        chain = OperatorChain((left, old_right))
        demand = OperatorDemand("vector", TypedVector(c, (7, 8)))
        receipt = fulfill(chain, demand)
        changed = chain.rebind(1, DenseMap("R", c, b, ((5, 6), (7, 9))))
        self.assertNotEqual(changed.fingerprint, chain.fingerprint)
        self.assertNotEqual(fulfill(changed, demand).result_fingerprint, receipt.result_fingerprint)
        self.assertFalse(verify_receipt(changed, demand, receipt))
        self.assertFalse(verify_receipt(chain, demand, replace(receipt, result_value=(0, 0))))
        self.assertFalse(verify_receipt(chain, demand, replace(receipt, estimated_scalar_products=0)))
        self.assertTrue(verify_receipt(chain, demand, receipt))

    def test_type_mismatch_even_when_dimensions_agree(self):
        m = 97
        a, b, c = [FiniteSpace(name, 2, m) for name in ("A", "B", "C")]
        z = FiniteSpace("A", 2, 8)
        left = DenseMap("left", b, a, ((1, 0), (0, 1)))
        right = DenseMap("right", c, b, ((1, 0), (0, 1)))
        with self.assertRaises(TypedOperatorError):
            OperatorChain((right, left))
        chain = OperatorChain((left, right))
        with self.assertRaises(TypedOperatorError):
            chain.apply(TypedVector(a, (1, 2)))
        with self.assertRaises(TypedOperatorError):
            chain.rebind(1, DenseMap("other", c, c, ((1, 0), (0, 1))))
        with self.assertRaises(TypedOperatorError):
            DenseMap("bad", z, a, ((1, 0), (0, 1)))
        with self.assertRaises(TypedOperatorError):
            chain.entry(2, 0)
        with self.assertRaises(TypedOperatorError):
            chain.entry(0, 2)

    def test_invalid_inputs_and_demand_refusals(self):
        s = FiniteSpace("s", 2, 7)
        for bad in (True, 0, -3, 0.5):
            with self.assertRaises(TypedOperatorError):
                FiniteSpace("f", bad, 7)
        with self.assertRaises(TypedOperatorError):
            TypedVector(s, (True, 1))
        with self.assertRaises(TypedOperatorError):
            DenseMap("bad", s, s, ((1, 2), (3, True)))
        with self.assertRaises(TypedOperatorError):
            DenseMap("bad", s, s, ((1, 2, 3), (4, 5, 6)))
        with self.assertRaises(TypedOperatorError):
            OperatorChain(())
        for kind in ("vector", "entry", "other"):
            with self.assertRaises(TypedOperatorError):
                OperatorDemand(kind)
        with self.assertRaises(TypedOperatorError):
            OperatorDemand("dense", row=0)
        with self.assertRaises(TypedOperatorError):
            OperatorDemand("entry", row=0, column=True)

    def test_logical_time_power_matches_repeated_reference_for_random_dense_operands(self):
        rng = random.Random(4722)
        for modulus in (8, 97):
            s = FiniteSpace("dynamic", 3, modulus)
            for trial in range(12):
                matrices = tuple(DenseMap(f"operand{idx}-{trial}", s, s,
                                          tuple(tuple(rng.randrange(modulus) for _ in range(3)) for __ in range(3)))
                                 for idx in range(3))
                chain = OperatorChain(matrices)
                temporal = PreparedTemporalOperator.from_chain(chain)
                initial = TypedVector(s, tuple(rng.randrange(modulus) for _ in range(3)))
                value = initial
                for t in range(41):
                    receipt = temporal.state_at(initial, t)
                    self.assertEqual(receipt.result, value)
                    self.assertEqual(receipt.intermediate_logical_states_materialized, 0)
                    self.assertEqual(receipt.exponent_bits, t.bit_length())
                    self.assertTrue(verify_temporal_receipt(temporal, receipt))
                    value = chain.apply(value)
                other = chain.rebind(0, DenseMap("modified", s, s, ((1, 0, 0), (0, 1, 0), (0, 0, 1))))
                self.assertNotEqual(temporal.fingerprint, PreparedTemporalOperator.from_chain(other).fingerprint)

    def test_huge_logical_time_and_noninvertible_ring(self):
        s = FiniteSpace("phase", 2, 101)
        advance = DenseMap("shear", s, s, ((1, 1), (0, 1)))
        scale = DiagonalMap("gain", s, s, (1, 1))
        chain = OperatorChain((advance, scale))
        temporal = PreparedTemporalOperator.from_chain(chain)
        initial = TypedVector(s, (39, 47))
        t = 10**30 + 11
        receipt = temporal.state_at(initial, t)
        self.assertEqual(receipt.result.values, ((39 + t * 47) % 101, 47))
        self.assertEqual(receipt.exponent_bits, t.bit_length())
        self.assertEqual(receipt.intermediate_logical_states_materialized, 0)
        self.assertTrue(verify_temporal_receipt(temporal, receipt))
        with self.assertRaises(TypedOperatorError):
            PreparedTemporalOperator.from_chain(OperatorChain((DenseMap("out", s, FiniteSpace("different", 2, 101), ((1, 0), (0, 1))),)))
        r = FiniteSpace("ring8", 2, 8)
        squared = OperatorChain((DenseMap("nilpotent", r, r, ((2, 0), (0, 0))),))
        self.assertEqual(PreparedTemporalOperator.from_chain(squared).state_at(TypedVector(r, (3, 4)), 100).result.values, (0, 0))

    def test_program_extracted_law_can_be_composed_in_typed_homogeneous_space(self):
        # Integration with GEOMETRY-FIRST-004: no polynomial law supplied here.
        from vgi.program_law import certify_program
        source = "def advance(x, y):\n    return x + y*y, y + 1\n"
        program = certify_program(source, 101)
        self.assertEqual(program.features, ((1, 0), (0, 1), (0, 2)))
        operator = homogeneous_affine_map("program-derived", "program-lift-frame",
                                          program.transform)
        graph = OperatorChain((operator, operator))
        initial = TypedVector(operator.domain, (39, 47, (47*47) % 101, 1))
        end = graph.apply(initial)
        self.assertEqual(end.values[-1], 1)
        self.assertEqual(project_homogeneous_vector(end),
                         (*program.state_at(39*101+47, 2).coordinates,
                          (end.values[1]*end.values[1])%101))
        self.assertEqual(end.values[2], end.values[1] ** 2 % 101)
        temporal = PreparedTemporalOperator.from_chain(graph)
        tick = 10**30+11
        far = temporal.state_at(initial, tick)
        expected = program.state_at(39*101+47, tick*2)
        self.assertEqual(far.result.values[:2], expected.coordinates)
        self.assertEqual(far.result.values[2], expected.coordinates[1]**2 % 101)
        self.assertEqual(far.result.values[-1], 1)
        self.assertTrue(verify_temporal_receipt(temporal, far))
        # A legitimate linear operator can still violate the affine chart.
        bad = DenseMap("break-chart", operator.domain, operator.codomain,
                       ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0)))
        with self.assertRaises(TypedOperatorError):
            project_homogeneous_vector(bad.apply(initial))

    def test_prepared_mathematical_evidence_cannot_be_rebound(self):
        s = FiniteSpace("state", 2, 11)
        chain = OperatorChain((DenseMap("a", s, s, ((3, 4), (1, 6))),))
        prepared = PreparedTemporalOperator.from_chain(chain)
        with self.assertRaises(TypedOperatorError):
            PreparedTemporalOperator(chain, ((1, 0), (0, 1)))
        receipt = prepared.state_at(TypedVector(s, (3, 4)), 40000)
        self.assertFalse(verify_temporal_receipt(prepared, replace(receipt, logical_tick=40001)))
        self.assertFalse(verify_temporal_receipt(prepared, replace(receipt, result=TypedVector(s, (0, 0)))))
        with self.assertRaises(TypedOperatorError):
            prepared.state_at(TypedVector(FiniteSpace("other", 2, 11), (3, 4)), 5)


if __name__ == "__main__":
    unittest.main()