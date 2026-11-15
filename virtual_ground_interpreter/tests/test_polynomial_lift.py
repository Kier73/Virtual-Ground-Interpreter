"""Independent finite-edge and high-time controls for GEOMETRY-FIRST-002."""
import random
import unittest

from vgi.geometry_first import FiniteGeometry
from vgi.polynomial_lift import (
    PolynomialLiftCertificate, PolynomialLiftError,
    TransitionSnapshot, discover_polynomial_lift,
)


def direct_step(snapshot, start, steps):
    state = start
    for _ in range(steps):
        state = snapshot.targets[state]
    return state


def closed_form_epsilon(modulus, x, y, ticks):
    # Sum (y+k)^2, k=0,...,n-1: exact integer division before reduction.
    square_sum = ticks * (ticks - 1) * (2 * ticks - 1) // 6
    return ((x + ticks * y * y + y * ticks * (ticks - 1) + square_sum) % modulus,
            (y + ticks) % modulus)


class PolynomialLiftDiscoveryTests(unittest.TestCase):
    def test_epsilon_discovers_nontrivial_feature_and_refuses_degree_one(self):
        snapshot = TransitionSnapshot.capture(FiniteGeometry(11), "epsilon")
        with self.assertRaises(PolynomialLiftError):
            discover_polynomial_lift(snapshot, 1)
        cert = discover_polynomial_lift(snapshot, 2)
        self.assertEqual(cert.features, ((1, 0), (0, 1), (0, 2)))
        self.assertEqual(cert.transform.matrix, ((1, 0, 1), (0, 1, 0), (0, 2, 1)))
        self.assertEqual(cert.transform.offset, (0, 1, 1))
        self.assertEqual(len(cert.fit_probes), 6)
        self.assertEqual(len(snapshot.targets), 121)
        self.assertEqual(cert.state_at(73, 0).state, 73)

    def test_randomized_repeated_ground_transitions_and_distant_time(self):
        rng = random.Random(144014)
        big = 10**40 + 71
        for prime in (5, 7, 11, 17):
            snapshot = TransitionSnapshot.capture(FiniteGeometry(prime), "epsilon")
            cert = discover_polynomial_lift(snapshot)
            for _ in range(30):
                start = rng.randrange(prime * prime)
                tick = rng.randrange(150)
                self.assertEqual(cert.state_at(start, tick).state,
                                 direct_step(snapshot, start, tick))
                x, y = divmod(start, prime)
                expected = closed_form_epsilon(prime, x, y, big)
                result = cert.state_at(start, big)
                self.assertEqual(result.coordinates, expected)
                self.assertEqual(result.exponent_bits, big.bit_length())
                self.assertEqual(result.materialized_intermediate_states, 0)
                self.assertEqual(result.lifted_coordinates[-1], expected[1]**2 % prime)

    def test_linear_delta_stays_two_dimensional(self):
        snapshot = TransitionSnapshot.capture(FiniteGeometry(7), "delta")
        cert = discover_polynomial_lift(snapshot)
        self.assertEqual(cert.features, ((1, 0), (0, 1)))
        self.assertEqual(cert.transform.matrix, ((1, 1), (0, 1)))
        self.assertEqual(cert.transform.offset, (0, 1))
        self.assertEqual(cert.state_at(8, 100).state, direct_step(snapshot, 8, 100))

    def test_tampered_single_edge_is_rejected(self):
        snapshot = TransitionSnapshot.capture(FiniteGeometry(11), "epsilon")
        targets = list(snapshot.targets)
        targets[22] = (targets[22] + 1) % len(targets)
        damaged = TransitionSnapshot(11, "epsilon", tuple(targets))
        self.assertNotEqual(damaged.fingerprint, snapshot.fingerprint)
        with self.assertRaises(PolynomialLiftError):
            discover_polynomial_lift(damaged)

    def test_nonlinear_cubic_and_unsupported_algebra_are_refused(self):
        prime = 7
        targets = tuple((((x + y**3) % prime) * prime + (y + 1) % prime)
                        for x in range(prime) for y in range(prime))
        cubic = TransitionSnapshot(prime, "cubic-control", targets)
        with self.assertRaises(PolynomialLiftError):
            discover_polynomial_lift(cubic, max_degree=2)
        # Increase the declared representation budget: the previously refused
        # cubic is now provably linear on an automatically discovered 4D lift.
        cubic_cert = discover_polynomial_lift(cubic, max_degree=3)
        self.assertEqual(cubic_cert.features,
                         ((1, 0), (0, 1), (0, 2), (0, 3)))
        self.assertEqual(cubic_cert.transform.matrix[-1], (0, 3, 3, 1))
        for point in range(prime * prime):
            for count in (0, 1, 2, 5, 20, 77):
                self.assertEqual(cubic_cert.state_at(point, count).state,
                                 direct_step(cubic, point, count))
        for invalid in (4, 8, 9, 21):
            with self.assertRaises(PolynomialLiftError):
                TransitionSnapshot(invalid, "invalid-modulus", tuple(range(invalid**2)))
        with self.assertRaises(PolynomialLiftError):
            discover_polynomial_lift(TransitionSnapshot.capture(FiniteGeometry(11), "epsilon"), 11)

    def test_snapshot_provenance_and_adversarial_certificate_rejected(self):
        geometry = FiniteGeometry(13)
        first = TransitionSnapshot.capture(geometry, "epsilon")
        second = TransitionSnapshot(13, "renamed", first.targets)
        cert = discover_polynomial_lift(first)
        self.assertNotEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(cert.snapshot.fingerprint, first.fingerprint)
        with self.assertRaises(PolynomialLiftError):
            cert.state_at(0, -1)
        with self.assertRaises(PolynomialLiftError):
            cert.state_at(169, 1)
        with self.assertRaises(PolynomialLiftError):
            PolynomialLiftCertificate(first, 2, cert.features,
                                      cert.transform, (0,) * len(cert.fit_probes))
        with self.assertRaises(PolynomialLiftError):
            PolynomialLiftCertificate(second, 2, ((1, 0), (0, 1)),
                                      cert.transform, cert.fit_probes)


if __name__ == "__main__":
    unittest.main()