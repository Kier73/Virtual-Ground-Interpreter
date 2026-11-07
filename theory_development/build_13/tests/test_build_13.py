from __future__ import annotations
import json, math, random, struct, tempfile, unittest, zipfile, importlib.util
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_13


def write_pcm16(path: Path, samples, fs=16000):
    vals = [max(-32768, min(32767, int(round(float(x) * 32767)))) for x in samples]
    payload = struct.pack("<" + "h" * len(vals), *vals)
    fmt = struct.pack("<HHIIHH", 1, 1, fs, fs * 2, 2, 16)
    def chunk(tag, data):
        return tag + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) & 1 else b"")
    body = b"WAVE" + chunk(b"fmt ", fmt) + chunk(b"data", payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def synth_voice(fs=16000, duration=1.2, f0=140.0, delay=0.0, high=0.0, seed=1):
    rng = random.Random(seed)
    n = int(fs * duration)
    shift = int(round(delay * fs))
    x = []
    for i in range(n):
        t = i / fs
        env = 0.45 + 0.25 * math.sin(2 * math.pi * 2.1 * t) ** 2
        s = (math.sin(2*math.pi*f0*t) + 0.45*math.sin(2*math.pi*2*f0*t)
             + 0.2*math.sin(2*math.pi*3*f0*t)) * env
        s += high * math.sin(2*math.pi*4800*t) * env
        x.append(0.22 * s + 0.001 * (rng.random() - 0.5))
    if shift > 0:
        x = [0.0] * shift + x[:-shift]
    return x


class TestWavReader(unittest.TestCase):
    def test_pcm16_mono(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.wav"
            write_pcm16(p, [0, 0.5, -0.5, 0.25])
            w = build_13.read_wav(p)
            self.assertEqual(w.sample_rate, 16000)
            self.assertEqual(w.bits_per_sample, 16)
            self.assertAlmostEqual(w.samples[1], 0.5, delta=1e-4)

    def test_pcm24(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.wav"
            vals = [0, int(0.25 * ((1 << 23)-1)), int(-0.25 * ((1 << 23)-1))]
            payload = b"".join((v if v >= 0 else v + (1 << 24)).to_bytes(3, "little") for v in vals)
            fmt = struct.pack("<HHIIHH", 1, 1, 8000, 24000, 3, 24)
            def chunk(tag, data):
                return tag + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) & 1 else b"")
            body = b"WAVE" + chunk(b"fmt ", fmt) + chunk(b"data", payload)
            p.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
            w = build_13.read_wav(p)
            self.assertEqual(w.bits_per_sample, 24)
            self.assertAlmostEqual(w.samples[1], 0.25, delta=1e-6)
            self.assertAlmostEqual(w.samples[2], -0.25, delta=1e-6)

    def test_reject_non_wav(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.wav"; p.write_bytes(b"not wave")
            with self.assertRaises(ValueError):
                build_13.read_wav(p)


class TestSignalFeatures(unittest.TestCase):
    def test_percentile_integer_position(self):
        self.assertEqual(build_13._percentile([1, 2, 3], 0.5), 2)
        self.assertEqual(build_13._percentile([1, 2, 3, 4], 0.5), 2.5)

    def test_fft_known_bin(self):
        n = 256; k = 7
        a = [complex(math.sin(2*math.pi*k*i/n), 0) for i in range(n)]
        build_13.fft_inplace(a)
        self.assertAlmostEqual(abs(a[k]), n/2, places=5)
        self.assertAlmostEqual(abs(a[n-k]), n/2, places=5)

    def test_summarize_channel(self):
        fs = 16000
        x = synth_voice(fs=fs, f0=175, high=0.05)
        w = build_13.WavData(fs, x, 1, "pcm", 16, len(x))
        m, env = build_13.summarize_channel(w)
        for key in ("rms", "log_rms", "centroid_common_hz", "band_80_250",
                    "f0_median_hz", "periodicity", "high_4000_7800_share"):
            self.assertIn(key, m)
            self.assertTrue(math.isfinite(m[key]))
        self.assertGreater(len(env), 10)
        self.assertGreater(m["f0_median_hz"], 100)
        self.assertLess(m["f0_median_hz"], 250)

    def test_raw_alignment_known_delay(self):
        fs = 8000
        a = synth_voice(fs=fs, duration=1.0, f0=165, seed=22)
        delay_s = 0.002
        b = synth_voice(fs=fs, duration=1.0, f0=165, delay=delay_s, seed=22)
        lag = build_13.estimate_raw_waveform_lag(a, fs, b, fs, max_lag_ms=5)
        self.assertAlmostEqual(lag["lag_ms"], delay_s*1000, delta=0.5)
        self.assertGreater(lag["correlation"], lag["zero_lag_correlation"])

    def test_envelope_alignment_known_delay(self):
        a = [0.0, 0.1, 0.8, 0.2, 0.0, 0.4, 0.9, 0.1, 0.0, 0.5, 0.2, 0.0]
        b = [0.0, 0.0] + a[:-2]
        lag = build_13.estimate_envelope_lag(a, b, frame_ms=10, max_lag_ms=40)
        self.assertEqual(lag["lag_ms"], 20)


class TestPairDiscoveryAndGeometry(unittest.TestCase):
    def _make_dataset(self, root: Path, speakers=1, utterances=8):
        for s in range(speakers):
            for u in range(utterances):
                d = root / "test" / f"speaker_{s:02d}" / f"utt_{u:03d}"
                fs = 16000
                throat = synth_voice(fs=fs, duration=0.7, f0=110+u*7, high=0.0, seed=u)
                acoustic = synth_voice(fs=fs, duration=0.7, f0=110+u*7, high=0.03, seed=u)
                write_pcm16(d / "throat_microphone.wav", throat, fs)
                write_pcm16(d / "acoustic_microphone.wav", acoustic, fs)
                (d / "features.json").write_text(json.dumps({
                    "speaker_id": f"speaker_{s:02d}", "sentence_id": f"utt_{u:03d}",
                    "text": "PRIVATE TRANSCRIPT SHOULD NOT BE EXPORTED",
                    "gender": "not used",
                    "throat_microphone": {"sampling_rate": fs, "num_samples": len(throat)},
                    "acoustic_microphone": {"sampling_rate": fs, "num_samples": len(acoustic)},
                }), encoding="utf-8")

    def test_discover_only_complete_pairs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self._make_dataset(root, speakers=1, utterances=8)
            orphan = root / "test" / "speaker_00" / "orphan"
            write_pcm16(orphan / "throat_microphone.wav", [0.1]*1000)
            pairs = build_13.discover_pairs(root / "test", split="test")
            self.assertEqual(len(pairs), 8)
            self.assertTrue(all("text" not in p for p in pairs))

    def test_pair_analysis_has_both_channels(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self._make_dataset(root, speakers=1, utterances=8)
            pair = build_13.discover_pairs(root / "test")[0]
            result = build_13.analyze_pair(pair)
            self.assertIn("throat", result)
            self.assertIn("acoustic", result)
            self.assertIn("raw_alignment", result)
            self.assertNotIn("speaker_id", result)

    def test_run_analysis_does_not_write_transcripts_or_speaker_ids(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "raw"; out = Path(td) / "out"
            self._make_dataset(root, speakers=2, utterances=8)
            report = build_13.run_analysis(root / "test", out, split="test",
                                           max_speakers=2, max_utterances_per_speaker=8,
                                           permutations=5, seed=7, provenance="synthetic_fixture")
            self.assertEqual(report["analysis_status"], "synthetic_smoke_test_complete")
            self.assertEqual(report["pairs_analyzed"], 16)
            serialized = (out / "build_13_report.json").read_text(encoding="utf-8")
            self.assertNotIn("speaker_00", serialized)
            self.assertNotIn("PRIVATE TRANSCRIPT", serialized)
            self.assertNotIn('"gender"', serialized)
            self.assertTrue((out / "rdm_view_summary.csv").exists())

    def test_sample_rate_metadata_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self._make_dataset(root, speakers=1, utterances=8)
            pair = build_13.discover_pairs(root / "test")[0]
            pair["throat_meta"] = {"sampling_rate": 8000}
            with self.assertRaises(ValueError):
                build_13.analyze_pair(pair)

    def test_feature_views_exclude_acoustic_only_high_band(self):
        for view, features in build_13.FEATURE_VIEWS.items():
            self.assertNotIn("high_4000_7800_share", features)

    def test_upsampled_throat_does_not_claim_above_nyquist_energy(self):
        fs = 16000
        samples = synth_voice(fs=fs, f0=150, high=0.2, seed=88)
        wav = build_13.WavData(fs, samples, 1, "pcm", 16, len(samples))
        throat_meta, _ = build_13.summarize_channel(wav, original_nyquist_hz=4000.0)
        acoustic_meta, _ = build_13.summarize_channel(wav, original_nyquist_hz=7800.0)
        self.assertFalse(throat_meta["high_band_valid"])
        self.assertEqual(throat_meta["high_4000_7800_share"], 0.0)
        self.assertTrue(acoustic_meta["high_band_valid"])
        self.assertGreater(acoustic_meta["high_4000_7800_share"], 0.0)


class TestSafeDatasetRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = ROOT / "scripts" / "fetch_taps.py"
        spec = importlib.util.spec_from_file_location("fetch_taps_build13_test", script)
        cls.fetch_module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(cls.fetch_module)

    def test_safe_extract_accepts_regular_archive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "ok.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("speaker/utterance/channel.wav", b"fixture")
            out = root / "extracted"
            count = self.fetch_module.safe_extract(archive, out)
            self.assertEqual(count, 1)
            self.assertEqual((out / "speaker/utterance/channel.wav").read_bytes(), b"fixture")

    def test_safe_extract_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", b"not allowed")
            with self.assertRaises(ValueError):
                self.fetch_module.safe_extract(archive, root / "out")
            self.assertFalse((root / "escape.txt").exists())

    def test_safe_extract_rejects_absolute_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("/tmp/escape.txt", b"not allowed")
            with self.assertRaises(ValueError):
                self.fetch_module.safe_extract(archive, root / "out")

    def test_download_verifies_md5_and_cleans_partial_on_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.bin"
            source.write_bytes(b"paired-sensor-fixture")
            import hashlib
            expected = hashlib.md5(source.read_bytes()).hexdigest()
            dest = root / "download.bin"
            result = self.fetch_module.download(source.as_uri(), dest, expected)
            self.assertTrue(result["verified"])
            self.assertEqual(dest.read_bytes(), source.read_bytes())
            bad_dest = root / "bad.bin"
            with self.assertRaises(ValueError):
                self.fetch_module.download(source.as_uri(), bad_dest, "0" * 32)
            self.assertFalse(bad_dest.exists())
            self.assertFalse((root / "bad.bin.part").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
