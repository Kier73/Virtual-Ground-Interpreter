import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cross_observer_invariants as m  # noqa: E402


class Build07Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = m.build_library()
        cls.rdms = {name: m.build_rdm(cls.candidates, name)
                    for name in ("base_shape", "holonomy", "temporal", "local_transition")}

    def test_candidate_library_has_32_paths(self):
        self.assertEqual(len(self.candidates), 32)

    def test_library_has_eight_geometric_families(self):
        self.assertEqual(len(m.SHAPES), 8)
        self.assertEqual(len({c.shape_id for c in self.candidates}), 8)

    def test_all_base_paths_are_closed_at_north(self):
        for c in self.candidates:
            self.assertLess(m.geodesic_s2(c.path[0], m.NORTH), 1e-12)
            self.assertLess(m.geodesic_s2(c.path[-1], m.NORTH), 1e-12)

    def test_all_lifts_project_to_their_base_paths(self):
        for c in self.candidates:
            for q, p in zip(c.lift[::max(1, len(c.lift)//12)], c.path[::max(1, len(c.path)//12)]):
                observed = m.DEFAULT_Q.rotate(q, m.NORTH)
                self.assertLess(m.geodesic_s2(observed, p), 1e-7)

    def test_horizontal_lift_closes_onto_same_fibre(self):
        for c in self.candidates:
            phase, residual = m.fibre_phase(c.lift[0], c.lift[-1], m.DEFAULT_Q)
            self.assertTrue(math.isfinite(phase))
            self.assertLess(residual, 2e-5)

    def test_geometric_path_is_reparameterization_invariant(self):
        for spec in m.SHAPES:
            a = m.build_candidate(spec, 1, 1.0)
            b = m.build_candidate(spec, 1, 1.7)
            self.assertEqual(a.path, b.path)
            self.assertEqual(a.phase, b.phase)

    def test_temporal_signal_changes_under_time_warp(self):
        changes = m.reparameterization_checks(self.candidates)
        self.assertGreater(changes["min_temporal_signature_change"], 0.3)

    def test_base_shape_and_holonomy_invariant_under_time_warp(self):
        result = m.reparameterization_checks(self.candidates)
        self.assertLess(result["max_base_shape_signature_error"], 1e-12)
        self.assertLess(result["max_holonomy_phase_error"], 1e-12)
        self.assertLess(result["max_s3_endpoint_error"], 1e-12)

    def test_reverse_paths_preserve_shape_and_reverse_signed_phase(self):
        by_name = {c.name: c for c in self.candidates}
        for spec in m.SHAPES:
            fwd = by_name[f"{spec.shape_id}_fwd_g1"]
            rev = by_name[f"{spec.shape_id}_rev_g1"]
            self.assertLess(m.euclidean(m.signature_base_shape(fwd), m.signature_base_shape(rev)), 1e-10)
            self.assertLess(m.euclidean(m.signature_local_transition(fwd), m.signature_local_transition(rev)), 1e-8)
            self.assertLess(abs(m.wrap_pi(fwd.phase + rev.phase)), 1e-10)

    def test_rdm_dimensions_symmetry_and_zero_diagonal(self):
        n = len(self.candidates)
        for rdm in self.rdms.values():
            self.assertEqual(len(rdm), n)
            for i in range(n):
                self.assertEqual(rdm[i][i], 0.0)
                for j in range(n):
                    self.assertAlmostEqual(rdm[i][j], rdm[j][i], places=12)
                    self.assertGreaterEqual(rdm[i][j], 0.0)

    def test_base_shape_and_local_transition_share_knn(self):
        overlap = m.mean_neighbor_jaccard(self.rdms["base_shape"], self.rdms["local_transition"], 3)
        self.assertAlmostEqual(overlap, 1.0, places=12)

    def test_base_shape_and_local_transition_rdm_relation(self):
        corr = m.spearman(m.upper_triangle(self.rdms["base_shape"]),
                          m.upper_triangle(self.rdms["local_transition"]))
        self.assertGreater(corr, 0.65)

    def test_temporal_observer_separates_all_time_warp_variants(self):
        groups = m.observer_equivalence_pairs(self.candidates, self.rdms["temporal"], 0.1)
        self.assertEqual(len(groups), 32)

    def test_base_shape_observer_collapses_each_shape_family(self):
        groups = m.observer_equivalence_pairs(self.candidates, self.rdms["base_shape"], 0.02)
        self.assertEqual(len(groups), 8)
        self.assertTrue(all(len(g) == 4 for g in groups))

    def test_local_transition_observer_collapses_each_shape_family(self):
        groups = m.observer_equivalence_pairs(self.candidates, self.rdms["local_transition"], 0.05)
        self.assertEqual(len(groups), 8)
        self.assertTrue(all(len(g) == 4 for g in groups))

    def test_holonomy_observer_refines_by_orientation(self):
        groups = m.observer_equivalence_pairs(self.candidates, self.rdms["holonomy"], 5e-5)
        self.assertEqual(len(groups), 12)
        self.assertTrue(all(len(g) in (2, 4) for g in groups))

    def test_codon_alias_renaming_preserves_quaternion_product(self):
        self.assertTrue(m.alias_renaming_check()["passed"])
        self.assertEqual(m.alias_renaming_check()["max_abs_error"], 0.0)

    def test_phase_half_area_converges_with_resolution(self):
        result = m.resolution_check((180, 360, 720))
        errors = [x["phase_half_area_error"] for x in result["samples"]]
        self.assertGreater(errors[0], errors[1])
        self.assertGreater(errors[1], errors[2])
        self.assertLess(errors[-1], 2e-5)

    def test_zero_dimensional_persistence_has_n_minus_one_deaths(self):
        for rdm in self.rdms.values():
            deaths = m.h0_death_curve(rdm)
            self.assertEqual(len(deaths), len(self.candidates)-1)
            self.assertEqual(deaths, sorted(deaths))

    def test_graph_laplacian_spectra_are_nonnegative(self):
        for rdm in self.rdms.values():
            eig = m.graph_laplacian_spectrum(rdm)
            self.assertEqual(len(eig), len(self.candidates))
            self.assertGreater(eig[0], -1e-8)
            self.assertLess(eig[0], 1e-8)
            self.assertTrue(all(eig[i] <= eig[i+1]+1e-10 for i in range(len(eig)-1)))

    def test_block_permutation_control_is_deterministic(self):
        a = m.block_permutation_control(self.rdms["base_shape"], self.rdms["local_transition"],
                                        trials=49, seed=99)
        b = m.block_permutation_control(self.rdms["base_shape"], self.rdms["local_transition"],
                                        trials=49, seed=99)
        self.assertEqual(a["null_correlations"], b["null_correlations"])

    def test_h0_interpretation_is_cautioned(self):
        report = m.run_analysis()
        note = report["h0_interpretation_note"]
        self.assertIn("not, by itself, evidence", note)


if __name__ == "__main__":
    unittest.main(verbosity=2)
