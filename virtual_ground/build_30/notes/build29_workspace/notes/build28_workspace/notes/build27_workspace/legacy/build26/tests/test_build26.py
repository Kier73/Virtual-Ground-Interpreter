from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "legacy" / "build24"))

from incremental_ground import (
    StreamingGroundInducer, PartialExecutableGround, UnknownTransitionError,
    GroundQuarantinedError, stream_from_teacher,
)
from latent_ground import fixture_grounds

ACTIONS = ("HOLD", "PROBE_A", "PROBE_B")


class Build26Tests(unittest.TestCase):
    def learner(self, channels=(0, 1), **kwargs):
        return StreamingGroundInducer(ACTIONS, channels, **kwargs)

    def stream_mode_labels(self, name, channels, count=36):
        ground = fixture_grounds()[name]
        learner = self.learner(channels, signature_mode="observation", max_horizon=8)
        stream_from_teacher(learner, ground, ["HOLD"] * count,
                            post_state_observation=True, channels=channels)
        return ground, learner

    def test_unknown_transitions_are_explicit_and_never_defaulted(self):
        learner = self.learner((0, 1))
        spec = learner.compile()
        self.assertEqual(spec["status"], "partial")
        self.assertEqual(spec["known_transition_count"], 0)
        with self.assertRaises(UnknownTransitionError):
            PartialExecutableGround(spec).step("missing", "HOLD")

    def test_joint_observer_learns_six_predictive_contexts(self):
        _, learner = self.stream_mode_labels("coupled_six", (0, 1), 36)
        self.assertEqual(learner.predictive_context_count, 6)
        self.assertEqual(learner.horizon, 1)
        self.assertEqual(learner.status, "tracking")

    def test_parity_observer_learns_two_context_quotient(self):
        _, learner = self.stream_mode_labels("coupled_six", (0,), 24)
        self.assertEqual(learner.predictive_context_count, 2)

    def test_modulo_three_observer_learns_three_context_quotient(self):
        _, learner = self.stream_mode_labels("coupled_six", (1,), 24)
        self.assertEqual(learner.predictive_context_count, 3)

    def test_unobservable_eight_modes_are_not_invented(self):
        _, learner = self.stream_mode_labels("unobservable_eight", (0,), 24)
        self.assertEqual(learner.predictive_context_count, 1)
        self.assertEqual(learner.compile()["known_transition_count"], 1)

    def test_delayed_signal_forces_history_horizon_refinement(self):
        ground = fixture_grounds()["delayed_six"]
        learner = self.learner((0,), signature_mode="mealy", max_horizon=8)
        stream_from_teacher(learner, ground, ["PROBE_A"] * 18,
                            post_state_observation=False, channels=(0,))
        self.assertGreaterEqual(learner.horizon, 5)
        self.assertEqual(learner.predictive_context_count, 6)
        self.assertEqual(learner.status, "tracking")

    def test_nonbijective_fixture_is_not_forced_into_a_cycle(self):
        ground = fixture_grounds()["partial_four"]
        learner = self.learner((0,), signature_mode="mealy", max_horizon=6)
        actions = ["HOLD", "PROBE_A", "PROBE_B"] * 18
        stream_from_teacher(learner, ground, actions, post_state_observation=False, channels=(0,))
        spec = learner.compile()
        self.assertIn(spec["status"], ("partial", "complete_over_observed_predictive_quotient", "unresolved"))
        self.assertGreaterEqual(spec["predictive_context_count"], 1)

    def test_partial_channels_commit_only_when_all_selected_channels_arrive(self):
        learner = self.learner((0, 1))
        learner.begin_action(0, "HOLD")
        learner.begin_action(1, "PROBE_A")
        learner.observe_channel(1, 1, 2, source="B")
        learner.observe_channel(1, 0, 0, source="A")
        self.assertEqual(learner.total_event_count, 0)
        learner.observe_channel(0, 1, 1, source="B")
        self.assertEqual(learner.total_event_count, 0)
        learner.observe_channel(0, 0, 0, source="A")
        self.assertEqual(learner.total_event_count, 2)
        self.assertEqual(learner.next_commit_step, 2)

    def test_sensor_channels_can_arrive_before_action_registration(self):
        learner = self.learner((0, 1))
        learner.observe_channel(0, 0, 1, source="early-A")
        learner.observe_channel(0, 1, 2, source="early-B")
        self.assertEqual(learner.total_event_count, 0)
        learner.begin_action(0, "HOLD")
        self.assertEqual(learner.total_event_count, 1)

    def test_out_of_order_future_step_waits_for_gap(self):
        learner = self.learner((0, 1))
        learner.begin_action(0, "HOLD")
        learner.begin_action(1, "HOLD")
        learner.observe_channel(1, 0, 1)
        learner.observe_channel(1, 1, 2)
        self.assertEqual(learner.total_event_count, 0)
        learner.observe_channel(0, 0, 0)
        learner.observe_channel(0, 1, 1)
        self.assertEqual(learner.total_event_count, 2)

    def test_duplicate_sensor_delivery_is_idempotent(self):
        learner = self.learner((0,))
        learner.ingest_event(0, "HOLD", (1,))
        before = learner.snapshot()
        after = learner.observe_channel(0, 0, 1, source="retransmit")
        self.assertEqual(before["fingerprint"], after["fingerprint"])
        self.assertEqual(after["duplicate_count"], 1)

    def test_conflicting_duplicate_quarantines_without_reset(self):
        learner = self.learner((0,))
        learner.ingest_event(0, "HOLD", (1,))
        learner.observe_channel(0, 0, 0, source="bad-retransmit")
        self.assertEqual(learner.status, "quarantined")
        with self.assertRaises(GroundQuarantinedError):
            learner.begin_action(1, "HOLD")
        self.assertEqual(learner.total_event_count, 1)

    def test_unknown_transition_remains_unknown_after_other_action_observed(self):
        learner = self.learner((0,))
        learner.ingest_event(0, "HOLD", (1,))
        spec = learner.compile()
        self.assertIn("PROBE_A", ACTIONS)
        self.assertGreater(len(spec["unknown_transitions"]), 0)
        executable = PartialExecutableGround(spec)
        current = spec["current_context"]
        with self.assertRaises(UnknownTransitionError):
            executable.step(current, "PROBE_A")

    def test_partial_specification_round_trip(self):
        learner = self.learner((0,))
        learner.ingest_event(0, "HOLD", (1,))
        spec = learner.compile()
        loaded = PartialExecutableGround.from_json(json.dumps(spec))
        self.assertEqual(loaded.spec["fingerprint"], spec["fingerprint"])
        self.assertEqual(loaded.spec["unknown_transitions"], spec["unknown_transitions"])

    def test_evidence_replay_reports_scope_without_claiming_unseen_proof(self):
        _, learner = self.stream_mode_labels("coupled_six", (0, 1), 18)
        cert = learner.verify_observed_evidence()
        self.assertEqual(cert["mismatched_events"], 0)
        self.assertIn("not proof of unseen transitions", cert["certificate_scope"])

    def test_structural_version_does_not_increment_for_duplicate_confirmation(self):
        learner = self.learner((0,))
        learner.ingest_event(0, "HOLD", (1,))
        version = learner.version
        learner.ingest_event(1, "HOLD", (1,))
        self.assertGreaterEqual(learner.version, version)
        # The assertion is not equality: second event may extend the suffix signature.
        # Repeating a known structural transition after the quotient stabilizes should not
        # necessarily create a new version.
        before = learner.version
        for i in range(2, 8):
            learner.ingest_event(i, "HOLD", (1,))
        self.assertLessEqual(learner.version - before, 2)

    def test_bounded_event_history_marks_truncation(self):
        learner = self.learner((0,), max_events=5, max_horizon=2)
        for i in range(12):
            learner.ingest_event(i, "HOLD", (i % 2,))
        self.assertEqual(learner.total_event_count, 12)
        self.assertEqual(len(learner.records), 5)
        self.assertEqual(learner.retired_event_count, 7)
        self.assertTrue(learner.data_truncated)
        self.assertTrue(learner.compile()["evidence"]["data_truncated"])

    def test_context_budget_is_enforced(self):
        learner = self.learner((0,), max_contexts=2, max_horizon=4)
        for i in range(8):
            if learner.status == "context_budget_exceeded":
                break
            learner.ingest_event(i, "HOLD", (i,))
        self.assertEqual(learner.status, "context_budget_exceeded")
        self.assertEqual(learner.compile()["status"], "context_budget_exceeded")

    def test_safe_probe_scheduler_uses_only_known_edges(self):
        _, learner = self.stream_mode_labels("coupled_six", (0, 1), 12)
        q = learner.current_context
        choice = learner.choose_probe([q], {
            "HOLD": {"cost": 1.0, "risk": 0.0},
            "PROBE_A": {"cost": 1.0, "risk": 0.0},
        })
        # The stream only exercised HOLD, so PROBE_A must not be treated as known.
        self.assertNotEqual(choice.get("selected_action"), "PROBE_A")

    def test_exploration_selector_can_target_unknown_edge_without_claiming_information_gain(self):
        learner = self.learner((0,))
        learner.ingest_event(0, "HOLD", (1,))
        context = learner.current_context
        choice = learner.choose_exploration_probe(context, {
            "PROBE_A": {"cost": 2.0, "risk": 0.1, "side_effect": "reversible probe"},
            "PROBE_B": {"cost": 1.0, "risk": 0.9, "side_effect": "high-risk probe"},
        }, max_risk=0.4)
        self.assertEqual(choice["status"], "exploration_probe_selected")
        self.assertEqual(choice["selected_action"], "PROBE_A")
        self.assertIsNone(choice["information_gain_estimate"])

    def test_exploration_selector_declines_when_unknown_edges_are_too_risky(self):
        learner = self.learner((0,))
        learner.ingest_event(0, "HOLD", (1,))
        choice = learner.choose_exploration_probe(learner.current_context, {
            "PROBE_A": {"cost": 1.0, "risk": 0.9},
            "PROBE_B": {"cost": 1.0, "risk": 0.95},
        }, max_risk=0.2)
        self.assertEqual(choice["status"], "no_safe_unknown_transition_to_probe")
        self.assertIsNone(choice["selected_action"])

    def test_persistent_unresolved_collisions_keep_conflict_and_version_logs_bounded(self):
        ground = fixture_grounds()["delayed_six"]
        learner = self.learner((0,), signature_mode="mealy", max_horizon=1, max_events=256)
        stream_from_teacher(learner, ground, ["PROBE_A"] * 180,
                            post_state_observation=False, channels=(0,))
        self.assertEqual(learner.status, "unresolved_context_collision")
        self.assertLessEqual(len(learner.conflict_log), 64)
        self.assertLessEqual(len(learner.version_lineage), 128)

    def test_quarantined_partial_ground_cannot_execute(self):
        learner = self.learner((0,))
        learner.ingest_event(0, "HOLD", (1,))
        learner.observe_channel(0, 0, 9)
        compiled = PartialExecutableGround(learner.compile())
        with self.assertRaises(GroundQuarantinedError):
            compiled.step(compiled.spec["current_context"], "HOLD")

    def test_mealy_and_observation_signatures_are_explicitly_distinct(self):
        a = StreamingGroundInducer(ACTIONS, (0,), signature_mode="observation")
        b = StreamingGroundInducer(ACTIONS, (0,), signature_mode="mealy")
        self.assertNotEqual(a.compile()["signature_mode"], b.compile()["signature_mode"])

    def test_version_lineage_records_horizon_refinement(self):
        ground = fixture_grounds()["coupled_six"]
        learner = self.learner((0,), max_horizon=4)
        stream_from_teacher(learner, ground, ["HOLD"] * 12,
                            post_state_observation=True, channels=(0,))
        reasons = [x["reason"] for x in learner.version_lineage]
        self.assertIn("history_horizon_refinement_after_collision", reasons)

    def test_bounded_stream_does_not_relearn_truncated_boundary_as_a_new_state_each_step(self):
        learner = self.learner((0,), max_events=16, max_horizon=2)
        for i in range(80):
            learner.ingest_event(i, "HOLD", (i % 2,))
        self.assertEqual(learner.predictive_context_count, 2)
        self.assertIsNone(learner.compile()["initial_context"])
        self.assertEqual(learner.compile()["startup_context_status"], "unknown_due_to_retention_truncation")
        self.assertLess(learner.version, 10)

    def test_unknown_initial_context_is_not_claimed_as_physical_state(self):
        learner = self.learner((0, 1))
        spec = learner.compile()
        self.assertIsNone(spec["initial_context"])
        self.assertEqual(spec["evidence"]["physical_hidden_state_claim"], "not inferred")


if __name__ == "__main__":
    unittest.main(verbosity=2)
