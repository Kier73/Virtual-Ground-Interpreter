import sys
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import relational_atlas as ra
import build_19 as b19


class TestEndpointAndPathComplementarity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = b19.make_fixture_paths()
        cls.names = list(cls.paths)
        cls.indices = {name: i for i, name in enumerate(cls.names)}
        cls.path_list = [cls.paths[n] for n in cls.names]

    def test_endpoint_harmonics_cannot_distinguish_same_endpoint_different_paths(self):
        a = b19.endpoint_harmonic_feature(self.paths["reference"][-1], "s3", 4)
        b = b19.endpoint_harmonic_feature(self.paths["alternate_same_endpoint"][-1], "s3", 4)
        self.assertLess(b19.feature_distance(a, b), 1e-12)

    def test_second_signature_level_separates_paths_with_same_endpoints(self):
        A = b19.observer_path(self.paths["reference"], "s3")
        B = b19.observer_path(self.paths["alternate_same_endpoint"], "s3")
        sig_a_1 = ra.truncated_path_signature(A, depth=1)
        sig_b_1 = ra.truncated_path_signature(B, depth=1)
        self.assertLess(ra.signature_error(sig_a_1, sig_b_1), 1e-11)
        sig_a_2 = ra.truncated_path_signature(A, depth=2)
        sig_b_2 = ra.truncated_path_signature(B, depth=2)
        self.assertGreater(ra.signature_error(sig_a_2, sig_b_2), 0.1)

    def test_first_signature_level_reconstructs_endpoint_when_start_is_known(self):
        P = self.paths["reference"]
        sig = ra.truncated_path_signature(b19.observer_path(P, "s3"), depth=1)
        self.assertLess(np.linalg.norm(P[0] + sig[1] - P[-1]), 1e-12)
        reconstructed = b19.endpoint_harmonic_feature(P[0] + sig[1], "s3", 4)
        direct = b19.endpoint_harmonic_feature(P[-1], "s3", 4)
        self.assertLess(b19.feature_distance(reconstructed, direct), 1e-12)

    def test_joint_kernel_separates_path_that_endpoint_kernel_collapses(self):
        mats = b19.representation_kernels(self.path_list, "s3", 4, 3)
        i = self.indices["reference"]
        j = self.indices["alternate_same_endpoint"]
        self.assertLess(b19.kernel_distance_matrix(mats["endpoint"])[i, j], 1e-12)
        self.assertGreater(b19.kernel_distance_matrix(mats["path"])[i, j], 0.1)
        self.assertGreater(b19.kernel_distance_matrix(mats["joint"])[i, j], 0.1)


