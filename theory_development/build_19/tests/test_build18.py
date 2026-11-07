import sys
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import relational_atlas as ra


class TestQuaternionAndSU2(unittest.TestCase):
    def setUp(self):
        self.q = ra.q_normalize(np.array([0.3, -0.2, 0.4, 0.5]))

    def test_quaternion_inverse(self):
        ident = ra.q_mul(self.q, ra.q_conj(self.q))
        np.testing.assert_allclose(ident, [1, 0, 0, 0], atol=1e-12)

    def test_su2_unitary_and_determinant(self):
        U = ra.su2_matrix(self.q)
        np.testing.assert_allclose(U.conj().T @ U, np.eye(2), atol=1e-12)
        self.assertAlmostEqual(abs(np.linalg.det(U) - 1), 0, places=12)

    def test_symmetric_power_is_unitary(self):
        for n in range(5):
            D = ra.su2_irrep(self.q, n)
            np.testing.assert_allclose(D.conj().T @ D, np.eye(n+1), atol=1e-11)

    def test_representation_homomorphism(self):
        r = ra.q_normalize(np.array([0.8, 0.2, -0.1, 0.3]))
        qr = ra.q_mul(self.q, r)
        for n in range(5):
            np.testing.assert_allclose(ra.su2_irrep(qr, n),
                                       ra.su2_irrep(self.q, n) @ ra.su2_irrep(r, n),
                                       atol=1e-11)

    def test_antipodal_parity(self):
        for n in range(6):
            self.assertLess(ra.antipodal_parity(self.q, n), 1e-11)

    def test_s3_geodesic_antipodes_are_maximally_separated(self):
        self.assertAlmostEqual(ra.q_distance_s3(self.q, -self.q), np.pi, places=12)

    def test_hopf_map_is_unit_vector(self):
        self.assertAlmostEqual(np.linalg.norm(ra.hopf_map(self.q)), 1.0, places=12)

    def test_hopf_map_constant_on_fibre(self):
        base = ra.hopf_map(self.q)
        for beta in np.linspace(0, 2*np.pi, 17):
            moved = ra.q_mul(self.q, ra.fibre_element(beta))
            np.testing.assert_allclose(ra.hopf_map(moved), base, atol=1e-12)

    def test_fibre_average_removes_half_integer_spin(self):
        for n in (1, 3, 5):
            avg = ra.fibre_average_rep(self.q, n, samples=256)
            self.assertLess(np.linalg.norm(avg), 1e-10)

    def test_fibre_average_retains_integer_spin_zero_weight(self):
        for n in (0, 2, 4):
            avg = ra.fibre_average_rep(self.q, n, samples=256)
            expected = ra.su2_irrep(self.q, n) @ ra.fibre_projector_expected(n)
            np.testing.assert_allclose(avg, expected, atol=1e-10)

    def test_fibre_projector_rank(self):
        for n in (1, 3, 5):
            self.assertEqual(np.linalg.matrix_rank(ra.fibre_projector_expected(n)), 0)
        for n in (0, 2, 4):
            self.assertEqual(np.linalg.matrix_rank(ra.fibre_projector_expected(n)), 1)

    def test_left_right_translation_preserves_representation_band_energy(self):
        a = ra.q_normalize(np.array([0.6, 0.1, 0.4, -0.3]))
        b = ra.q_normalize(np.array([0.4, -0.2, 0.5, 0.1]))
        Dq = ra.su2_irrep(self.q, 3)
        Dnew = ra.su2_irrep(ra.q_mul(ra.q_mul(a, self.q), b), 3)
        predicted = ra.su2_irrep(a, 3) @ Dq @ ra.su2_irrep(b, 3)
        np.testing.assert_allclose(Dnew, predicted, atol=1e-11)
        self.assertAlmostEqual(np.linalg.norm(Dq, "fro"), np.linalg.norm(Dnew, "fro"), places=11)
        self.assertAlmostEqual(np.linalg.norm(Dq, "fro"), np.sqrt(4), places=11)

    def test_schur_orthogonality_monte_carlo(self):
        error = ra.haar_schur_error(n=1, count=18000, seed=77)
        self.assertLess(error, 0.008)


class TestIntertwiners(unittest.TestCase):
    def test_unitary_intertwiner_and_gram_preservation(self):
        result = ra.unitary_intertwiner_demo()
        self.assertLess(result["intertwiner_residual"], 1e-10)
        self.assertLess(result["gram_matrix_error"], 1e-10)

    def test_observer_charts_make_information_loss_explicit(self):
        names = {x.name: x for x in ra.OBSERVER_CHARTS}
        self.assertIn("fibre_phase", names["S3-lift"].visible_coordinates)
        self.assertIn("fibre_phase", names["Hopf-base"].lost_coordinates)
        self.assertIn("absolute duration", names["Clock-free path"].lost_coordinates)
        self.assertIn("elapsed-time coordinate", names["Timed path"].visible_coordinates)


class TestPathSignatures(unittest.TestCase):
    def test_signature_straight_segment_subdivision_invariant(self):
        whole = ra.truncated_path_signature(np.array([[0.,0.],[2.,1.]]), depth=3)
        split = ra.truncated_path_signature(np.array([[0.,0.],[1.,0.5],[2.,1.]]), depth=3)
        self.assertLess(ra.signature_error(whole, split), 1e-12)

    def test_piecewise_linear_reparameterization_preserves_signature(self):
        coarse = np.array([[0.,0.],[1.,0.],[1.,1.]])
        dense = np.array([[0.,0.],[0.1,0.],[0.6,0.],[1.,0.],[1.,0.2],[1.,0.7],[1.,1.]])
        sig_coarse = ra.truncated_path_signature(coarse, depth=3)
        sig_dense = ra.truncated_path_signature(dense, depth=3)
        self.assertLess(ra.signature_error(sig_coarse, sig_dense), 1e-12)

    def test_tree_like_backtrack_has_trivial_signature(self):
        path = np.array([[0.,0.],[1.,0.],[0.,0.]])
        sig = ra.truncated_path_signature(path, depth=4)
        expected = [np.array(1.0)] + [np.zeros((2,)*k) for k in range(1,5)]
        self.assertLess(ra.signature_error(sig, expected), 1e-12)

    def test_path_orientation_is_detected(self):
        forward = ra.truncated_path_signature(np.array([[0.,0.],[1.,0.],[1.,1.]]), depth=2)
        reverse = ra.truncated_path_signature(np.array([[1.,1.],[1.,0.],[0.,0.]]), depth=2)
        self.assertGreater(ra.signature_error(forward, reverse), 0.1)

    def test_signature_degree_one_is_endpoint_displacement(self):
        path = np.array([[0.,0.],[0.2,0.7],[1.0,-0.1]])
        sig = ra.truncated_path_signature(path, depth=2)
        np.testing.assert_allclose(sig[1], path[-1]-path[0], atol=1e-12)

    def test_time_augmented_signature_retains_duration_change(self):
        state_path = np.array([[0.,0.],[1.,0.],[1.,1.]])
        time_a = np.array([0.,1.,2.])
        time_b = np.array([0.,2.,4.])
        geom_a = ra.truncated_path_signature(state_path, depth=3)
        geom_b = ra.truncated_path_signature(state_path, depth=3)
        timed_a = ra.truncated_path_signature(np.column_stack([time_a, state_path]), depth=3)
        timed_b = ra.truncated_path_signature(np.column_stack([time_b, state_path]), depth=3)
        self.assertLess(ra.signature_error(geom_a, geom_b), 1e-12)
        self.assertGreater(ra.signature_error(timed_a, timed_b), 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
