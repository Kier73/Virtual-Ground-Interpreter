from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ground_diagnosis import (
    TransitionSample, HistoryTransition, ConflictRecord,
    discover_operation_candidates, compile_ground, PartialGenerativeGround,
    diagnose_history_collision, isolated_spikes, diagnose_sensor_shift,
    detect_regime_change, DiagnosticEvidence, diagnose_competing_explanations,
    build_report, SelfConstructingGroundInterpreter, choose_discriminating_probe,
)


class OperationDiscoveryTests(unittest.TestCase):
    def samples(self):
        out = []
        step = 0
        for x in range(7):
            out.append(TransitionSample(step, (x,), ("evt_a", "evt_b"), (x + 1,))); step += 1
            out.append(TransitionSample(step, (x,), ("evt_c",), (x + 3,))); step += 1
        return out

    def test_discovers_opaque_operation_signatures_without_action_catalogue(self):
        candidates = discover_operation_candidates(self.samples())
        self.assertEqual(len(candidates), 2)
        self.assertEqual({c.constant_delta for c in candidates}, {(1,), (3,)})

    def test_reversed_event_order_is_a_distinct_candidate(self):
        s = [TransitionSample(i, (i,), ("a", "b"), (i+1,)) for i in range(3)]
        s += [TransitionSample(i+3, (i,), ("b", "a"), (i+4,)) for i in range(3)]
        candidates = discover_operation_candidates(s)
        self.assertEqual({c.event_signature for c in candidates}, {("a", "b"), ("b", "a")})

    def test_one_off_event_sequence_is_not_promoted_to_operation(self):
        s = self.samples() + [TransitionSample(99, (0,), ("one_off",), (9,))]
        candidates = discover_operation_candidates(s)
        self.assertNotIn(("one_off",), {c.event_signature for c in candidates})

    def test_contextual_effect_falls_back_to_table_not_false_constant_law(self):
        s = [TransitionSample(0, (0,), ("x",), (1,)),
             TransitionSample(1, (1,), ("x",), (3,)),
             TransitionSample(2, (0,), ("x",), (1,)),
             TransitionSample(3, (1,), ("x",), (3,))]
        c = discover_operation_candidates(s)[0]
        self.assertEqual(c.effect_mode, "state_conditioned_table")
        # Here observed deltas are +1 and +2, so a contextual table should be used.
        self.assertIsNone(c.constant_delta)

    def test_conflicting_same_prestate_effect_is_ambiguous(self):
        s = [TransitionSample(0, (0,), ("x",), (1,)),
             TransitionSample(1, (0,), ("x",), (2,)),
             TransitionSample(2, (0,), ("x",), (1,))]
        c = discover_operation_candidates(s)[0]
        self.assertEqual(c.status, "ambiguous_effect")
        self.assertIn("[0]", c.ambiguous_pre_states)

    def test_partial_compiler_keeps_unknown_operation_unknown(self):
        samples = self.samples()
        spec = compile_ground(samples, discover_operation_candidates(samples))
        model = PartialGenerativeGround(spec)
        self.assertEqual(model.predict((0,), ("evt_a", "evt_b"))["next_state"], [1])
        self.assertEqual(model.predict((0,), ("not_seen",))["status"], "unknown_operation")

    def test_round_trip_preserves_fingerprint(self):
        samples = self.samples()
        spec = compile_ground(samples, discover_operation_candidates(samples))
        model = PartialGenerativeGround.from_json(PartialGenerativeGround(spec).to_json())
        self.assertEqual(model.spec["fingerprint"], spec["fingerprint"])

    def test_single_prestate_does_not_license_global_delta_generalization(self):
        s = [TransitionSample(0, (4,), ("one",), (5,)),
             TransitionSample(1, (4,), ("one",), (5,))]
        c = discover_operation_candidates(s)[0]
        self.assertEqual(c.effect_mode, "single_prestate_table")
        model = PartialGenerativeGround(compile_ground(s, [c]))
        self.assertEqual(model.predict((9,), ("one",))["status"], "unknown_precondition")

    def test_context_table_predicts_only_observed_preconditions(self):
        s = [TransitionSample(0, (0,), ("x",), (1,)),
             TransitionSample(1, (1,), ("x",), (3,)),
             TransitionSample(2, (0,), ("x",), (1,)),
             TransitionSample(3, (1,), ("x",), (3,))]
        model = PartialGenerativeGround(compile_ground(s, discover_operation_candidates(s)))
        self.assertEqual(model.predict((0,), ("x",))["next_state"], [1])
        self.assertEqual(model.predict((5,), ("x",))["status"], "unknown_precondition")

    def test_incremental_interpreter_discovers_without_action_vocabulary(self):
        learner = SelfConstructingGroundInterpreter()
        for x in range(4):
            learner.ingest(TransitionSample(x*2, (x,), ("raw_7", "raw_2"), (x+1,)))
            learner.ingest(TransitionSample(x*2+1, (x,), ("raw_9",), (x+3,)))
        self.assertEqual(learner.snapshot()["candidate_operation_count"], 2)
        self.assertEqual(learner.predict((9,), ("raw_7", "raw_2"))["next_state"], [10])

    def test_online_version_ignores_duplicate_support_when_structure_same(self):
        learner = SelfConstructingGroundInterpreter()
        learner.ingest(TransitionSample(0, (0,), ("r",), (1,)))
        learner.ingest(TransitionSample(1, (0,), ("r",), (1,)))
        v = learner.version
        learner.ingest(TransitionSample(2, (0,), ("r",), (1,)))
        self.assertEqual(learner.version, v)

    def test_online_interpreter_bounds_retained_samples(self):
        learner = SelfConstructingGroundInterpreter(max_samples=4)
        for i in range(8):
            learner.ingest(TransitionSample(i, (i,), ("r",), (i+1,)))
        snap = learner.snapshot()
        self.assertEqual(snap["retained_samples"], 4)
        self.assertEqual(snap["retired_samples"], 4)
        self.assertTrue(snap["data_truncated"])

    def test_report_replays_all_training_examples(self):
        report = build_report(self.samples())
        self.assertEqual(report["evidence_replay"]["mismatched"], 0)
        self.assertEqual(report["evidence_replay"]["unknown"], 0)


