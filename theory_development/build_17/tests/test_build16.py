import math
import random
import unittest

from harmonic_representations import (
    dft, idft, fourier_diagnostics, inner_product, norm_squared,
    circular_shift, spectrum_magnitude, graph_laplacian,
    symmetric_jacobi_eigensystem, graph_fourier, permute_square_matrix,
    eigenvalue_multiplicity_groups,
)
from local_clock_graph import EventStream, align_event_streams, analyze_stream_pair, affine_clock_transform
from build_16 import make_pair, score_alignment, evaluate_weights


class TestFiniteFourier(unittest.TestCase):
    def setUp(self):
        rng = random.Random(17)
        self.x = [complex(rng.uniform(-1,1), rng.uniform(-1,1)) for _ in range(13)]
        self.y = [complex(rng.uniform(-1,1), rng.uniform(-1,1)) for _ in range(13)]

    def test_inverse(self):
        self.assertLess(max(abs(a-b) for a,b in zip(self.x, idft(dft(self.x)))), 1e-10)

    def test_parseval_norm(self):
        self.assertAlmostEqual(norm_squared(self.x), norm_squared(dft(self.x)), places=10)

    def test_inner_product_preserved(self):
        self.assertAlmostEqual(abs(inner_product(self.x,self.y)-inner_product(dft(self.x),dft(self.y))), 0, places=10)

    def test_fourth_power_identity(self):
        d = fourier_diagnostics(self.x)
        self.assertLess(d["fourth_power_identity_max_abs_error"], 1e-10)

    def test_round_trip_and_parseval_diagnostics(self):
        d = fourier_diagnostics(self.x)
        self.assertLess(d["reconstruction_max_abs_error"], 1e-10)
        self.assertLess(d["parseval_abs_error"], 1e-10)

    def test_circular_shift_changes_phase_not_magnitude(self):
        a = spectrum_magnitude(self.x)
        b = spectrum_magnitude(circular_shift(self.x, 4))
        self.assertLess(max(abs(x-y) for x,y in zip(a,b)), 1e-10)

    def test_empty_input_rejected(self):
        with self.assertRaises(ValueError): dft([])
        with self.assertRaises(ValueError): idft([])


class TestGraphFourier(unittest.TestCase):
    def setUp(self):
        # A 5-node weighted path with one extra chord; positive connected graph.
        self.a = [
            [0,1,0,0,0.4],
            [1,0,1,0,0],
            [0,1,0,1,0],
            [0,0,1,0,1],
            [0.4,0,0,1,0],
        ]
        self.x = [0.2, -0.7, 1.3, 0.1, 0.8]

    def test_laplacian_symmetric(self):
        l = graph_laplacian(self.a)
        for i in range(len(l)):
            for j in range(len(l)):
                self.assertAlmostEqual(l[i][j], l[j][i])

    def test_laplacian_zero_row_sums(self):
        l = graph_laplacian(self.a)
        for row in l:
            self.assertAlmostEqual(sum(row), 0.0, places=12)

    def test_laplacian_psd(self):
        vals, _ = symmetric_jacobi_eigensystem(graph_laplacian(self.a))
        self.assertGreaterEqual(min(vals), -1e-10)

    def test_connected_graph_has_one_zero_mode(self):
        vals, _ = symmetric_jacobi_eigensystem(graph_laplacian(self.a))
        self.assertEqual(sum(abs(x) < 1e-9 for x in vals), 1)

    def test_eigenvectors_orthonormal(self):
        vals, u = symmetric_jacobi_eigensystem(graph_laplacian(self.a))
        n = len(vals)
        for i in range(n):
            for j in range(n):
                dot = sum(u[k][i]*u[k][j] for k in range(n))
                self.assertAlmostEqual(dot, 1.0 if i == j else 0.0, places=9)

    def test_graph_fourier_parseval(self):
        r = graph_fourier(self.a, self.x)
        self.assertLess(r["parseval_abs_error"], 1e-9)

    def test_graph_fourier_reconstruction(self):
        r = graph_fourier(self.a, self.x)
        self.assertLess(r["reconstruction_max_abs_error"], 1e-9)

    def test_node_relabeling_preserves_spectrum(self):
        p = [4,2,0,3,1]
        ap = permute_square_matrix(self.a, p)
        v1, _ = symmetric_jacobi_eigensystem(graph_laplacian(self.a))
        v2, _ = symmetric_jacobi_eigensystem(graph_laplacian(ap))
        self.assertLess(max(abs(x-y) for x,y in zip(v1,v2)), 1e-9)

    def test_multiplicity_groups(self):
        g = eigenvalue_multiplicity_groups([0.0, 1.0, 1.0+1e-10, 3.0])
        self.assertEqual([x["multiplicity"] for x in g], [1,2,1])

    def test_invalid_asymmetry_rejected(self):
        with self.assertRaises(ValueError): graph_laplacian([[0,1],[0,0]])


