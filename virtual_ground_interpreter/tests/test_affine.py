import random
import unittest

from vgi import (
    GroundTransitionSystem, OrbitNavigator, OrbitPolicy, OrbitTimeCoordinate,
    TransitionObservation, TransitionOutcome,
)
from vgi.affine import (
    AffineFastForwardError, AffineOrbitCertificate, ModularAffineMap,
)


def reference_step(matrix, offset, vector, modulus):
    return tuple(
        (
            sum(matrix[row][column] * vector[column] for column in range(len(vector)))
            + offset[row]
        ) % modulus
        for row in range(len(vector))
    )


def make_transient_orbit():
    states = ("s0", "s1", "s2", "s3")
    successors = {"s0": "s1", "s1": "s2", "s2": "s3", "s3": "s3"}
    ground = GroundTransitionSystem(
        states=states, actions=("ADVANCE",), initial_state="s0",
        channels=("out",),
        observations=tuple(
            TransitionObservation(
                source, "ADVANCE", (TransitionOutcome(successors[source], (0,)),),
            )
            for source in states
        ),
    )
    policy = OrbitPolicy.from_mapping(ground, {state: "ADVANCE" for state in states})
    origin = OrbitTimeCoordinate("affine-test-clock", 17)
    orbit = OrbitNavigator.compile(
        ground, policy, start_state="s0", start_time=origin,
    )
    return orbit, origin


