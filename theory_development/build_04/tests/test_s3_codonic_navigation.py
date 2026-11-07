import math
import unittest

from s3_codonic_navigation import (
    ALG, IDENTITY, Registry, QuaternionAlgebra, compile_quaternion_multiply,
    cap_loop, fibre_phase, hopf_project, horizontal_lift, qnormalize,
    reverse_closed_path, s3_distance, so3_distance, slerp_s3, slerp_so3,
    solid_angle_cap, solid_angle_wavy_cap, vector_error, wavy_cap_loop,
)


class QuaternionAlgebraTests(unittest.TestCase):
    def test_codonic_hamilton_product_matches_known_i_squared(self):
        i = (0.0, 1.0, 0.0, 0.0)
        self.assertAlmostEqual(ALG.qmul(i, i)[0], -1.0, places=14)
        self.assertLess(max(abs(x) for x in ALG.qmul(i, i)[1:]), 1e-14)

    def test_program_uses_only_registered_scalar_primitives(self):
        p = compile_quaternion_multiply()
        valid = {"ad", "su", "mx"}
        self.assertTrue(all(ins.codon in valid for ins in p.instructions))

    def test_registry_alias_changes_names_not_algebra(self):
        aliases = Registry(add="plus", sub="minus", mul="times", div="over", sqrt="root")
        alg2 = QuaternionAlgebra(aliases)
        a = (0.8, 0.1, -0.2, 0.55)
        b = (0.7, -0.3, 0.4, 0.2)
        self.assertLess(max(abs(x-y) for x,y in zip(ALG.qmul(a,b), alg2.qmul(a,b))), 1e-14)

    def test_registry_rejects_ambiguous_aliases(self):
        with self.assertRaises(ValueError):
            Registry(add="op", sub="op")

    def test_quaternion_normalization(self):
        q = ALG.normalize((1.0, 2.0, -3.0, 4.0))
        self.assertAlmostEqual(ALG.norm_sq(q), 1.0, places=14)

    def test_noncommutative_quaternion_product(self):
        i = (0.0, 1.0, 0.0, 0.0)
        j = (0.0, 0.0, 1.0, 0.0)
        self.assertEqual(ALG.qmul(i, j), (0.0, 0.0, 0.0, 1.0))
        self.assertEqual(ALG.qmul(j, i), (0.0, 0.0, 0.0, -1.0))


class S3AndSO3MetricTests(unittest.TestCase):
    def test_s3_antipodes_are_pi_apart(self):
        minus = tuple(-x for x in IDENTITY)
        self.assertAlmostEqual(s3_distance(IDENTITY, minus), math.pi, places=14)

    def test_so3_identifies_antipodes(self):
        minus = tuple(-x for x in IDENTITY)
        self.assertAlmostEqual(so3_distance(IDENTITY, minus), 0.0, places=14)

    def test_s3_slerp_has_unit_norm_and_constant_fractional_distance(self):
        q1 = qnormalize((0.3, 0.4, -0.2, 0.7))
        total = s3_distance(IDENTITY, q1)
        for t in (0.1, 0.25, 0.5, 0.9):
            qt = slerp_s3(IDENTITY, q1, t)
            self.assertAlmostEqual(ALG.norm_sq(qt), 1.0, places=12)
            self.assertAlmostEqual(s3_distance(IDENTITY, qt), t * total, places=11)

    def test_s3_slerp_rejects_ambiguous_antipodal_geodesic(self):
        minus = tuple(-x for x in IDENTITY)
        with self.assertRaises(ValueError):
            slerp_s3(IDENTITY, minus, 0.5)

    def test_so3_slerp_avoids_antipodal_long_path(self):
        minus = tuple(-x for x in IDENTITY)
        mid = slerp_so3(IDENTITY, minus, 0.5)
        self.assertAlmostEqual(so3_distance(IDENTITY, mid), 0.0, places=12)


class HopfTransportTests(unittest.TestCase):
    def test_hopf_projection_is_invariant_under_fibre_action(self):
        beta = 0.73
        fibre = (math.cos(beta), 0.0, 0.0, math.sin(beta))
        q = qnormalize((0.7, 0.2, -0.3, 0.6))
        shifted = ALG.qmul(q, fibre)
        self.assertLess(vector_error(hopf_project(q), hopf_project(shifted)), 1e-12)

    def test_cap_loop_closes_in_base_but_not_in_total_space(self):
        theta = 0.62
        lift = horizontal_lift(cap_loop(theta))
        self.assertLess(vector_error(hopf_project(lift[0]), hopf_project(lift[-1])), 1e-10)
        self.assertGreater(s3_distance(lift[0], lift[-1]), 0.01)

    def test_holonomy_matches_half_solid_angle(self):
        theta = 0.62
        lift = horizontal_lift(cap_loop(theta, 160, 960))
        phase, residual = fibre_phase(IDENTITY, lift[-1])
        expected = 0.5 * solid_angle_cap(theta)
        self.assertLess(abs(phase - expected), 2e-5)
        self.assertLess(residual, 1e-10)

    def test_refinement_converges(self):
        theta = 0.85
        exact = 0.5 * solid_angle_cap(theta)
        coarse = horizontal_lift(cap_loop(theta, 20, 80))[-1]
        fine = horizontal_lift(cap_loop(theta, 120, 720))[-1]
        coarse_phase, _ = fibre_phase(IDENTITY, coarse)
        fine_phase, _ = fibre_phase(IDENTITY, fine)
        self.assertLess(abs(fine_phase - exact), abs(coarse_phase - exact))

    def test_reversed_loop_negates_holonomy(self):
        path = cap_loop(0.62)
        forward = horizontal_lift(path)[-1]
        backward = horizontal_lift(reverse_closed_path(path))[-1]
        pf, _ = fibre_phase(IDENTITY, forward)
        pb, _ = fibre_phase(IDENTITY, backward)
        self.assertLess(abs(pf + pb), 2e-5)

    def test_distinct_loops_same_base_endpoint_different_holonomy(self):
        lift_a = horizontal_lift(cap_loop(0.62))
        lift_b = horizontal_lift(cap_loop(0.98))
        self.assertLess(vector_error(hopf_project(lift_a[-1]), hopf_project(lift_b[-1])), 1e-10)
        phase_a, _ = fibre_phase(IDENTITY, lift_a[-1])
        phase_b, _ = fibre_phase(IDENTITY, lift_b[-1])
        self.assertGreater(abs(phase_a - phase_b), 0.2)
        self.assertGreater(s3_distance(lift_a[-1], lift_b[-1]), 0.2)

    def test_initial_fibre_gauge_representative_does_not_change_holonomy(self):
        beta = 0.47
        q0 = (math.cos(beta), 0.0, 0.0, math.sin(beta))
        path = cap_loop(0.62)
        lift = horizontal_lift(path, q0)
        phase, residual = fibre_phase(q0, lift[-1])
        expected = 0.5 * solid_angle_cap(0.62)
        self.assertLess(abs(phase - expected), 2e-5)
        self.assertLess(residual, 1e-10)

    def test_non_circular_loop_holonomy_matches_area_integral(self):
        params = {"theta0": 0.72, "amplitude": 0.13, "mode": 3}
        lift = horizontal_lift(wavy_cap_loop(**params))
        phase, residual = fibre_phase(IDENTITY, lift[-1])
        expected = 0.5 * solid_angle_wavy_cap(**params)
        self.assertLess(abs(phase - expected), 3e-5)
        self.assertLess(residual, 1e-10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
