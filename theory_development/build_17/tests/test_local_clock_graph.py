from __future__ import annotations
import json
import math
import random
import tempfile
import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from local_clock_graph import (
    EventStream, affine_clock_transform, align_event_streams,
    analyze_stream_pair, build_event_graph, event_features,
    extract_event_stream_from_wav, graph_topology_signature,
)
from build_15 import run_taps_graph_analysis
from test_build_14 import write_pcm16, synth_voice


def latent_stream(seed=22, count=45):
    rng = random.Random(seed)
    times = [0.0]
    for _ in range(count - 1):
        times.append(times[-1] + rng.uniform(0.22, 0.91))
    marks = [0.2 + 0.8 * rng.random() for _ in times]
    return times, marks


class TestEventStream(unittest.TestCase):
    def test_rejects_non_monotone_times(self):
        with self.assertRaises(ValueError):
            EventStream("A", (0.0, 0.4, 0.3), (0.1, 0.2, 0.3)).validate()

    def test_rejects_nonfinite_mark(self):
        with self.assertRaises(ValueError):
            EventStream("A", (0.0,), (math.nan,)).validate()

    def test_rejects_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            EventStream("A", (0.0, 1.0), (0.2,)).validate()

    def test_empty_stream_is_valid(self):
        EventStream("A", (), ()).validate()
        result = align_event_streams(EventStream("A", (), ()), EventStream("B", (), ()))
        self.assertEqual(result["matched_count"], 0)


class TestIndependentClockInvariance(unittest.TestCase):
    def setUp(self):
        self.times, self.marks = latent_stream()

    def test_features_invariant_to_offset_and_positive_scale(self):
        a = EventStream("A", tuple(self.times), tuple(self.marks), self.times[-1] + 1)
        tb = affine_clock_transform(self.times, offset_s=19.0, scale=4.25)
        b = EventStream("B", tuple(tb), tuple(v * 11.0 + 3.0 for v in self.marks),
                        4.25 * (self.times[-1] + 1))
        fa, fb = event_features(a), event_features(b)
        for x, y in zip(fa, fb):
            self.assertAlmostEqual(x["mark_rank"], y["mark_rank"], places=12)
            self.assertAlmostEqual(x["interval_log_shape"], y["interval_log_shape"], places=12)

    def test_graph_topology_invariant_to_affine_clock(self):
        a = EventStream("A", tuple(self.times), tuple(self.marks))
        b = EventStream("B", tuple(affine_clock_transform(self.times, -7.0, 0.125)),
                        tuple(v * 5.0 for v in self.marks))
        sa, sb = graph_topology_signature(a), graph_topology_signature(b)
        self.assertEqual(sa["event_count"], sb["event_count"])
        self.assertEqual(sa["recurrence_edges"], sb["recurrence_edges"])
        for key in ("normalized_interval_cv", "normalized_interval_median",
                    "normalized_interval_q25", "normalized_interval_q75",
                    "recurrence_density"):
            self.assertAlmostEqual(sa[key], sb[key], places=10, msg=key)

    def test_alignment_does_not_depend_on_independent_clock_coordinates(self):
        times_b = [self.times[i] for i in range(len(self.times)) if i not in {7, 18, 31}]
        marks_b = [self.marks[i] * 7.0 + 2.0 for i in range(len(self.marks)) if i not in {7, 18, 31}]
        a = EventStream("A", tuple(self.times), tuple(self.marks))
        b = EventStream("B", tuple(affine_clock_transform(times_b, 21.0, 3.7)), tuple(marks_b))
        baseline = align_event_streams(a, EventStream("B", tuple(times_b), tuple(marks_b)))
        transformed = align_event_streams(a, b)
        self.assertEqual([(m["left_index"], m["right_index"]) for m in baseline["matches"]],
                         [(m["left_index"], m["right_index"]) for m in transformed["matches"]])

    def test_post_match_clock_fit_recovers_known_affine_relation(self):
        a = EventStream("A", tuple(self.times), tuple(self.marks))
        scale, offset = 2.75, 14.5
        b = EventStream("B", tuple(affine_clock_transform(self.times, offset, scale)),
                        tuple(self.marks))
        result = analyze_stream_pair(a, b)
        fit = result["post_match_clock_relation"]
        relation = fit["left_time_approximately_equals_offset_plus_scale_times_right_time"]
        self.assertAlmostEqual(relation["scale"], 1.0 / scale, places=10)
        self.assertAlmostEqual(relation["offset_s"], -offset / scale, places=10)
        self.assertLess(fit["median_absolute_residual_s"], 1e-9)

    def test_matcher_declares_no_shared_clock_requirement(self):
        a = EventStream("A", tuple(self.times), tuple(self.marks))
        b = EventStream("B", tuple(affine_clock_transform(self.times, 1000.0, 0.01)), tuple(self.marks))
        result = align_event_streams(a, b)
        self.assertIn("no timestamp synchronization", result["clock_assumption"])