class ModularAffineMapTests(unittest.TestCase):
    def test_affine_power_matches_independent_repeated_reference(self):
        rng = random.Random(20261111)
        for _ in range(80):
            dimension = rng.randint(1, 3)
            modulus = rng.randint(2, 29)
            matrix = tuple(
                tuple(rng.randint(-15, 15) for _ in range(dimension))
                for _ in range(dimension)
            )
            offset = tuple(rng.randint(-20, 20) for _ in range(dimension))
            source = tuple(rng.randint(-30, 30) for _ in range(dimension))
            count = rng.randint(0, 60)
            affine = ModularAffineMap(modulus, matrix, offset)
            expected = tuple(value % modulus for value in source)
            canonical_matrix = tuple(
                tuple(value % modulus for value in row) for row in matrix
            )
            canonical_offset = tuple(value % modulus for value in offset)
            for _step in range(count):
                expected = reference_step(
                    canonical_matrix, canonical_offset, expected, modulus,
                )
            self.assertEqual(affine.power(source, count), expected)

    def test_zero_exponent_is_identity(self):
        affine = ModularAffineMap(12, ((2, 3), (4, 5)), (7, 11))
        self.assertEqual(affine.power((-1, 14), 0), (11, 2))

    def test_closed_affine_orbit_fast_forwards_transient_and_cycle(self):
        orbit, origin = make_transient_orbit()
        self.assertTrue(orbit.closed)
        self.assertEqual((orbit.cycle_start_index, orbit.cycle_period), (3, 1))
        affine = ModularAffineMap(8, ((2,),), (0,))
        certificate = AffineOrbitCertificate.certify(
            orbit, affine, {"s0": (1,), "s1": (2,), "s2": (4,), "s3": (0,)},
        )
        result = certificate.state_at(origin.advance(10**12 + 3))
        self.assertEqual(result.status, "located")
        self.assertEqual((result.state, result.vector), ("s3", (0,)))
        self.assertEqual(result.logical_transitions, 10**12 + 3)
        self.assertEqual(result.exponent_bits, (10**12 + 3).bit_length())
        self.assertEqual(result.materialized_intermediate_states, 0)
        self.assertEqual(result.method, "homogeneous_matrix_exponentiation")
        self.assertEqual(result.ground_fingerprint, orbit.system.fingerprint)
        self.assertEqual(result.policy_fingerprint, orbit.policy.fingerprint)

    def test_certificate_rejects_non_closed_orbit(self):
        ground = GroundTransitionSystem(
            states=("a", "b"), actions=("ADVANCE",), initial_state="a",
            channels=("out",),
            observations=(
                TransitionObservation("a", "ADVANCE", (TransitionOutcome("b", (0,)),)),
            ),
        )
        policy = OrbitPolicy.from_mapping(ground, {"a": "ADVANCE"})
        orbit = OrbitNavigator.compile(
            ground, policy, start_state="a",
            start_time=OrbitTimeCoordinate("open-orbit", 0),
        )
        self.assertFalse(orbit.closed)
        with self.assertRaises(AffineFastForwardError):
            AffineOrbitCertificate.certify(
                orbit, ModularAffineMap(5, ((1,),), (1,)), {"a": (0,), "b": (1,)},
            )

    def test_certificate_rejects_transition_mismatch(self):
        orbit, _ = make_transient_orbit()
        with self.assertRaises(AffineFastForwardError):
            AffineOrbitCertificate.certify(
                orbit, ModularAffineMap(8, ((1,),), (0,)),
                {"s0": (1,), "s1": (2,), "s2": (4,), "s3": (0,)},
            )

    def test_certificate_requires_complete_injective_embedding(self):
        orbit, _ = make_transient_orbit()
        affine = ModularAffineMap(8, ((2,),), (0,))
        with self.assertRaises(AffineFastForwardError):
            AffineOrbitCertificate.certify(
                orbit, affine, {"s0": (1,), "s1": (2,), "s2": (4,)},
            )
        with self.assertRaises(AffineFastForwardError):
            AffineOrbitCertificate.certify(
                orbit, affine,
                {"s0": (1,), "s1": (1,), "s2": (4,), "s3": (0,)},
            )

    def test_clock_mismatch_and_pre_origin_are_refused(self):
        orbit, origin = make_transient_orbit()
        certificate = AffineOrbitCertificate.certify(
            orbit, ModularAffineMap(8, ((2,),), (0,)),
            {"s0": (1,), "s1": (2,), "s2": (4,), "s3": (0,)},
        )
        mismatch = certificate.state_at(OrbitTimeCoordinate("other-clock", 99))
        before = certificate.state_at(OrbitTimeCoordinate(origin.clock_id, 16))
        self.assertEqual(mismatch.status, "clock_mismatch")
        self.assertIsNone(mismatch.state)
        self.assertEqual(before.status, "before_origin")
        self.assertIsNone(before.state)

    def test_certificate_fingerprint_binds_orbit_and_encoding(self):
        orbit, _ = make_transient_orbit()
        affine = ModularAffineMap(8, ((2,),), (0,))
        first = AffineOrbitCertificate.certify(
            orbit, affine, {"s0": (1,), "s1": (2,), "s2": (4,), "s3": (0,)},
        )
        scaled = AffineOrbitCertificate.certify(
            orbit, affine, {"s0": (3,), "s1": (6,), "s2": (4,), "s3": (0,)},
        )
        self.assertNotEqual(first.fingerprint, scaled.fingerprint)
        checks = first.to_dict()["verified_edges"]
        self.assertEqual(len(checks), len(orbit.steps))
        self.assertTrue(all(item["matched"] for item in checks))

    def test_composite_modulus_and_noninvertible_matrix_are_supported(self):
        affine = ModularAffineMap(8, ((2,),), (0,))
        self.assertEqual(affine.apply((1,)), (2,))
        self.assertEqual(affine.power((1,), 3), (0,))
        self.assertEqual(affine.power((1,), 10**40), (0,))

    def test_invalid_dimensions_and_boolean_values_are_rejected(self):
        with self.assertRaises(AffineFastForwardError):
            ModularAffineMap(7, ((1, 2),), (0,))
        with self.assertRaises(AffineFastForwardError):
            ModularAffineMap(True, ((1,),), (0,))
        with self.assertRaises(AffineFastForwardError):
            ModularAffineMap(7, ((True,),), (0,))
        with self.assertRaises(AffineFastForwardError):
            ModularAffineMap(7, ((1,),), (0.5,))
        with self.assertRaises(AffineFastForwardError):
            ModularAffineMap(7, ((1,),), (0,)).power((0,), True)


if __name__ == "__main__":
    unittest.main()
