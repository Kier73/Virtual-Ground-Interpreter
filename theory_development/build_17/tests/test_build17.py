import math
import unittest

from temporal_representations import (
    circular_shift, fourier_magnitude, stft_magnitude,
    stft_shift_covariance_error, stationary_haar_detail_energies,
    log_mellin_magnitude, positive_log_grid_signal, time_dilate_log_samples,
    gaussian_event_signal, dilate_signal_about_center, warp_signal_quadratic,
    graph_spectral_signature, graph_signature_permutation_diagnostic,
    normalized_log_intervals, relative_l2, run_representation_comparison,
    quadratic_clock_map, event_graph,
)


class Build17Tests(unittest.TestCase):
    def test_fourier_magnitude_circular_shift_invariant(self):
        x,_=gaussian_event_signal()
        self.assertLess(relative_l2(fourier_magnitude(x),fourier_magnitude(circular_shift(x,32))),1e-12)

    def test_stft_is_shift_covariant_for_hop_aligned_shift(self):
        x,_=gaussian_event_signal()
        self.assertLess(stft_shift_covariance_error(x,32),1e-12)

    def test_stft_feature_field_changes_under_nonlinear_warp(self):
        x,_=gaussian_event_signal()
        y=warp_signal_quadratic(x,0.35)
        a=[v for row in stft_magnitude(x) for v in row]
        b=[v for row in stft_magnitude(y) for v in row]
        self.assertGreater(relative_l2(a,b),0.05)

    def test_haar_pooled_energy_shift_invariant(self):
        x,_=gaussian_event_signal()
        a=stationary_haar_detail_energies(x,max_level=6)
        b=stationary_haar_detail_energies(circular_shift(x,17),max_level=6)
        self.assertLess(relative_l2(a,b),1e-12)

    def test_haar_energy_redistributes_under_dilation(self):
        x,_=gaussian_event_signal()
        a=stationary_haar_detail_energies(x,max_level=6)
        b=stationary_haar_detail_energies(dilate_signal_about_center(x,1.15),max_level=6)
        self.assertGreater(relative_l2(a,b),0.01)

    def test_mellin_magnitude_invariant_to_log_grid_translation(self):
        _,x=positive_log_grid_signal()
        a=log_mellin_magnitude(x)
        b=log_mellin_magnitude(time_dilate_log_samples(x,8))
        self.assertLess(relative_l2(a,b),1e-12)

    def test_fourier_spectrum_changes_under_time_dilation(self):
        x,_=gaussian_event_signal()
        y=dilate_signal_about_center(x,1.15)
        self.assertGreater(relative_l2(fourier_magnitude(x),fourier_magnitude(y)),0.01)

    def test_affine_clock_preserves_graph_spectrum(self):
        _,centers=gaussian_event_signal()
        a=graph_spectral_signature(centers)
        b=graph_spectral_signature([13.0+2.75*t for t in centers])
        self.assertLess(relative_l2(a["eigenvalues"],b["eigenvalues"]),1e-10)

    def test_nonlinear_clock_changes_graph_spectrum(self):
        _,centers=gaussian_event_signal()
        warped=[quadratic_clock_map(t,511.0,0.35) for t in centers]
        a=graph_spectral_signature(centers)
        b=graph_spectral_signature(warped)
        self.assertGreater(relative_l2(a["eigenvalues"],b["eigenvalues"]),1e-5)

    def test_recurrence_edges_parameterized_and_reported(self):
        _,centers=gaussian_event_signal()
        a,_=event_graph(centers,motif_tolerance=0.3)
        b,_=event_graph(centers,motif_tolerance=0.6)
        count=lambda m: sum(1 for i in range(len(m)) for j in range(i+2,len(m)) if m[i][j]>0)
        self.assertLess(count(a),count(b))

    def test_graph_spectral_projector_invariant_under_node_relabeling(self):
        _,centers=gaussian_event_signal()
        result=graph_signature_permutation_diagnostic(centers)
        self.assertLess(result["eigenvalue_max_abs_error"],1e-10)
        self.assertLess(result["eigenspace_energy_max_abs_error"],1e-9)

    def test_normalized_intervals_affine_invariant(self):
        _,centers=gaussian_event_signal()
        a=normalized_log_intervals(centers)
        b=normalized_log_intervals([100+3.2*t for t in centers])
        self.assertLess(relative_l2(a,b),1e-12)

    def test_normalized_intervals_not_invariant_to_nonlinear_map(self):
        _,centers=gaussian_event_signal()
        warped=[quadratic_clock_map(t,511.0,0.35) for t in centers]
        self.assertGreater(relative_l2(normalized_log_intervals(centers),normalized_log_intervals(warped)),1e-5)

    def test_result_explicitly_synthetic_only(self):
        result=run_representation_comparison()
        self.assertIn("synthetic",result["provenance"])
        self.assertTrue(any("no physical sensor" in x for x in result["caveats"]))

    def test_invalid_stft_shift_rejected(self):
        x,_=gaussian_event_signal()
        with self.assertRaises(ValueError):
            stft_shift_covariance_error(x,3)


if __name__=="__main__":
    unittest.main()
