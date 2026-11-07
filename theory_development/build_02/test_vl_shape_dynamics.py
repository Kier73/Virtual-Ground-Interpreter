import math
import unittest

from vl_shape_dynamics import (
    Observer, ellipse_trace, trace_with_observer, response_signature,
    discrete_line_integral, signed_area, stable_limit_cycle_trace,
    estimate_decay_rate, Intention, intention_distance, moving_average, rms,
)


class ShapeDynamicsTests(unittest.TestCase):
    def test_closed_ellipse_phase_converges_to_signed_area(self):
        a, b = 1.3, 0.6
        t, p = ellipse_trace(a, b, n=8192)
        area = signed_area(p)
        phase = discrete_line_integral(p)
        self.assertAlmostEqual(area, math.pi * a * b, places=6)
        self.assertAlmostEqual(phase, area, places=10)

    def test_time_reparameterization_preserves_geometric_phase(self):
        obs = Observer("identity")
        tu, pu = ellipse_trace(1.2, 0.7, n=4096, timing="uniform")
        tw, pw = ellipse_trace(1.2, 0.7, n=4096, timing="warped", warp=0.45)
        su = response_signature(trace_with_observer(tu, pu, obs), obs)
        sw = response_signature(trace_with_observer(tw, pw, obs), obs)
        self.assertAlmostEqual(su["geometric_phase"], sw["geometric_phase"], places=6)
        self.assertAlmostEqual(su["signed_area"], sw["signed_area"], places=6)
        self.assertGreater(abs(su["phase_rate_rms"] - sw["phase_rate_rms"]), 0.05)

    def test_reversing_path_reverses_phase(self):
        obs = Observer("identity")
        tf, pf = ellipse_trace(1.0, 0.8, n=2048, direction=1)
        tr, pr = ellipse_trace(1.0, 0.8, n=2048, direction=-1)
        sf = response_signature(trace_with_observer(tf, pf, obs), obs)
        sr = response_signature(trace_with_observer(tr, pr, obs), obs)
        self.assertAlmostEqual(sf["geometric_phase"], -sr["geometric_phase"], places=7)

    def test_area_preserving_observer_preserves_phase(self):
        t, p = ellipse_trace(1.2, 0.7, n=2048)
        identity = Observer("identity")
        stretch = Observer("stretch", ((2.0, 0.0), (0.0, 0.5)))
        s1 = response_signature(trace_with_observer(t, p, identity), identity)
        s2 = response_signature(trace_with_observer(t, p, stretch), stretch)
        self.assertAlmostEqual(s1["geometric_phase"], s2["geometric_phase"], places=7)

    def test_rank_deficient_observer_collapses_area(self):
        t, p = ellipse_trace(1.0, 0.8, n=2048)
        blind = Observer("blind", ((1.0, 0.0), (0.0, 0.0)))
        sig = response_signature(trace_with_observer(t, p, blind), blind)
        self.assertAlmostEqual(sig["signed_area"], 0.0, places=10)
        self.assertAlmostEqual(sig["geometric_phase"], 0.0, places=10)

    def test_intention_selects_different_notions_of_distance(self):
        t1, p1 = ellipse_trace(1.0, 1.0, n=2048, timing="uniform")
        t2, p2 = ellipse_trace(1.0, 1.0, n=2048, timing="warped", warp=0.45)
        obs = Observer("identity")
        s1 = response_signature(trace_with_observer(t1, p1, obs), obs)
        s2 = response_signature(trace_with_observer(t2, p2, obs), obs)
        shape = Intention("shape", {"geometric_phase": 1.0, "signed_area": 1.0})
        tone = Intention("tone", {"phase_rate_rms": 1.0, "phase_rate_cv": 1.0})
        self.assertLess(intention_distance(s1, s2, shape), 1e-5)
        self.assertGreater(intention_distance(s1, s2, tone), 0.05)

    def test_stable_cycle_decay_rate_recovered(self):
        t, p, e = stable_limit_cycle_trace(kappa=0.63, duration=7.0, n=4096)
        estimate = estimate_decay_rate(t[::16], e[::16])
        self.assertAlmostEqual(estimate, 0.63, places=10)

    def test_noise_filter_also_suppresses_same_frequency_signal(self):
        n = 2000
        high = [math.sin(2.0 * math.pi * 80.0 * i / n) for i in range(n)]
        filtered = moving_average(high, 25)
        gain = rms(filtered) / rms(high)
        self.assertLess(gain, 0.5)

    def test_observer_scaling_changes_observed_phase(self):
        t, p = ellipse_trace(1.0, 0.8, n=2048)
        full = Observer("full")
        half_y = Observer("half_y", ((1.0, 0.0), (0.0, 0.5)))
        s_full = response_signature(trace_with_observer(t, p, full), full)
        s_half = response_signature(trace_with_observer(t, p, half_y), half_y)
        self.assertAlmostEqual(s_half["geometric_phase"], 0.5 * s_full["geometric_phase"], places=7)

    def test_time_must_increase(self):
        obs = Observer("identity")
        with self.assertRaises(ValueError):
            trace_with_observer((0.0, 1.0, 0.5), ((1, 0), (0, 1), (-1, 0)), obs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
