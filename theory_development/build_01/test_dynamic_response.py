import math
import unittest

from dynamic_response import AR2Seed, analytic_transfer, simulate_gain, spectral_response
from vl_response_geometry import Observer, s3_distance


class DynamicResponseTests(unittest.TestCase):
    def test_poles_encode_radius_and_frequency(self):
        seed = AR2Seed(0.87, 0.8)
        p1, p2 = seed.poles()
        self.assertAlmostEqual(abs(p1), 0.87, places=12)
        self.assertAlmostEqual(abs(p2), 0.87, places=12)
        self.assertAlmostEqual(math.atan2(p1.imag, p1.real), 0.8, places=12)
        self.assertAlmostEqual(math.atan2(p2.imag, p2.real), -0.8, places=12)

    def test_stability_constraints_are_enforced(self):
        with self.assertRaises(ValueError):
            AR2Seed(1.0, 0.8)
        with self.assertRaises(ValueError):
            AR2Seed(0.8, 0.0)

    def test_simulated_gain_matches_analytic_transfer(self):
        seed = AR2Seed(0.9, 0.75)
        measured, _ = simulate_gain(seed, seed.omega0, n_samples=16000)
        theoretical = abs(analytic_transfer(seed, seed.omega0))
        self.assertLess(abs(measured - theoretical) / theoretical, 0.01)

    def test_peak_tracks_natural_frequency(self):
        seed = AR2Seed(0.93, 1.2)
        response = spectral_response(seed, n_freq=257)
        self.assertLess(abs(response.peak_frequency - seed.omega0), 0.04)

    def test_damping_changes_peak_strength(self):
        low_damped = spectral_response(AR2Seed(0.92, 1.0))
        high_damped = spectral_response(AR2Seed(0.60, 1.0))
        self.assertGreater(low_damped.peak_gain, high_damped.peak_gain)

    def test_observer_weighting_changes_spectral_geometry(self):
        seed_a = AR2Seed(0.92, 0.4)
        seed_b = AR2Seed(0.92, 2.2)
        balanced = Observer.identity()
        oscillatory = Observer.diagonal("oscillatory", (0.5, 0.5, 1.0, 3.0))
        d1 = s3_distance(spectral_response(seed_a, balanced).q_resp, spectral_response(seed_b, balanced).q_resp)
        d2 = s3_distance(spectral_response(seed_a, oscillatory).q_resp, spectral_response(seed_b, oscillatory).q_resp)
        self.assertNotAlmostEqual(d1, d2, places=4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
