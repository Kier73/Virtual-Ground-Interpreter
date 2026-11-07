import csv
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

import build_11
from wav_tools import read_pcm_wav, estimate_rt60


class Build11DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.windows = build_11.load_excerpt(ROOT / "source_data" / "measurement_01_excerpt.csv")
        cls.features = {name: build_11.feature_window(rows) for name, rows in cls.windows.items()}

    def test_excerpt_rows_and_windows(self):
        self.assertEqual(sum(map(len, self.windows.values())), 411)
        self.assertEqual(len(self.windows), 8)

    def test_all_windows_time_monotone(self):
        for rows in self.windows.values():
            times = [r["time_s"] for r in rows]
            self.assertTrue(all(b > a for a, b in zip(times, times[1:])))

    def test_source_line_numbers_preserved(self):
        for rows in self.windows.values():
            self.assertTrue(all(r["source_line"] >= 2 for r in rows))

    def test_window_gaps_not_concatenated(self):
        names = list(self.windows)
        self.assertEqual(names[0], "pre_63_30_63_88")
        self.assertGreater(self.windows[names[1]][0]["time_s"] - self.windows[names[0]][-1]["time_s"], 0.3)

    def test_feature_values_finite(self):
        for feat in self.features.values():
            for value in feat.values():
                if isinstance(value, (int, float)):
                    self.assertTrue(math.isfinite(value))

    def test_sensor_near_limit_flags_only_post_windows(self):
        flagged = {n for n, f in self.features.items() if f["near_4g_fraction"] > 0}
        self.assertEqual(flagged, {"post_67_51_68_53", "post_68_82_69_20", "post_69_20_69_60"})

    def test_rdm_is_symmetric_and_zero_diagonal(self):
        for columns in build_11.FEATURE_VIEWS.values():
            names, matrix = build_11.make_rdm(self.features, columns)
            for i in range(len(names)):
                self.assertAlmostEqual(matrix[i][i], 0.0)
                for j in range(len(names)):
                    self.assertAlmostEqual(matrix[i][j], matrix[j][i])

    def test_unit_conversion_distance_invariant(self):
        base = {n: [f["std_x_g"], f["std_y_g"], f["std_z_g"]] for n, f in self.features.items()}
        scaled = {n: [x * build_11.G0 for x in vec] for n, vec in base.items()}
        a, b = build_11.pairwise_from_vectors(base), build_11.pairwise_from_vectors(scaled)
        err = max(abs(a[i][j] - b[i][j]) for i in range(len(a)) for j in range(len(a)))
        self.assertLess(err, 1e-12)

    def test_codon_aliases_match(self):
        self.assertEqual(build_11.codon_apply("ad", 1.25, 2.75), build_11.codon_apply("plus", 1.25, 2.75))
        self.assertEqual(build_11.codon_apply("mx", 1.25, 2.75), build_11.codon_apply("times", 1.25, 2.75))

    def test_division_zero_rejected(self):
        with self.assertRaises(ZeroDivisionError):
            build_11.codon_apply("dv", 1.0, 0.0)

    def test_observer_interval_constants(self):
        self.assertEqual(build_11.OBSERVER_INTERVAL, (66.0, 68.0))
        self.assertEqual(build_11.OBSERVER_POINT, 67.0)

    def test_descriptive_groups_have_two_windows_each(self):
        pre = [n for n, rows in self.windows.items() if rows[-1]["time_s"] < 66]
        event = [n for n, rows in self.windows.items() if rows[0]["time_s"] >= 66 and rows[-1]["time_s"] <= 68]
        post = [n for n, rows in self.windows.items() if rows[0]["time_s"] > 68]
        self.assertEqual((len(pre), len(event), len(post)), (2, 2, 2))


class WavToolTests(unittest.TestCase):
    def _write_wav(self, path, width, channels, rate, raw_bytes):
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(width)
            wf.setframerate(rate)
            wf.writeframes(raw_bytes)

    def test_read_16bit_mono(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.wav"
            values = [0, 16384, -16384, 32767, -32768]
            raw = b"".join(struct.pack("<h", x) for x in values)
            self._write_wav(path, 2, 1, 8000, raw)
            rate, frames, meta = read_pcm_wav(path)
            self.assertEqual(rate, 8000)
            self.assertEqual(meta["frames"], 5)
            self.assertAlmostEqual(frames[1][0], 0.5, places=4)
            self.assertAlmostEqual(frames[2][0], -0.5, places=4)

    def test_read_24bit_stereo(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x24.wav"
            vals = [0x400000, -0x400000]
            raw = b"".join((v & 0xFFFFFF).to_bytes(3, "little") for v in vals)
            self._write_wav(path, 3, 2, 48000, raw)
            rate, frames, meta = read_pcm_wav(path)
            self.assertEqual((rate, meta["channels"], meta["frames"]), (48000, 2, 1))
            self.assertAlmostEqual(frames[0][0], 0.5, places=6)
            self.assertAlmostEqual(frames[0][1], -0.5, places=6)

    def test_rt60_returns_none_for_silence(self):
        self.assertIsNone(estimate_rt60([[0.0], [0.0]], 48000))

    def test_rt60_positive_for_decay(self):
        rate = 8000
        n = 8000
        samples = [[math.exp(-i / 1200.0)] for i in range(n)]
        result = estimate_rt60(samples, rate)
        self.assertIsNotNone(result)
        self.assertGreater(result, 0.0)

    def test_rt60_requires_valid_sample_rate(self):
        self.assertIsNone(estimate_rt60([[1.0]], 0))


if __name__ == "__main__":
    unittest.main()