class TestEventGraph(unittest.TestCase):
    def test_graph_contains_local_successor_and_cross_correspondence_edges(self):
        times, marks = latent_stream(count=18)
        a = EventStream("throat", tuple(times), tuple(marks))
        b = EventStream("acoustic", tuple(affine_clock_transform(times, 6.0, 2.0)), tuple(marks))
        result = analyze_stream_pair(a, b)
        graph = result["graph"]
        self.assertEqual(graph["cross_observer_clock_edges"], 0)
        self.assertEqual(graph["correspondence_edge_count"], len(result["alignment"]["matches"]))
        self.assertEqual(graph["successor_edge_count"], 2 * (len(times) - 1))
        self.assertTrue(all(e["type"] != "clock_difference" for e in graph["edges"]))

    def test_repeated_interval_motifs_generate_recurrence_edges(self):
        gaps = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0]
        times = [0.0]
        for gap in gaps: times.append(times[-1] + gap)
        stream = EventStream("A", tuple(times), tuple([0.5] * len(times)))
        self.assertGreater(graph_topology_signature(stream)["recurrence_edges"], 0)

    def test_graph_successor_edges_preserve_local_order(self):
        a = EventStream("A", (0.0, 0.4, 1.2, 2.0), (0.2, 0.8, 0.3, 0.7))
        b = EventStream("B", (5.0, 6.0, 7.0, 8.0), (0.2, 0.8, 0.3, 0.7))
        al = align_event_streams(a, b)
        graph = build_event_graph(a, b, al)
        left_succ = [e for e in graph["edges"] if e["type"] == "successor" and e["source"].startswith("L:")]
        self.assertEqual([(e["source"], e["target"]) for e in left_succ],
                         [("L:0", "L:1"), ("L:1", "L:2"), ("L:2", "L:3")])


class TestNoisyEventMatching(unittest.TestCase):
    def test_dropout_and_false_events_produce_partial_monotone_alignment(self):
        rng = random.Random(903)
        times, marks = latent_stream(seed=903, count=50)
        left = EventStream("A", tuple(times), tuple(marks))
        retained = []
        for i, (t, mark) in enumerate(zip(times, marks)):
            if rng.random() > 0.10:
                retained.append((t, mark, i))
        right = [(12.0 + 3.0*t + rng.gauss(0, 0.004),
                  4.0 + 2.5*mark + rng.gauss(0, 0.008), original)
                 for t, mark, original in retained]
        for _ in range(5):
            t = rng.uniform(times[0], times[-1])
            right.append((12.0 + 3.0*t, 4.0 + 2.5*rng.random(), None))
        right.sort(key=lambda x: x[0])
        right_stream = EventStream("B", tuple(x[0] for x in right), tuple(x[1] for x in right))
        result = align_event_streams(left, right_stream)
        pairs = {(m["left_index"], m["right_index"]) for m in result["matches"]}
        truth = {(original, j) for j, (_, _, original) in enumerate(right) if original is not None}
        precision = len(pairs & truth) / max(1, len(pairs))
        recall = len(pairs & truth) / max(1, len(truth))
        self.assertGreater(precision, 0.80)
        self.assertGreater(recall, 0.80)
        ordered = [(m["left_index"], m["right_index"]) for m in result["matches"]]
        self.assertTrue(all(a[0] < b[0] and a[1] < b[1] for a, b in zip(ordered, ordered[1:])))

    def test_gap_penalty_must_be_positive(self):
        a = EventStream("A", (0.0, 1.0), (0.2, 0.8))
        with self.assertRaises(ValueError): align_event_streams(a, a, gap_penalty=0)

    def test_dp_size_guard(self):
        n = 2001
        a = EventStream("A", tuple(float(i) for i in range(n)), tuple(float(i % 9) for i in range(n)))
        with self.assertRaises(ValueError): align_event_streams(a, a)


class TestWavIntegration(unittest.TestCase):
    def test_extracts_event_stream_from_wav(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "speech.wav"
            write_pcm16(p, synth_voice(fs=16000, duration=1.2, f0=150, seed=33))
            stream = extract_event_stream_from_wav(str(p), "test-observer")
            self.assertEqual(stream.observer, "test-observer")
            self.assertEqual(len(stream.local_times_s), len(stream.marks))
            self.assertGreater(stream.duration_s, 1.1)

    def test_taps_runner_outputs_aggregate_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "raw" / "test"
            for u in range(8):
                d = root / "speaker_private" / f"utt_{u:02d}"
                fs = 16000
                throat = synth_voice(fs=fs, duration=1.2, f0=125+u*2, seed=u)
                acoustic = synth_voice(fs=fs, duration=1.2, f0=125+u*2, delay=0.001, high=0.02, seed=u)
                write_pcm16(d / "throat_microphone.wav", throat, fs)
                write_pcm16(d / "acoustic_microphone.wav", acoustic, fs)
                (d / "features.json").write_text(json.dumps({
                    "speaker_id": "speaker_private", "sentence_id": f"utt_{u:02d}",
                    "text": "PRIVATE TRANSCRIPT", "gender": "private",
                    "throat_microphone": {"sampling_rate": fs},
                    "acoustic_microphone": {"sampling_rate": fs},
                }), encoding="utf-8")
            out = Path(td) / "out"
            report = run_taps_graph_analysis(root, out, split="test")
            self.assertEqual(report["pairs_discovered"], 8)
            self.assertEqual(report["pairs_analyzed"], 8)
            serialized = (out / "build_15_report.json").read_text(encoding="utf-8")
            self.assertNotIn("speaker_private", serialized)
            self.assertNotIn("PRIVATE TRANSCRIPT", serialized)
            self.assertNotIn('"gender"', serialized)
            self.assertNotIn('"utterance_ids_exported": true', serialized)
            self.assertFalse(report["privacy"]["raw_audio_copied"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
