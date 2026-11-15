"""Independent reference controls for the geometry-first experiment."""
import random
import unittest

from vgi.geometry_first import (
    ACTIONS, CertifiedGeometryNavigator, CodonRequirement, DeferredMatrixProduct, FiniteGeometry,
    GeometryError, bind_registry, discover_commutations, discover_laws,
    naive_product, navigate, place_dependency_graph,
)
from vgi.affine import ModularAffineMap


class GeometryFirstTests(unittest.TestCase):
    def test_opaque_seed_relabeling_does_not_change_intrinsic_geometry(self):
        geometry = FiniteGeometry(100)
        before = geometry.fingerprint
        first, second, third = (geometry.opaque_addresses(s)
                                for s in ("one", "two", "three"))
        self.assertEqual(len(first), 10000)
        self.assertTrue(all(a != b and a != c for a, b, c in zip(first, second, third)))
        self.assertEqual(geometry.fingerprint, before)
        self.assertEqual(geometry.distance(0, 99), 1)
        self.assertNotEqual(first[0], second[0])
        self.assertNotEqual(first[0], first[99])

    def test_intrinsic_discovery_finds_laws_before_registry(self):
        geom = FiniteGeometry(19)
        laws = discover_laws(geom)
        self.assertEqual(laws["alpha"].uniform_displacement, (1, 0))
        self.assertEqual(laws["beta"].uniform_displacement, (0, 1))
        self.assertEqual(laws["alpha"].orbit_period, 19)
        self.assertTrue(laws["alpha"].bijective)
        self.assertTrue(laws["gamma"].idempotent)
        self.assertFalse(laws["gamma"].bijective)
        self.assertIsNone(laws["gamma"].uniform_displacement)
        self.assertEqual(laws["delta"].affine_matrix, ((1, 1), (0, 1)))
        self.assertEqual(laws["delta"].affine_offset, (0, 1))
        self.assertIsNone(laws["epsilon"].affine_matrix)
        self.assertIsNone(laws["epsilon"].uniform_displacement)
        commutes = discover_commutations(geom)
        self.assertTrue(commutes[("alpha", "beta")])
        self.assertFalse(commutes[("alpha", "gamma")])
        self.assertTrue(commutes[("beta", "gamma")])
        registry1 = (CodonRequirement("next_row", True, displacement=(1, 0)),
                     CodonRequirement("clear_row", False, idempotent=True))
        registry2 = (CodonRequirement("advance_a", True, displacement=(1, 0)),
                     CodonRequirement("reset", False, idempotent=True))
        self.assertEqual(bind_registry(laws, registry1),
                         {"next_row": "alpha", "clear_row": "gamma"})
        self.assertEqual(bind_registry(laws, registry2),
                         {"advance_a": "alpha", "reset": "gamma"})
        with self.assertRaises(GeometryError):
            bind_registry(laws, (CodonRequirement("ambiguous", True),))

    def test_temporal_navigation_matches_repeated_reference_and_large_jump(self):
        geom = FiniteGeometry(23)
        laws = discover_laws(geom)
        rng = random.Random(9485)
        for action in ACTIONS:
            for _ in range(10):
                state = rng.choice(list(geom.points()))
                t = rng.randrange(0, 100)
                expected = state
                for __ in range(t):
                    expected = geom.step(expected, action)
                if action == "epsilon" and t > 0:
                    with self.assertRaises(GeometryError):
                        navigate(geom, laws[action], state, t)
                else:
                    self.assertEqual(navigate(geom, laws[action], state, t), expected)
        certificate = CertifiedGeometryNavigator(geom)
        self.assertEqual(certificate.state_at("delta", 123, 100),
                         navigate(geom, laws["delta"], 123, 100))
        self.assertEqual(sum(l.complete_edges_checked for l in certificate.laws),
                         len(ACTIONS) * geom.side ** 2)
        huge = 10**30 + 11
        self.assertEqual(navigate(geom, laws["alpha"], 0, huge),
                         geom.address((huge % 23, 0)))
        self.assertEqual(navigate(geom, laws["gamma"], 123, huge),
                         geom.step(123, "gamma"))
        x, y = geom.coordinates(123)
        expected_x = (x + huge * y + huge * (huge - 1) // 2) % geom.side
        expected_y = (y + huge) % geom.side
        self.assertEqual(certificate.state_at("delta", 123, huge),
                         geom.address((expected_x, expected_y)))
        with self.assertRaises(GeometryError):
            certificate.state_at("epsilon", 123, huge)
        with self.assertRaises(GeometryError):
            navigate(geom, laws["alpha"], 0, -1)

    def test_guided_positioning_improves_locality_not_semantics(self):
        geom = FiniteGeometry(100)
        deps = [()] + [(i - 1,) if i % 4 else (i - 1, i - 3)
                       for i in range(1, 48)]
        random_points, random_cost = place_dependency_graph(geom, deps, 1001, False)
        guided_points, guided_cost = place_dependency_graph(geom, deps, 1001, True)
        self.assertEqual(len(set(random_points)), 48)
        self.assertEqual(len(set(guided_points)), 48)
        self.assertLess(guided_cost, random_cost)
        self.assertGreater(random_cost / guided_cost, 5)
        with self.assertRaises(GeometryError):
            place_dependency_graph(geom, ((0,),), 1, True)

    def test_dynamic_matrix_product_is_not_a_precomputed_answer(self):
        rng = random.Random(20261114)
        for modulus in (8, 97):
            for n in (2, 4, 8):
                for _ in range(3):
                    a = [[rng.randrange(-30, 30) for j in range(n)] for i in range(n)]
                    b = [[rng.randrange(-30, 30) for j in range(n)] for i in range(n)]
                    product = DeferredMatrixProduct.from_operands(a, b, modulus)
                    expected = naive_product(product.left, product.right, modulus)
                    self.assertEqual(product.materialize(), expected)
                    vector = [rng.randrange(modulus) for _ in range(n)]
                    self.assertEqual(product.apply_vector(vector),
                                     tuple(sum(row[k] * vector[k] for k in range(n))
                                           % modulus for row in expected))
                    a[0][0] += 1
                    changed = DeferredMatrixProduct.from_operands(a, b, modulus)
                    self.assertNotEqual(changed.context_fingerprint, product.context_fingerprint)
        with self.assertRaises(GeometryError):
            DeferredMatrixProduct.from_operands(((1, 2),), ((1,),), 8)
        with self.assertRaises(GeometryError):
            DeferredMatrixProduct(((1,),), ((1,),), 8, "false-context")

    def test_existing_modular_affine_orbit_supports_contextual_matrix_power(self):
        # This is not a new speedup: it uses VGI's previously certified algebraic primitive.
        transform = ModularAffineMap(97, ((2, 3), (1, 1)), (5, 7))
        start = (42, 17)
        state = start
        for tick in range(120):
            self.assertEqual(transform.power(start, tick), state)
            state = transform.apply(state)
        big = 10**18 + 29
        self.assertEqual(transform.power(start, big + 17),
                         transform.power(transform.power(start, big), 17))


if __name__ == "__main__":
    unittest.main()