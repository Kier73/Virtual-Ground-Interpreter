from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "build27_workspace"))
from stream_ground import (
    Checkpoint, ContinuousTrace, ExecutablePartialGround, StreamGroundError,
    _solve_exact, build_effect_equations, compile_partial_ground,
    discover_and_compile, mine_motifs, permutation_filter_motifs,
    segment_stream, verify_ground_fingerprint,
)
from run_build28 import OPS, generate_trace


class ContinuousStreamBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train_pairs = [generate_trace(f"train_{i:02d}", 8000+i) for i in range(12)]
        cls.test_pairs = [generate_trace(f"test_{i:02d}", 9000+i) for i in range(5)]
        cls.train = [x[0] for x in cls.train_pairs]
        cls.test = [x[0] for x in cls.test_pairs]
        cls.learned = discover_and_compile(cls.train, min_len=2, max_len=4,
            min_occurrences=5, min_trace_support=3, top_k=5,
            ambiguity_margin=0.40, permutation_trials=31, permutation_seed=28028)

    def test_learner_receives_continuous_tokens_not_operation_boundaries(self):
        trace, truth, _ = self.train_pairs[0]
        truth_boundaries = {end for _, end, _ in truth}
        nonaligned = [c.offset for c in trace.checkpoints if c.offset not in truth_boundaries]
        self.assertGreater(len(nonaligned), 0)
        self.assertEqual(trace.checkpoints[0].offset, 0)
        self.assertEqual(trace.checkpoints[-1].offset, len(trace.tokens))

    def test_discovers_four_recurrent_opaque_motifs(self):
        expected = {tuple(x[0]) for x in OPS.values()}
        actual = {m.signature for m in self.learned["motifs"]}
        self.assertEqual(actual, expected)

    def test_boundaries_recovered_on_training_and_heldout_streams(self):
        all_pairs = self.train_pairs + self.test_pairs
        for trace, truth, _ in all_pairs:
            seg = (self.learned["segmentations"].get(trace.trace_id)
                   or segment_stream(trace, self.learned["motifs"], top_k=5, ambiguity_margin=0.40))
            self.assertEqual(seg.status, "resolved", trace.trace_id)
            predicted = {(s.start, s.end, s.signature) for s in seg.best.segments}
            self.assertEqual(predicted, set(truth), trace.trace_id)

    def test_nested_submotifs_are_audited_not_double_counted(self):
        nested = self.learned["nested_submotifs"]
        self.assertGreaterEqual(len(nested), 4)
        active = {m.signature for m in self.learned["motifs"]}
        self.assertNotIn(("pulse", "edge"), active)
        self.assertNotIn(("edge", "tail"), active)

    def test_ambiguous_prefix_segmentation_is_preserved(self):
        traces = []
        for i in range(5):
            traces.append(ContinuousTrace(f"ab_{i}", ("a", "b", f"n{i}"),
                (Checkpoint(0,(0,)), Checkpoint(3,(1,)))))
        for i in range(5):
            traces.append(ContinuousTrace(f"abc_{i}", ("a", "b", "c", f"m{i}"),
                (Checkpoint(0,(0,)), Checkpoint(4,(2,)))))
        motifs, _ = mine_motifs(traces, min_len=2, max_len=3,
                                min_occurrences=4, min_trace_support=3)
        target = ContinuousTrace("target", ("a", "b", "c"),
                                 (Checkpoint(0,(0,)), Checkpoint(3,(2,))))
        result = segment_stream(target, motifs, top_k=5, ambiguity_margin=0.50)
        self.assertEqual(result.status, "ambiguous")
        self.assertGreaterEqual(len(result.alternatives), 2)

    def test_inferred_checkpoint_effects_are_exact_and_unique(self):
        fit = self.learned["effect_fit"]
        self.assertEqual(fit["status"], "effects_uniquely_identified")
        by_sig = {tuple(op["signature"]): op["effect"] for op in self.learned["ground"]["operations"]}
        for name, (signature, effect) in OPS.items():
            self.assertEqual(by_sig[signature], list(effect), name)

    def test_checkpoint_equations_use_sparse_unaligned_observations(self):
        fit = self.learned["effect_fit"]
        self.assertGreater(fit["equations"], 20)
        self.assertTrue(all(x["status"] == "unique" for x in fit["rank_by_dimension"]))

    def test_heldout_checkpoint_effects_predict_exactly(self):
        from stream_ground import predict_checkpoint_deltas
        test_seg = {tr.trace_id: segment_stream(tr, self.learned["motifs"], top_k=5,
                                                ambiguity_margin=0.40) for tr in self.test}
        pred = predict_checkpoint_deltas(self.test, test_seg, self.learned["ground"], self.learned["motifs"])
        self.assertEqual(pred["correct"], pred["total"])
        self.assertGreater(pred["total"], 0)

    def test_recurrent_zero_effect_decoy_is_not_promoted_to_operation(self):
        by_sig = {tuple(op["signature"]): op for op in self.learned["ground"]["operations"]}
        decoy = by_sig[("hum", "click")]
        self.assertEqual(decoy["effect"], [0, 0])
        self.assertEqual(decoy["status"], "recurrent_zero_effect_motif")

    def test_order_permutation_rejects_accidental_motifs(self):
        import random
        shuffled = []
        for i, trace in enumerate(self.train):
            toks = list(trace.tokens)
            random.Random(3000+i).shuffle(toks)
            shuffled.append(ContinuousTrace(f"shuffle_{i}", tuple(toks), trace.checkpoints))
        raw, _ = mine_motifs(shuffled, min_len=2, max_len=4,
                             min_occurrences=5, min_trace_support=3)
        filtered, audit = permutation_filter_motifs(shuffled, raw, trials=31, seed=38028)
        self.assertGreater(len(raw), 0)
        self.assertEqual(len(filtered), 0)
        self.assertTrue(all(not x["survives_order_null"] for x in audit))

    def test_real_motifs_survive_familywise_permutation_screen(self):
        audit = self.learned["permutation_audit"]
        self.assertEqual(len(audit), 4)
        self.assertTrue(all(x["survives_order_null"] for x in audit))
        self.assertTrue(all(x["observed_occurrences"] > x["familywise_null_max_across_candidates"] for x in audit))

    def test_unknown_background_sequence_is_not_compiled(self):
        model = ExecutablePartialGround(self.learned["ground"])
        self.assertEqual(model.apply([10, 10], ["ambient_unseen", "token"])['status'], "unknown_operation")

    def test_executable_ground_roundtrip_and_fingerprint(self):
        spec = self.learned["ground"]
        self.assertTrue(verify_ground_fingerprint(spec))
        model = ExecutablePartialGround.from_json(json.dumps(spec, sort_keys=True))
        result = model.apply([10, 10], ["pulse", "edge", "tail"])
        self.assertEqual(result["next_state"], [11, 10])
        self.assertEqual(result["status"], "inductive_candidate")

    def test_zero_effect_motif_does_not_change_state(self):
        model = ExecutablePartialGround(self.learned["ground"])
        result = model.apply([8, 9], ["hum", "click"])
        self.assertEqual(result["next_state"], [8, 9])
        self.assertEqual(result["status"], "recurrent_zero_effect_motif")


    def test_inserted_token_does_not_silently_match_exact_motif(self):
        trace = ContinuousTrace("inserted", ("pulse", "inserted", "edge", "tail"),
                                (Checkpoint(0,(0,0)), Checkpoint(4,(1,0))))
        result = segment_stream(trace, self.learned["motifs"], top_k=5, ambiguity_margin=0.40)
        self.assertFalse(any(tuple(seg.signature) == ("pulse", "edge", "tail")
                             for alt in result.alternatives for seg in alt.segments))

    def test_ambiguous_segmentation_is_not_used_for_effect_learning(self):
        traces = []
        for i in range(5):
            traces.append(ContinuousTrace(f"ab_{i}", ("a", "b", f"n{i}"),
                (Checkpoint(0,(0,)), Checkpoint(3,(1,)))))
        for i in range(5):
            traces.append(ContinuousTrace(f"abc_{i}", ("a", "b", "c", f"m{i}"),
                (Checkpoint(0,(0,)), Checkpoint(4,(2,)))))
        motifs, _ = mine_motifs(traces, min_len=2, max_len=3,
                                min_occurrences=4, min_trace_support=3)
        target = ContinuousTrace("target", ("a", "b", "c"),
                                 (Checkpoint(0,(0,)), Checkpoint(3,(2,))))
        result = segment_stream(target, motifs, top_k=5, ambiguity_margin=0.50)
        effects = build_effect_equations([target], {"target": result}, motifs)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(effects["status"], "no_attributable_checkpoint_intervals")

    def test_ground_fingerprint_rejects_tampering(self):
        spec = dict(self.learned["ground"])
        spec["operations"] = [dict(x) for x in spec["operations"]]
        spec["operations"][0]["effect"] = [999, 999]
        self.assertFalse(verify_ground_fingerprint(spec))
        with self.assertRaises(StreamGroundError):
            ExecutablePartialGround(spec)

    def test_underdetermined_effects_remain_unknown(self):
        result = _solve_exact([[1, 1], [2, 2]], [3, 6], 2)
        self.assertEqual(result["status"], "underdetermined")
        self.assertIsNone(result["solution"])

    def test_inconsistent_checkpoint_equations_are_not_forced(self):
        result = _solve_exact([[1], [1]], [1, 2], 1)
        self.assertEqual(result["status"], "inconsistent")

    def test_checkpoint_validation_rejects_unsorted_offsets(self):
        bad = ContinuousTrace("bad", ("x", "y"),
            (Checkpoint(0,(0,)), Checkpoint(2,(1,)), Checkpoint(1,(1,))))
        with self.assertRaises(StreamGroundError):
            mine_motifs([bad])

    def test_recurrent_motif_counts_and_order_are_deterministic(self):
        again = discover_and_compile(self.train, min_len=2, max_len=4,
            min_occurrences=5, min_trace_support=3, top_k=5,
            ambiguity_margin=0.40, permutation_trials=31, permutation_seed=28028)
        self.assertEqual([m.as_dict() for m in again["motifs"]],
                         [m.as_dict() for m in self.learned["motifs"]])
        self.assertEqual(again["ground"]["fingerprint"], self.learned["ground"]["fingerprint"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