class TestObserverQuotients(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = b19.make_fixture_paths()
        cls.names = list(cls.paths)
        cls.indices = {name: i for i, name in enumerate(cls.names)}
        cls.path_list = [cls.paths[n] for n in cls.names]

    def _distance(self, observer, component, left, right):
        K = b19.representation_kernels(self.path_list, observer, 4, 3)[component]
        D = b19.kernel_distance_matrix(K)
        return float(D[self.indices[left], self.indices[right]])

    def test_s3_observer_sees_variable_fibre_phase(self):
        self.assertGreater(self._distance("s3", "joint", "reference", "fibre_shifted"), 0.1)

    def test_hopf_observer_cannot_see_fibre_phase(self):
        self.assertLess(self._distance("hopf", "endpoint", "reference", "fibre_shifted"), 1e-11)
        self.assertLess(self._distance("hopf", "path", "reference", "fibre_shifted"), 1e-11)
        self.assertLess(self._distance("hopf", "joint", "reference", "fibre_shifted"), 1e-11)

    def test_so3_observer_identifies_antipodal_lifts(self):
        self.assertLess(self._distance("so3", "endpoint", "reference", "antipodal_lift"), 1e-11)
        self.assertLess(self._distance("so3", "path", "reference", "antipodal_lift"), 1e-10)

    def test_s3_observer_distinguishes_antipodal_lifts(self):
        self.assertGreater(self._distance("s3", "endpoint", "reference", "antipodal_lift"), 0.1)
        self.assertGreater(self._distance("s3", "path", "reference", "antipodal_lift"), 0.1)

    def test_hopf_projection_is_pointwise_equal_for_fibre_shift(self):
        A = np.stack([ra.hopf_map(q) for q in self.paths["reference"]])
        B = np.stack([ra.hopf_map(q) for q in self.paths["fibre_shifted"]])
        np.testing.assert_allclose(A, B, atol=1e-12)


class TestPathEquivalencesAndTime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = b19.make_fixture_paths()
        cls.path_list = [cls.paths[n] for n in cls.paths]
        cls.names = list(cls.paths)
        cls.indices = {name: i for i, name in enumerate(cls.names)}

    def _distance(self, observer, component, left, right):
        K = b19.representation_kernels(self.path_list, observer, 4, 3)[component]
        D = b19.kernel_distance_matrix(K)
        return float(D[self.indices[left], self.indices[right]])

    def test_change_of_time_labels_does_not_change_geometric_signature(self):
        p = self.paths["reference"]
        t1 = np.linspace(0.0, 1.0, len(p))
        split = len(p)//2
        t2 = np.concatenate([np.linspace(0.0, 0.9, split+1),
                             np.linspace(0.9, 1.0, len(p)-split)[1:]])
        a = b19.signature_feature(b19.observer_path(p, "s3"), 3)
        b = b19.signature_feature(b19.observer_path(p, "s3"), 3)
        self.assertLess(b19.feature_distance(a, b), 1e-12)
        self.assertGreater(b19.feature_distance(
            b19.time_augmented_signature(p, t1),
            b19.time_augmented_signature(p, t2)), 0.01)

    def test_tree_like_forward_reverse_excursion_is_quotiented(self):
        for observer in ("s3", "so3", "hopf"):
            d = self._distance(observer, "path", "reference", "tree_like_excursion")
            self.assertLess(d, 1e-7, msg=f"{observer}: {d}")

    def test_different_sampling_density_on_same_geodesic_path_canonicalizes(self):
        q0 = np.array([1., 0., 0., 0.])
        q1 = ra.q_normalize(np.array([0.5, 0.5, 0.5, 0.5]))
        qm = ra.q_normalize(np.array([0.5, -0.5, 0.5, -0.5]))
        p1 = b19.sample_s3_polyline(np.stack([q0, qm, q1]), [2, 13])
        p2 = b19.sample_s3_polyline(np.stack([q0, qm, q1]), [8, 8])
        c1 = b19.canonical_s3_path(p1)
        c2 = b19.canonical_s3_path(p2)
        np.testing.assert_allclose(c1, c2, atol=1e-12)
        f1 = b19.signature_feature(c1, 3)
        f2 = b19.signature_feature(c2, 3)
        self.assertLess(b19.feature_distance(f1, f2), 1e-11)

    def test_perturbation_response_is_finite_and_increases_with_noise(self):
        p = self.paths["reference"]
        rng = np.random.default_rng(1901)
        errors = []
        for sigma in (1e-4, 1e-3, 1e-2):
            noisy = p + rng.normal(0.0, sigma, p.shape)
            noisy = np.stack([ra.q_normalize(q) for q in noisy])
            errors.append(b19.feature_distance(
                b19.signature_feature(b19.observer_path(p, "s3"), 3),
                b19.signature_feature(b19.observer_path(noisy, "s3"), 3)))
        self.assertTrue(np.all(np.isfinite(errors)))
        self.assertLess(errors[0], errors[1])
        self.assertLess(errors[1], errors[2])


class TestObserverKernels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = b19.make_fixture_paths()
        cls.path_list = [cls.paths[n] for n in cls.paths]

    def test_all_observer_kernels_are_positive_semidefinite(self):
        for observer in ("s3", "so3", "hopf"):
            mats = b19.representation_kernels(self.path_list, observer, 4, 3)
            for name, K in mats.items():
                self.assertLess(b19.max_psd_violation(K), 1e-10, (observer, name))

    def test_kernel_distance_equals_feature_space_distance(self):
        P = b19.path_feature_matrix(self.path_list, "s3", 3)
        K = b19.linear_gram(P)
        i, j = 0, 1
        d1 = b19.kernel_distance_matrix(K)[i, j]
        d2 = b19.feature_distance(P[i], P[j])
        self.assertAlmostEqual(d1, d2, places=10)

    def test_common_left_right_action_preserves_all_s3_gram_relations(self):
        mats = b19.representation_kernels(self.path_list, "s3", 4, 3)
        a = ra.q_normalize(np.array([0.7, -0.2, 0.4, 0.5]))
        b = ra.q_normalize(np.array([0.8, 0.1, -0.3, 0.4]))
        moved = [np.stack([ra.q_mul(ra.q_mul(a, q), b) for q in p]) for p in self.path_list]
        moved_mats = b19.representation_kernels(moved, "s3", 4, 3)
        for name in mats:
            np.testing.assert_allclose(mats[name], moved_mats[name], atol=1e-10)

    def test_kernel_does_not_add_separation_beyond_its_feature_map(self):
        P = b19.path_feature_matrix(self.path_list, "s3", 3)
        K = b19.linear_gram(P)
        D = b19.kernel_distance_matrix(K)
        for i in range(len(P)):
            for j in range(len(P)):
                self.assertAlmostEqual(D[i, j], b19.feature_distance(P[i], P[j]), places=9)

    def test_joint_kernel_is_weighted_sum_of_component_kernels(self):
        mats = b19.representation_kernels(self.path_list, "s3", 4, 3)
        np.testing.assert_allclose(mats["joint"],
                                   0.5*mats["endpoint"] + 0.5*mats["path"],
                                   atol=1e-12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