class CompetingExplanationTests(unittest.TestCase):
    def test_isolated_spike_is_detected(self):
        self.assertEqual(isolated_spikes([1, 2, 99, 2, 3, 4]), [2])

    def test_multiple_adjacent_changes_are_not_single_spikes(self):
        self.assertEqual(isolated_spikes([1, 2, 99, 98, 3]), [])

    def test_history_collision_resolving_at_longer_horizon(self):
        r = [HistoryTransition((0, 0), ("a",), (1,)),
             HistoryTransition((1, 0), ("a",), (2,))]
        d = diagnose_history_collision(r, max_horizon=2)
        self.assertEqual(d["status"], "insufficient_history")
        self.assertEqual(d["minimum_resolving_horizon"], 2)
        self.assertEqual(d["candidate_predictive_factor"]["type"], "observed_history_lag")
        self.assertEqual(d["candidate_predictive_factor"]["lag"], 2)

    def test_hidden_variable_vs_stochastic_remains_unresolved(self):
        r = [HistoryTransition((0, 0), ("a",), (1,)),
             HistoryTransition((0, 0), ("a",), (2,))]
        d = diagnose_history_collision(r, max_horizon=3)
        self.assertEqual(d["status"], "unresolved_predictive_divergence")
        self.assertIn("stochastic_or_noisy_transition", d["candidate_explanations"])

    def test_sensor_offset_with_stable_reference_is_calibration_candidate(self):
        d = diagnose_sensor_shift({"A": [1,2,3], "ref": [5,5,5]},
                                  {"A": [4,5,6], "ref": [5,5,5]},
                                  reference_channels=["ref"])
        self.assertEqual(d["status"], "sensor_calibration_shift_candidate")
        self.assertEqual(d["constant_offset"], 3)

    def test_sensor_offset_without_reference_is_unresolved(self):
        d = diagnose_sensor_shift({"A": [1,2,3]}, {"A": [4,5,6]}, reference_channels=[])
        self.assertEqual(d["status"], "sensor_remap_vs_system_change_unresolved")

    def test_regime_change_requires_multiple_context_operation_pairs(self):
        baseline = {("q0", "a"): (0,), ("q1", "b"): (1,)}
        records = []
        for step in (10, 11):
            records.append(ConflictRecord(step, "q0", "a", (0,), (2,), "sensorA"))
            records.append(ConflictRecord(step, "q1", "b", (1,), (3,), "sensorB"))
        d = detect_regime_change(baseline, records)
        self.assertEqual(d["status"], "ground_regime_revision_candidate")
        self.assertEqual(d["change_point"], 10)
        self.assertTrue(d["sensor_corroboration"])

    def test_single_conflict_does_not_propose_ground_revision(self):
        d = detect_regime_change({("q0", "a"): (0,)},
                                 [ConflictRecord(1, "q0", "a", (0,), (1,), "A")])
        self.assertNotEqual(d["status"], "ground_regime_revision_candidate")

    def test_noise_candidate_has_no_ground_revision_authority(self):
        e = DiagnosticEvidence(isolated_spike_recovered=True, independent_channels_stable=True)
        d = diagnose_competing_explanations(e)
        self.assertEqual(d["primary_explanation"], "measurement_noise")
        self.assertFalse(d["ground_revision_authorized"])

    def test_new_state_requires_repetition_corrob_and_profile(self):
        weak = diagnose_competing_explanations(DiagnosticEvidence(novel_observation_repeated=1))
        self.assertNotEqual(weak["primary_explanation"], "new_predictive_state_candidate")
        strong = diagnose_competing_explanations(DiagnosticEvidence(
            novel_observation_repeated=4,
            independent_channels_confirm_novelty=True,
            novel_state_has_stable_transition_profile=True))
        self.assertEqual(strong["primary_explanation"], "new_predictive_state_candidate")

    def test_regime_revision_requires_independent_sensor_corroboration(self):
        e = DiagnosticEvidence(multi_context_persistent_transition_conflicts=True,
                              multiple_sensors_corroborate_conflicts=False)
        d = diagnose_competing_explanations(e)
        self.assertNotIn("ground_regime_change_candidate", {x["explanation"] for x in d["candidates"]})

    def test_competing_hidden_and_stochastic_explanations_are_both_retained(self):
        e = DiagnosticEvidence(max_history_still_collides=True,
                              repeated_same_history_action_multiple_outputs=True)
        d = diagnose_competing_explanations(e)
        names = {x["explanation"] for x in d["candidates"]}
        self.assertIn("hidden_predictive_variable_candidate", names)
        self.assertIn("stochastic_or_unmodelled_context", names)
        self.assertTrue(d["unresolved_ambiguities"])

    def test_probe_selector_separates_competing_explanations(self):
        result = choose_discriminating_probe(
            ["sensor_offset", "new_state", "regime_change"],
            {"reference_test": {"sensor_offset": "offset", "new_state": "stable", "regime_change": "stable"},
             "repeat_test": {"sensor_offset": "offset", "new_state": "new", "regime_change": "new"}},
            {"reference_test": {"cost": 1.0, "risk": 0.0},
             "repeat_test": {"cost": 2.0, "risk": 0.0}}, max_risk=0.2)
        self.assertEqual(result["status"], "discriminating_probe_selected")
        self.assertEqual(result["selected_probe"], "reference_test")

    def test_probe_selector_declines_high_risk_only_probe(self):
        result = choose_discriminating_probe(
            ["a", "b"], {"danger": {"a": 0, "b": 1}},
            {"danger": {"cost": 0.1, "risk": 0.9}}, max_risk=0.2)
        self.assertEqual(result["status"], "no_safe_discriminating_probe")

    def test_probe_selector_reports_no_information_when_all_hypotheses_predict_same(self):
        result = choose_discriminating_probe(
            ["a", "b"], {"same": {"a": 1, "b": 1}}, {"same": {"cost": 1, "risk": 0}})
        self.assertEqual(result["status"], "no_safe_discriminating_probe")

    def test_change_point_ignores_records_that_do_not_match_baseline(self):
        baseline = {("q0", "a"): (0,), ("q1", "b"): (1,)}
        records = [ConflictRecord(10, "q0", "a", (9,), (2,), "A"),
                   ConflictRecord(11, "q0", "a", (9,), (2,), "A")]
        d = detect_regime_change(baseline, records)
        self.assertNotEqual(d["status"], "ground_regime_revision_candidate")
        self.assertEqual(len(d["baseline_mismatch_records"]), 2)

    def test_no_evidence_returns_insufficient(self):
        d = diagnose_competing_explanations(DiagnosticEvidence())
        self.assertEqual(d["status"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
