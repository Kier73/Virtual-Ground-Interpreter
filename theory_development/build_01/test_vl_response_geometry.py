import math
import unittest

from vl_response_geometry import (
    Expr,
    Observer,
    canonical_json,
    default_registry,
    response_signature,
    s3_distance,
    seed_identity,
)


class ResponseGeometryTests(unittest.TestCase):
    def setUp(self):
        self.registry = default_registry()
        self.x = Expr.var()
        self.c = Expr.const
        self.call = Expr.call
        self.observer = Observer.identity()

    def test_commutative_reordering_is_canonical(self):
        left = self.call("ad", self.x, self.c(2))
        right = self.call("ad", self.c(2), self.x)
        self.assertEqual(canonical_json(left, self.registry), canonical_json(right, self.registry))
        self.assertEqual(seed_identity(left, self.registry)["sha256"], seed_identity(right, self.registry)["sha256"])

    def test_declared_identity_reductions(self):
        forms = [
            self.x,
            self.call("ad", self.x, self.c(0)),
            self.call("mx", self.x, self.c(1)),
            self.call("su", self.x, self.c(0)),
            self.call("dv", self.x, self.c(1)),
        ]
        ids = {seed_identity(form, self.registry)["sha256"] for form in forms}
        self.assertEqual(len(ids), 1)

    def test_hash_is_identity_not_metric(self):
        a = seed_identity(self.x, self.registry)
        b = seed_identity(self.call("ng", self.x), self.registry)
        self.assertNotEqual(a["sigma64"], b["sigma64"])
        # Geometry is measured from response signatures, not hash bytes.
        ra = response_signature(self.x, self.observer, self.registry)
        rb = response_signature(self.call("ng", self.x), self.observer, self.registry)
        self.assertAlmostEqual(s3_distance(ra.q_resp, rb.q_resp), math.pi, places=7)

    def test_amplitude_is_not_silently_lost(self):
        a = response_signature(self.x, self.observer, self.registry)
        b = response_signature(self.call("mx", self.c(3), self.x), self.observer, self.registry)
        self.assertAlmostEqual(s3_distance(a.q_resp, b.q_resp), 0.0, places=7)
        self.assertGreater(b.amplitude, a.amplitude)

    def test_observer_can_change_neighborhood_geometry(self):
        sinusoid = self.call("sn", self.call("mx", self.c(2 * math.pi), self.x))
        square = self.call("sq", self.x)
        mixed_plus = self.call("ad", square, self.call("mx", self.c(0.4), sinusoid))
        mixed_minus = self.call("su", square, self.call("mx", self.c(0.4), sinusoid))
        balanced = Observer.identity("balanced")
        oscillation = Observer.diagonal("oscillation", (1, 1, 1, 4))
        d_balanced = s3_distance(
            response_signature(mixed_plus, balanced, self.registry).q_resp,
            response_signature(mixed_minus, balanced, self.registry).q_resp,
        )
        d_osc = s3_distance(
            response_signature(mixed_plus, oscillation, self.registry).q_resp,
            response_signature(mixed_minus, oscillation, self.registry).q_resp,
        )
        self.assertNotAlmostEqual(d_balanced, d_osc, places=5)

    def test_s3_antipode_is_maximally_distant(self):
        a = response_signature(self.x, self.observer, self.registry).q_resp
        minus_a = tuple(-v for v in a)
        self.assertAlmostEqual(s3_distance(a, minus_a), math.pi, places=7)


    def test_orthogonal_observer_reparameterization_preserves_geometry(self):
        theta = 0.37
        c, sn = math.cos(theta), math.sin(theta)
        rotation = Observer("orthogonal", (
            (c, 0.0, 0.0, -sn),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (sn, 0.0, 0.0, c),
        ))
        forms = [self.x, self.call("sq", self.x), self.call("ng", self.x)]
        base = [response_signature(f, self.observer, self.registry) for f in forms]
        rotated = [response_signature(f, rotation, self.registry) for f in forms]
        for i in range(len(forms)):
            for j in range(i + 1, len(forms)):
                self.assertAlmostEqual(
                    s3_distance(base[i].q_resp, base[j].q_resp),
                    s3_distance(rotated[i].q_resp, rotated[j].q_resp),
                    places=7,
                )

    def test_unknown_operation_fails(self):
        with self.assertRaises(KeyError):
            response_signature(self.call("not_registered", self.x), self.observer, self.registry)

    def test_invalid_arity_fails(self):
        with self.assertRaises(ValueError):
            response_signature(self.call("ad", self.x), self.observer, self.registry)


if __name__ == "__main__":
    unittest.main(verbosity=2)
