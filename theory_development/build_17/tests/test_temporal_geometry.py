from __future__ import annotations
import unittest
import temporal_geometry
import build_14


class TestTemporalEmission(unittest.TestCase):
    def setUp(self):
        self.times = [0.7, 1.4, 2.1, 3.5, 4.2, 6.3, 7.0, 9.1]
        self.marks = [0.5, 0.9, 0.6, 0.8, 1.0, 0.7, 0.4, 0.9]

    def test_translation_does_not_change_signature(self):
        base = temporal_geometry.event_time_signature(self.times, self.marks, duration_s=10.0)
        shifted = temporal_geometry.event_time_signature(
            [t + 100.0 for t in self.times], self.marks, duration_s=10.0)
        for key in base:
            self.assertAlmostEqual(base[key], shifted[key], places=12, msg=key)

    def test_uniform_clock_scaling_preserves_shape_but_changes_rate(self):
        base = temporal_geometry.event_time_signature(self.times, self.marks, duration_s=10.0)
        c = 3.5
        scaled = temporal_geometry.event_time_signature(
            [c*t for t in self.times], self.marks, duration_s=10.0*c)
        for key in ("event_interval_cv", "event_interval_entropy",
                    "event_interval_q10_norm", "event_interval_q25_norm",
                    "event_interval_q50_norm", "event_interval_q75_norm",
                    "event_interval_q90_norm", "event_mark_cv_norm"):
            self.assertAlmostEqual(base[key], scaled[key], places=12, msg=key)
        self.assertAlmostEqual(scaled["event_rate_hz"], base["event_rate_hz"] / c, places=12)
        self.assertAlmostEqual(scaled["event_interval_median_s"],
                               base["event_interval_median_s"] * c, places=12)

    def test_affine_probe_passes(self):
        self.assertEqual(temporal_geometry.affine_invariance_probe(self.times, self.marks)["status"], "passed")

    def test_detector_clock_scale_with_scaled_observer_resolution(self):
        env = [0.05, 0.1, 0.8, 0.1, 0.05, 0.7, 0.05, 0.9, 0.05,
               0.1, 0.75, 0.05, 0.1, 0.85, 0.05, 0.1, 0.7, 0.05]
        base = temporal_geometry.summarize_envelope(env, frame_ms=20.0,
                                                    duration_s=len(env)*0.02,
                                                    min_gap_ms=80.0)
        c = 3.0
        scaled = temporal_geometry.summarize_envelope(env, frame_ms=20.0*c,
                                                      duration_s=len(env)*0.02*c,
                                                      min_gap_ms=80.0*c)
        for key in ("event_interval_cv", "event_interval_entropy",
                    "event_interval_q10_norm", "event_interval_q25_norm",
                    "event_interval_q50_norm", "event_interval_q75_norm",
                    "event_interval_q90_norm", "event_mark_cv_norm"):
            self.assertAlmostEqual(base[key], scaled[key], places=12, msg=key)
        self.assertAlmostEqual(scaled["event_rate_hz"], base["event_rate_hz"] / c, places=12)

    def test_event_marks_gain_normalized(self):
        a = temporal_geometry.event_time_signature(self.times, self.marks, duration_s=10.0)
        b = temporal_geometry.event_time_signature(self.times, [v * 37.0 for v in self.marks], duration_s=10.0)
        self.assertAlmostEqual(a["event_mark_cv_norm"], b["event_mark_cv_norm"], places=12)

    def test_median_normalized_interval_is_one_by_definition(self):
        result = temporal_geometry.event_time_signature(self.times, self.marks, duration_s=10.0)
        self.assertAlmostEqual(result["event_interval_q50_norm"], 1.0, places=10)

    def test_feature_schema_has_consistent_columns(self):
        import csv
        from pathlib import Path
        schema = Path(__file__).resolve().parents[1] / "feature_schema.csv"
        with schema.open(encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == len(rows[0]) for row in rows))

    def test_event_detector_respects_minimum_gap(self):
        env = [0.05, 0.1, 0.8, 0.1, 0.05, 0.7, 0.05, 0.9,
               0.05, 0.1, 0.75, 0.05, 0.1, 0.85, 0.05, 0.1]
        times, marks = temporal_geometry.detect_envelope_events(env, frame_ms=20.0, min_gap_ms=80.0)
        self.assertEqual(len(times), len(marks))
        self.assertTrue(all((b-a) >= 0.08 for a, b in zip(times, times[1:])))

    def test_temporal_views_are_separated(self):
        self.assertNotIn("event_interval_q50_norm", build_14.FEATURE_VIEWS["temporal_emission"])
        self.assertIn("event_rate_hz", build_14.FEATURE_VIEWS["temporal_rate"])
        self.assertNotIn("event_rate_hz", build_14.FEATURE_VIEWS["temporal_emission"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
