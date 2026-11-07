from __future__ import annotations
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
B24 = ROOT / "legacy" / "build24"
sys.path.insert(0, str(B24))
sys.path.insert(0, str(ROOT))

from latent_ground import LearnedMealyGround
from online_ground import (
    ClockFit, GroundVersionMonitor, LocalClockRegistry, OnlineBeliefTracker,
    ProbeProfile, SafeProbeScheduler, load_machine_from_spec,
)

REPORTS = B24 / "reports"


def machine(name: str) -> LearnedMealyGround:
    return load_machine_from_spec(str(REPORTS / f"ground_spec_{name}.json"))


class Build25Tests(unittest.TestCase):
    def test_unknown_initial_context_starts_with_all_predictive_states(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        self.assertEqual(set(tracker.belief), set(m.states))

    def test_full_sensor_observation_refines_unknown_start(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        tracker.begin_action(0, "HOLD")
        # Physical starting context q2 emits (0,2); the learner is not told q2.
        tracker.observe_channel(0, 1, 2, source="sensor-B")
        self.assertEqual(len(tracker.belief), 2)
        tracker.observe_channel(0, 0, 0, source="sensor-A")
        self.assertEqual(len(tracker.belief), 1)
        self.assertEqual(tracker.belief, ("q3",))

    def test_observer_quotient_is_retained_not_expanded(self):
        m = machine("coupled_six__parity_only")
        tracker = OnlineBeliefTracker(m)
        self.assertEqual(len(tracker.belief), 2)
        tracker.begin_action(0, "HOLD")
        tracker.observe_channel(0, 0, 1)
        self.assertEqual(len(tracker.belief), 1)
        self.assertEqual(set(m.states), {"q0", "q1"})

    def test_unobservable_contexts_remain_ambiguous(self):
        m = machine("unobservable_eight__available")
        tracker = OnlineBeliefTracker(m)
        for i in range(5):
            tracker.begin_action(i, "HOLD")
            tracker.observe_channel(i, 0, 0, source="constant-sensor")
        self.assertEqual(len(tracker.belief), 1)
        self.assertEqual(tracker.status, "tracking")

    def test_delayed_distinction_appears_only_after_long_probe(self):
        m = machine("delayed_six__available")
        tracker = OnlineBeliefTracker(m)
        for i in range(5):
            tracker.begin_action(i, "HOLD")
            tracker.observe_channel(i, 0, 0)
        self.assertEqual(len(tracker.belief), 6)
        tracker.begin_action(5, "PROBE_A")
        tracker.observe_channel(5, 0, 1)
        self.assertEqual(len(tracker.belief), 1)

    def test_late_out_of_order_sensor_events_filter_full_path(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        tracker.begin_action(0, "HOLD")
        tracker.begin_action(1, "PROBE_A")
        # Step 1 arrives before the earlier step 0 outputs.
        tracker.observe_channel(1, 1, 0, source="B")
        tracker.observe_channel(0, 1, 2, source="B")
        tracker.observe_channel(1, 0, 1, source="A")
        tracker.observe_channel(0, 0, 0, source="A")
        self.assertEqual(len(tracker.belief), 1)
        self.assertEqual(tracker.belief, ("q5",))
        self.assertEqual(tracker.unresolved_steps, ())

    def test_sensor_output_can_arrive_before_action_record(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        tracker.observe_channel(0, 1, 2, source="fast-sensor")
        tracker.begin_action(0, "HOLD")
        tracker.observe_channel(0, 0, 0, source="slow-sensor")
        self.assertEqual(len(tracker.belief), 1)

    def test_duplicate_sensor_retransmission_is_idempotent(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        tracker.begin_action(0, "HOLD")
        tracker.observe_channel(0, 0, 0)
        tracker.observe_channel(0, 1, 2)
        before = tracker.snapshot()
        after = tracker.observe_channel(0, 1, 2, source="retransmit")
        self.assertEqual(before["belief"], after["belief"])
        self.assertEqual(after["status"], "tracking")

    def test_conflict_quarantines_without_automatic_reset(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        tracker.begin_action(0, "HOLD")
        tracker.observe_channel(0, 0, 9, source="faulty-sensor")
        self.assertEqual(tracker.status, "contradicted")
        self.assertIsNotNone(tracker.conflict)
        with self.assertRaises(RuntimeError):
            tracker.begin_action(1, "HOLD")

    def test_conflict_evidence_is_preserved(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        tracker.begin_action(0, "HOLD")
        tracker.observe_channel(0, 0, 9)
        evidence = tracker.export_evidence()
        self.assertEqual(evidence["format"], "VG-OnlineEvidence-1")
        self.assertEqual(evidence["status"], "contradicted")
        self.assertEqual(evidence["snapshot"]["version_monitor"]["auto_committed"], False)

    def test_single_conflict_does_not_propose_revision(self):
        mon = GroundVersionMonitor("abc")
        from online_ground import Conflict
        mon.record(Conflict(0, "HOLD", ((0, 9),), (), "sensor", "unexpected"))
        self.assertEqual(mon.status, "single_or_unconfirmed_conflict")

    def test_independent_conflicts_propose_but_do_not_commit_revision(self):
        mon = GroundVersionMonitor("abc")
        from online_ground import Conflict
        mon.record(Conflict(0, "HOLD", ((0, 9),), (), "sensor-A", "unexpected"))
        out = mon.record(Conflict(2, "PROBE_A", ((0, 8),), (), "sensor-B", "unexpected"))
        self.assertEqual(out["status"], "ground_revision_proposal")
        self.assertFalse(out["auto_committed"])

    def test_safe_probe_scheduler_avoids_high_risk_action(self):
        m = machine("coupled_six__joint")
        scheduler = SafeProbeScheduler(m, max_risk=0.4)
        profiles = {
            "HOLD": ProbeProfile(1.0, 0.0, "passive"),
            "PROBE_A": ProbeProfile(2.0, 0.1, "small reversible effect"),
            "PROBE_B": ProbeProfile(0.1, 0.9, "irreversible effect"),
        }
        choice = scheduler.choose(m.states, profiles)
        self.assertEqual(choice["status"], "selected")
        self.assertNotEqual(choice["selected_action"], "PROBE_B")
        self.assertTrue(all(x["risk"] <= 0.4 for x in choice["candidates"]))

    def test_scheduler_returns_no_probe_when_all_probes_uninformative(self):
        m = machine("unobservable_eight__available")
        scheduler = SafeProbeScheduler(m)
        profiles = {a: ProbeProfile(1, 0) for a in m.transitions[m.initial]}
        choice = scheduler.choose(m.states, profiles)
        self.assertEqual(choice["status"], "no_safe_informative_probe")
        self.assertIsNone(choice["selected_action"])

    def test_local_clocks_are_not_joined_by_raw_timestamp(self):
        reg = LocalClockRegistry()
        a = reg.add_event(source="A", source_sequence=1, local_timestamp=105.0,
                         channel=0, value=1, step_id=None)
        b = reg.add_event(source="B", source_sequence=1, local_timestamp=105.0,
                         channel=1, value=2, step_id=None)
        self.assertEqual(a["join_status"], "unmatched_no_shared_event_identity")
        self.assertEqual(b["join_status"], "unmatched_no_shared_event_identity")
        self.assertEqual(reg.summary()["retained_unmatched_event_count"], 2)

    def test_explicit_step_identity_joins_async_sources(self):
        reg = LocalClockRegistry()
        a = reg.add_event(source="A", source_sequence=1, local_timestamp=8.0,
                         channel=0, value=0, step_id=12)
        b = reg.add_event(source="B", source_sequence=1, local_timestamp=203.0,
                         channel=1, value=2, step_id=12)
        self.assertEqual(a["join_status"], "joined_by_explicit_step_id")
        self.assertEqual(b["join_status"], "joined_by_explicit_step_id")

    def test_clock_fit_recovers_offset_and_drift_with_two_anchors(self):
        clock = ClockFit("B")
        # local = 2 * reference + 100; map local -> reference.
        clock.add_anchor(100.0, 0.0)
        clock.add_anchor(104.0, 2.0)
        clock.add_anchor(110.0, 5.0)
        self.assertEqual(clock.status, "affine_clock_calibrated")
        self.assertAlmostEqual(clock.slope, 0.5)
        self.assertAlmostEqual(clock.intercept, -50.0)
        self.assertAlmostEqual(clock.to_reference(110.0), 5.0)

    def test_single_anchor_does_not_claim_drift_calibration(self):
        clock = ClockFit("A")
        clock.add_anchor(10.0, 0.0)
        self.assertEqual(clock.status, "offset_only_drift_unresolved")
        with self.assertRaises(RuntimeError):
            clock.to_reference(12.0)

    def test_source_sequence_enforces_source_local_order(self):
        reg = LocalClockRegistry()
        reg.add_event(source="A", source_sequence=2, local_timestamp=1, channel=0, value=0)
        with self.assertRaises(ValueError):
            reg.add_event(source="A", source_sequence=1, local_timestamp=2, channel=0, value=1)

    def test_clock_models_are_independent_per_source(self):
        reg = LocalClockRegistry()
        reg.add_anchor("A", 10, 0)
        reg.add_anchor("A", 20, 10)
        reg.add_anchor("B", 100, 0)
        reg.add_anchor("B", 120, 10)
        self.assertAlmostEqual(reg.map_time("A", 15), 5)
        self.assertAlmostEqual(reg.map_time("B", 110), 5)
        self.assertNotEqual(reg.clocks["A"].slope, reg.clocks["B"].slope)

    def test_machine_loaded_without_teacher_or_reset(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        self.assertFalse(hasattr(tracker, "teacher"))
        self.assertFalse(hasattr(tracker, "reset"))

    def test_partial_four_nonbijective_machine_tracks_online(self):
        m = machine("partial_four__available")
        tracker = OnlineBeliefTracker(m)
        for i, action in enumerate(("HOLD", "PROBE_A", "HOLD")):
            tracker.begin_action(i, action)
            # select an output expected from at least one currently live state
            state = tracker.belief[0]
            value = m.outputs[state][action][0]
            tracker.observe_channel(i, 0, value)
        self.assertIn(tracker.status, ("tracking", "contradicted"))

    def test_action_effect_is_applied_even_before_observation_arrives(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        tracker.begin_action(0, "PROBE_B")
        self.assertIn(0, tracker.unresolved_steps)
        tracker.begin_action(1, "HOLD")
        self.assertIn(0, tracker.unresolved_steps)
        self.assertIn(1, tracker.unresolved_steps)

    def test_pending_horizon_is_bounded(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m, max_pending_steps=2)
        tracker.begin_action(0, "HOLD")
        tracker.begin_action(1, "HOLD")
        with self.assertRaises(RuntimeError):
            tracker.begin_action(2, "HOLD")

    def test_export_does_not_claim_physical_hidden_state(self):
        m = machine("coupled_six__residue3_only")
        tracker = OnlineBeliefTracker(m)
        ev = tracker.export_evidence()
        self.assertTrue(ev["unknown_initial_context"])
        self.assertEqual(len(ev["initial_candidate_states"]), 3)

    def test_completed_steps_are_compacted_from_live_memory(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m, history_limit=8, completed_cache_limit=3)
        for i in range(10):
            q = tracker.belief[0]
            action = "HOLD"
            output = m.outputs[q][action]
            tracker.begin_action(i, action)
            tracker.observe_channel(i, 0, output[0])
            tracker.observe_channel(i, 1, output[1])
        self.assertEqual(tracker.completed_step_count, 10)
        self.assertLessEqual(len(tracker.completed_cache), 3)
        self.assertEqual(tracker.observations, {})
        self.assertEqual(tracker.actions_by_step, {})
        self.assertLessEqual(len(tracker.history), 8)
        self.assertGreater(tracker.history_total_count, len(tracker.history))

    def test_old_event_outside_duplicate_retention_is_stale_not_new_evidence(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m, completed_cache_limit=1)
        for i in range(3):
            q = tracker.belief[0]
            out = m.outputs[q]["HOLD"]
            tracker.begin_action(i, "HOLD")
            tracker.observe_channel(i, 0, out[0])
            tracker.observe_channel(i, 1, out[1])
        before = tracker.status
        after = tracker.observe_channel(0, 0, 123, source="delayed-stale-event")
        self.assertEqual(before, "tracking")
        self.assertEqual(after["status"], "tracking")
        self.assertIn("stale_observation_outside_retention", [h["kind"] for h in tracker.history])

    def test_clock_registry_event_and_unmatched_buffers_are_bounded(self):
        reg = LocalClockRegistry(event_history_limit=5, unmatched_history_limit=2)
        for i in range(10):
            reg.add_event(source="A", source_sequence=i, local_timestamp=float(i),
                          channel=0, value=i, step_id=None)
        summary = reg.summary()
        self.assertEqual(summary["total_event_count"], 10)
        self.assertEqual(summary["retained_event_count"], 5)
        self.assertEqual(summary["total_unmatched_event_count"], 10)
        self.assertEqual(summary["retained_unmatched_event_count"], 2)

    def test_clock_registry_delivers_by_shared_step_identity(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        tracker.begin_action(0, "HOLD")
        reg = LocalClockRegistry()
        receipt_b = reg.add_event(source="B", source_sequence=1, local_timestamp=111,
                                  channel=1, value=2, step_id=0)
        receipt_a = reg.add_event(source="A", source_sequence=1, local_timestamp=8,
                                  channel=0, value=0, step_id=0)
        reg.deliver(tracker, receipt_b)
        after_b = len(tracker.belief)
        reg.deliver(tracker, receipt_a)
        self.assertEqual(after_b, 2)
        self.assertEqual(len(tracker.belief), 1)

    def test_unkeyed_clock_event_is_not_delivered_as_a_measurement(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        reg = LocalClockRegistry()
        receipt = reg.add_event(source="A", source_sequence=1, local_timestamp=1,
                                channel=0, value=99, step_id=None)
        result = reg.deliver(tracker, receipt)
        self.assertEqual(result["status"], "unmatched")
        self.assertEqual(tracker.status, "tracking")
        self.assertEqual(len(tracker.belief), 6)

    def test_clock_mapping_requires_distinct_anchor_geometry(self):
        clock = ClockFit("A")
        clock.add_anchor(5, 0)
        clock.add_anchor(5, 1)
        self.assertEqual(clock.status, "insufficient_clock_geometry")
        with self.assertRaises(RuntimeError):
            clock.to_reference(6)

    def test_invalid_risk_profile_is_rejected(self):
        m = machine("coupled_six__joint")
        scheduler = SafeProbeScheduler(m)
        with self.assertRaises(ValueError):
            scheduler.choose(m.states, {"HOLD": ProbeProfile(1, 1.5)})

    def test_conflicting_duplicate_sensor_event_is_quarantined(self):
        m = machine("coupled_six__joint")
        tracker = OnlineBeliefTracker(m)
        tracker.begin_action(0, "HOLD")
        tracker.observe_channel(0, 0, 0, source="sensor-A")
        result = tracker.observe_channel(0, 0, 9, source="sensor-A-revision")
        self.assertEqual(result["status"], "contradicted")
        self.assertEqual(result["conflict"]["observed"]["0"], 9)

    def test_scheduler_declines_when_every_informative_probe_is_over_risk_limit(self):
        m = machine("coupled_six__joint")
        scheduler = SafeProbeScheduler(m, max_risk=0.2)
        profiles = {a: ProbeProfile(1, 0.95, "high-impact") for a in m.transitions[m.initial]}
        result = scheduler.choose(m.states, profiles)
        self.assertEqual(result["status"], "no_safe_informative_probe")
        self.assertIsNone(result["selected_action"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
