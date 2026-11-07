import math
import unittest

from codonic_connection import (
    Registry, compile_rotation, transport_matrix, matvec, determinant,
    rotation_error, observer_closed, RADIAL_OBSERVER, FULL_OBSERVER,
    oriented_phase, reverse_path, identity, matmul, max_abs_matrix_delta,
    conjugate, trace, path_samples, finite_difference_rms,
)


class CodonicConnectionTests(unittest.TestCase):
    def test_rotation_matches_analytic_matrix(self):
        angles = [-2.2, -1.1, -0.3, 0.1, 0.8, 1.7, 2.8]
        angles.extend(-2.95 + i * (5.90 / 80.0) for i in range(81))
        for theta in angles:
            with self.subTest(theta=theta):
                self.assertLess(rotation_error(transport_matrix(compile_rotation(theta)), theta), 1e-11)

    def test_each_shear_is_area_preserving(self):
        for theta in (-1.7, -0.4, 0.9, 2.1):
            for edge in compile_rotation(theta):
                self.assertAlmostEqual(determinant(edge.matrix()), 1.0, places=12)

    def test_transport_matrix_is_derived_from_executable_codons(self):
        for theta in (-1.3, 0.2, 1.6):
            for edge in compile_rotation(theta):
                k = edge.coefficient
                expected = ((1.0, k), (0.0, 1.0)) if edge.axis == "x" else ((1.0, 0.0), (k, 1.0))
                self.assertLess(max_abs_matrix_delta(edge.matrix(), expected), 1e-12)

    def test_total_transport_preserves_area(self):
        for theta in (-2.1, -0.5, 0.8, 2.4):
            self.assertAlmostEqual(determinant(transport_matrix(compile_rotation(theta))), 1.0, places=12)

    def test_radial_observer_closes(self):
        for start in ((1.0, 0.0), (0.3, -1.7), (-2.0, 4.5)):
            path = compile_rotation(0.8)
            end = matvec(transport_matrix(path), start)
            self.assertTrue(observer_closed(RADIAL_OBSERVER, start, end))

    def test_full_observer_detects_hidden_fibre_change(self):
        path = compile_rotation(0.8)
        start = (1.0, 0.0)
        end = matvec(transport_matrix(path), start)
        self.assertFalse(observer_closed(FULL_OBSERVER, start, end))

    def test_holonomy_phase_matches_parameter(self):
        for theta in (-2.0, -0.7, 0.25, 0.8, 2.3):
            end = matvec(transport_matrix(compile_rotation(theta)), (1.0, 0.0))
            self.assertAlmostEqual(oriented_phase((1.0, 0.0), end), theta, places=12)

    def test_reverse_path_is_inverse(self):
        path = compile_rotation(0.8)
        reverse = reverse_path(path)
        product = matmul(transport_matrix(reverse), transport_matrix(path))
        self.assertLess(max_abs_matrix_delta(product, identity()), 1e-12)

    def test_reverse_path_reverses_signed_phase(self):
        path = compile_rotation(1.2)
        h = transport_matrix(path)
        r = transport_matrix(reverse_path(path))
        forward_phase = oriented_phase((1.0, 0.0), matvec(h, (1.0, 0.0)))
        reverse_phase = oriented_phase((1.0, 0.0), matvec(r, (1.0, 0.0)))
        self.assertAlmostEqual(forward_phase, -reverse_phase, places=12)

    def test_registry_renaming_preserves_operation(self):
        default = transport_matrix(compile_rotation(0.9, Registry("ad", "mx")))
        renamed = transport_matrix(compile_rotation(0.9, Registry("plus", "times")))
        self.assertLess(max_abs_matrix_delta(default, renamed), 1e-12)

    def test_noncommuting_shears(self):
        path = compile_rotation(0.9)
        sx, sy, _ = path
        xy = matmul(sx.matrix(), sy.matrix())
        yx = matmul(sy.matrix(), sx.matrix())
        self.assertGreater(max_abs_matrix_delta(xy, yx), 1e-3)

    def test_conjugacy_preserves_trace_and_determinant(self):
        h = transport_matrix(compile_rotation(1.0))
        basis = ((2.0, 0.5), (0.0, 0.5))
        hp = conjugate(h, basis)
        self.assertAlmostEqual(trace(h), trace(hp), places=12)
        self.assertAlmostEqual(determinant(h), determinant(hp), places=12)

    def test_time_schedule_keeps_endpoint_but_changes_rate_signature(self):
        theta = 0.8
        u = path_samples(theta, (1.0, 1.0, 1.0), 60)
        w = path_samples(theta, (2.0, 0.7, 1.3), 60)
        self.assertAlmostEqual(u[-1]["x"], w[-1]["x"], places=12)
        self.assertAlmostEqual(u[-1]["y"], w[-1]["y"], places=12)
        self.assertGreater(abs(finite_difference_rms(u, "angle") - finite_difference_rms(w, "angle")), 1e-3)

    def test_theta_outside_domain_rejected(self):
        for theta in (math.pi, -math.pi, math.inf, math.nan):
            with self.assertRaises(ValueError):
                compile_rotation(theta)

    def test_invalid_axis_rejected(self):
        from codonic_connection import _make_shear
        with self.assertRaises(ValueError):
            _make_shear("z", 0.2, Registry(), 1)

    def test_unknown_codon_rejected(self):
        from codonic_connection import CodonProgram, Instruction, CodonExecutionError
        p = CodonProgram((Instruction("unknown", "x", 1, 2),), Registry())
        with self.assertRaises(CodonExecutionError):
            p.execute(1.0, 0.0)


if __name__ == "__main__":
    unittest.main()