class TestEventGraphAndControls(unittest.TestCase):
    def test_affine_clock_transform_does_not_change_match_pairs(self):
        a = EventStream("A", (0,1,2,4,7,8,11), (0.2,0.8,0.3,0.7,0.1,0.9,0.5))
        b = EventStream("B", tuple(19+3.7*t for t in a.local_times_s),
                        tuple(5+2*m for m in a.marks))
        x = align_event_streams(a,b)
        self.assertEqual([(m["left_index"],m["right_index"]) for m in x["matches"]],
                         [(i,i) for i in range(7)])

    def test_affine_clock_relation_recovered_after_matching(self):
        a = EventStream("A", (0,1,2,4,7,8,11), (0.2,0.8,0.3,0.7,0.1,0.9,0.5))
        b = EventStream("B", tuple(19+3.7*t for t in a.local_times_s),
                        tuple(5+2*m for m in a.marks))
        result = analyze_stream_pair(a,b)
        relation = result["post_match_clock_relation"]["left_time_approximately_equals_offset_plus_scale_times_right_time"]
        self.assertAlmostEqual(relation["scale"], 1/3.7, places=9)
        self.assertAlmostEqual(relation["offset_s"], -19/3.7, places=9)

    def test_no_clock_edges_in_coupled_graph(self):
        a = EventStream("A", (0,1,2,4,7,8,11), (0.2,0.8,0.3,0.7,0.1,0.9,0.5))
        b = EventStream("B", tuple(19+3.7*t for t in a.local_times_s),
                        tuple(5+2*m for m in a.marks))
        result = analyze_stream_pair(a,b)
        self.assertEqual(result["graph"]["cross_observer_clock_edges"], 0)

    def test_mark_only_synthetic_signal_is_informative(self):
        result = evaluate_weights(list(range(40,50)), mark_weight=1, interval_weight=0)
        self.assertGreater(result["mean_f1"], 0.80)

    def test_independent_mark_shuffle_reduces_alignment(self):
        seeds = list(range(60,70))
        baseline = evaluate_weights(seeds, mark_weight=0.78, interval_weight=0.22)
        shuffled = evaluate_weights(seeds, mark_weight=0.78, interval_weight=0.22,
                                    shuffle_b_marks=True)
        self.assertLess(shuffled["mean_f1"], baseline["mean_f1"] - 0.2)

    def test_event_order_shuffle_is_strong_negative_control(self):
        result = evaluate_weights(list(range(70,80)), mark_weight=0.78,
                                  interval_weight=0.22, shuffle_b_order=True)
        self.assertLess(result["mean_f1"], 0.25)

    def test_mark_rank_invariant_to_monotone_affine_mark_transform(self):
        a = EventStream("A", (0,1,3,4,8), (0.2,0.4,0.1,0.9,0.7))
        b = EventStream("B", (5,7,11,13,21), tuple(11+4*m for m in a.marks))
        res = align_event_streams(a,b,mark_weight=1.0,interval_weight=0.0)
        self.assertEqual(len(res["matches"]),5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
