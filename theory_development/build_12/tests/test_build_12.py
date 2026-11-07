from __future__ import annotations
import math, struct, tempfile, unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_12


def make_wav(path: Path, samples, fs=48000, bits=32, float_format=True):
    channels = 1
    if float_format:
        tag = 3
        payload = b"".join(struct.pack("<f", float(x)) for x in samples)
    elif bits == 16:
        tag = 1
        payload = b"".join(struct.pack("<h", max(-32768, min(32767, int(round(x * 32767))))) for x in samples)
    elif bits == 24:
        tag = 1
        out = bytearray()
        for x in samples:
            v = max(-(1 << 23), min((1 << 23)-1, int(round(x * ((1 << 23)-1)))))
            if v < 0: v += 1 << 24
            out.extend(v.to_bytes(3, "little"))
        payload = bytes(out)
    else:
        raise ValueError
    block = channels * (bits // 8)
    fmt = struct.pack("<HHIIHH", tag, channels, fs, fs * block, block, bits)
    def chunk(cid, data):
        return cid + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) & 1 else b"")
    body = b"WAVE" + chunk(b"fmt ", fmt) + chunk(b"data", payload)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


class TestWavReader(unittest.TestCase):
    def test_read_float32(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "float.wav"
            make_wav(p, [0.0, 0.5, -0.25, 1.0])
            fs, channels, meta = build_12.read_wav(p)
            self.assertEqual(fs, 48000)
            self.assertEqual(meta["encoding"], "ieee_float")
            self.assertAlmostEqual(channels[0][1], 0.5, places=6)

    def test_read_pcm16(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "pcm16.wav"
            make_wav(p, [0.0, 0.5, -0.5], bits=16, float_format=False)
            _, c, m = build_12.read_wav(p)
            self.assertEqual(m["bits_per_sample"], 16)
            self.assertAlmostEqual(c[0][1], 0.5, delta=1e-4)

    def test_read_pcm24(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "pcm24.wav"
            make_wav(p, [0.0, 0.25, -0.25], bits=24, float_format=False)
            _, c, m = build_12.read_wav(p)
            self.assertEqual(m["bits_per_sample"], 24)
            self.assertAlmostEqual(c[0][2], -0.25, delta=1e-6)

    def test_reject_non_wav(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.wav"; p.write_bytes(b"not wav")
            with self.assertRaises(ValueError): build_12.read_wav(p)


class TestResponseFeatures(unittest.TestCase):
    def test_decay_estimate_exponential(self):
        fs = 48000; tau = 0.20
        x = [math.exp(-(i/fs)/tau) for i in range(fs * 2)]
        result = build_12._decay_metrics(x, fs)
        expected = 60.0 / (8.685889638 / tau)
        self.assertTrue(math.isfinite(result["t20_s"]))
        self.assertAlmostEqual(result["t20_s"], expected, delta=0.025)

    def test_full_feature_bundle(self):
        fs=48000; tau=0.24
        x=[math.exp(-(i/fs)/tau) * (1.0 if i < 300 else 1.0 + 0.04*math.sin(i*0.09)) for i in range(fs)]
        f=build_12.analyze_channel(x, fs)
        for key in ("c50_db", "c80_db", "d50", "ts_s", "edt_s", "t20_s", "band_500_share"):
            self.assertIn(key, f)
            self.assertTrue(math.isfinite(f[key]), key)
        self.assertGreaterEqual(f["d50"], 0.0)
        self.assertLessEqual(f["d50"], 1.0)

    def test_short_signal_rejected(self):
        with self.assertRaises(ValueError): build_12.analyze_channel([0.0]*100, 48000)

    def test_silent_signal_rejected(self):
        with self.assertRaises(ValueError): build_12.analyze_channel([0.0]*5000, 48000)

    def test_too_low_sample_rate_rejected(self):
        with self.assertRaises(ValueError): build_12.analyze_channel([0.1]*5000, 4000)

    def test_gain_scaling_preserves_normalized_decay(self):
        fs=48000; x=[math.exp(-i/(fs*0.2)) for i in range(fs)]
        a=build_12.analyze_channel(x, fs)
        b=build_12.analyze_channel([3*v for v in x], fs)
        self.assertAlmostEqual(a["t20_s"], b["t20_s"], places=8)
        self.assertAlmostEqual(a["d50"], b["d50"], places=8)
        self.assertAlmostEqual(b["peak_abs"]/a["peak_abs"], 3.0, places=8)


class TestGeometry(unittest.TestCase):
    def setUp(self):
        self.rooms = {
            "A": {"edt_s": 0.3, "t20_s": 0.4, "c50_db": 5.0, "band_centroid_hz": 900.0, "peak_abs": 0.4, "rms": 0.01, "energy": 0.1, "crest_factor": 40.0, "decay_rmse_db": 1.0, "t20_band_median_s": 0.4},
            "B": {"edt_s": 0.7, "t20_s": 0.8, "c50_db": 0.0, "band_centroid_hz": 1200.0, "peak_abs": 0.2, "rms": 0.02, "energy": 0.2, "crest_factor": 10.0, "decay_rmse_db": 2.0, "t20_band_median_s": 0.8},
            "C": {"edt_s": 1.1, "t20_s": 1.2, "c50_db": -5.0, "band_centroid_hz": 1800.0, "peak_abs": 0.1, "rms": 0.03, "energy": 0.3, "crest_factor": 3.3, "decay_rmse_db": 3.0, "t20_band_median_s": 1.2},
        }

    def test_rdm_symmetric(self):
        names, rdm = build_12.make_rdm(self.rooms, ["edt_s", "t20_s"])
        self.assertEqual(names, ["A", "B", "C"])
        for i in range(3):
            self.assertAlmostEqual(rdm[i][i], 0.0)
            for j in range(3): self.assertAlmostEqual(rdm[i][j], rdm[j][i])

    def test_room_aggregation_median(self):
        rows=[{"room_id":"A", "edt_s":0.3, "rir_count":1}, {"room_id":"A", "edt_s":0.5, "rir_count":1}, {"room_id":"B", "edt_s":0.8, "rir_count":1}]
        agg=build_12.aggregate_rooms(rows)
        self.assertAlmostEqual(agg["A"]["edt_s"], 0.4)
        self.assertEqual(agg["A"]["rir_count"], 2)

    def test_spearman_rdm_identical(self):
        _, a=build_12.make_rdm(self.rooms, ["edt_s", "t20_s"])
        self.assertAlmostEqual(build_12.rdm_spearman(a, a), 1.0)

    def test_paired_cross_domain_rdm_requires_explicit_pairs(self):
        rows_a=[{"pair_id":k, "a":v, "b":v*2} for k,v in zip("ABCD", [0.1,0.3,0.7,1.1])]
        rows_b=[{"pair_id":k, "x":v*5, "y":v*3} for k,v in zip("ABCD", [0.1,0.3,0.7,1.1])]
        result=build_12.paired_cross_domain_rdm_correlation(rows_a, rows_b, ["a","b"], ["x","y"])
        self.assertAlmostEqual(result, 1.0, places=9)
        with self.assertRaises(ValueError):
            build_12.paired_cross_domain_rdm_correlation(rows_a, rows_b[:-1], ["a"], ["x"])

    def test_feature_views_are_independent(self):
        self.assertNotEqual(build_12.FEATURE_VIEWS["level"], build_12.FEATURE_VIEWS["decay"])
        self.assertNotIn("peak_abs", build_12.FEATURE_VIEWS["decay"])


class TestEndToEnd(unittest.TestCase):
    def test_analyze_tree_and_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"rir"; out=Path(td)/"out"
            fs=48000
            for room,tau in (("room_A",0.2),("room_B",0.3),("room_C",0.4)):
                d=root/room; d.mkdir(parents=True)
                x=[math.exp(-(i/fs)/tau) for i in range(fs//2)]
                make_wav(d/"rir_01.wav", x)
            report=build_12.build_outputs(root, out)
            self.assertEqual(report["analysis_status"], "analyzed")
            self.assertEqual(len(report["rooms"]), 3)
            self.assertTrue((out/"rir_file_features.csv").exists())
            self.assertTrue((out/"rdm_decay.csv").exists())

    def test_no_files_does_not_claim_empirical_analysis(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"empty"; root.mkdir()
            report=build_12.build_outputs(root, Path(td)/"out")
            self.assertEqual(report["analysis_status"], "no_usable_wavs")
            self.assertEqual(report["rooms"], [])

if __name__ == "__main__":
    unittest.main(verbosity=2)
