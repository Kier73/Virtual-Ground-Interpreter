import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ground_discovery import *


class DiscoveryGroundTests(unittest.TestCase):
    def setUp(self):
        self.models = candidate_grounds()

    def test_candidate_family_has_32_distinct_parameter_sets(self):
        self.assertEqual(len(self.models), 32)
        self.assertEqual(len({h.identifier for h in self.models}), 32)

    def test_every_model_preserves_mass_balance(self):
        for h in self.models:
            for a in range(h.capacity + 1):
                for b in range(h.capacity + 1):
                    for p in range(4):
                        s = State(a, b, p)
                        for action in ACTIONS:
                            _, ledger = h.step(s, action)
                            self.assertEqual(ledger["mass_balance_residual"], 0)

    def test_all_models_are_behaviorally_distinguishable_in_probe_catalog(self):
        classes = behavioral_equivalence_classes(self.models)
        self.assertEqual(len(classes), 32)
        self.assertTrue(all(len(c) == 1 for c in classes))

    def test_probe_cost_is_positive(self):
        for probe in probe_catalog():
            self.assertGreater(probe_cost(probe), 0)

    def test_information_gain_nonnegative_and_bounded(self):
        probe = Probe(State(2, 0, 0), "A_TO_B", "FULL")
        ig = probe_information_gain(self.models, probe)
        self.assertGreaterEqual(ig, 0)
        self.assertLessEqual(ig, math.log2(len(self.models)) + 1e-12)

    def test_active_probe_never_eliminates_true_model_for_every_hypothesis(self):
        for true in self.models:
            result = run_active_identification(true)
            self.assertTrue(result["identified"], true.identifier)
            self.assertEqual(result["remaining_hypotheses"], 1)
            self.assertEqual(result["probe_count"], 2)
            self.assertIn(true.identifier, result["remaining_ids"])

    def test_active_policy_uses_probe_information_per_cost(self):
        probe, details = choose_probe(self.models)
        self.assertIsNotNone(probe)
        self.assertGreater(details["information_gain_bits"], 0)
        self.assertGreater(details["score_per_cost"], 0)

    def test_passive_hold_cannot_identify_transfer_quantum(self):
        for true in self.models:
            result = run_passive_identification(true, 12)
            self.assertGreaterEqual(result["remaining_hypotheses"], 2)
            self.assertTrue(any("Q1" in x for x in result["remaining_ids"]))
            self.assertTrue(any("Q2" in x for x in result["remaining_ids"]))

    def test_sensor_cost_changes_probe_selection(self):
        cheap_full = DEFAULT_COST_MODEL
        expensive_full = {
            "reset": 1.0,
            "action": {"HOLD": 0.25, "A_TO_B": 1.0, "B_TO_A": 1.0},
            "sensor": {"TOTAL": 0.2, "LEVELS": 0.5, "FULL": 20.0},
        }
        p_default, _ = choose_probe(self.models, cost_model=cheap_full)
        p_constrained, _ = choose_probe(self.models, cost_model=expensive_full)
        self.assertNotEqual(p_default.identifier, p_constrained.identifier)
        self.assertEqual(p_default.sensor, "FULL")
        self.assertEqual(p_constrained.sensor, "LEVELS")

    def test_out_of_family_model_can_match_discovery_probes_but_fail_holdout(self):
        actual = GroundHypothesis(3, "inflow_C", "demand_A", 1, 1)
        result = run_active_identification(actual)
        self.assertTrue(result["identified"])
        selected_id = result["remaining_ids"][0]
        selected = next(h for h in self.models if h.identifier == selected_id)
        self.assertEqual(selected.inflow_name, "inflow_A")
        holdout = Probe(State(0, 0, 1), "HOLD", "LEVELS")
        self.assertNotEqual(predict(selected, holdout), predict(actual, holdout))

    def test_one_observation_conflict_is_quarantined_not_ground_shift(self):
        h = self.models[0]
        monitor = ChangeEvidence()
        probe = Probe(State(0, 0, 0), "HOLD", "FULL")
        actual = observe(h.step(probe.initial, probe.action)[0], probe.sensor)
        altered = (actual[0] + 1, actual[1], actual[2])
        result = monitor.ingest([h], probe, altered, [h.revised(inflow_name="inflow_B")])
        self.assertEqual(result["status"], "quarantined_single_conflict")
        self.assertFalse(monitor.proposed)

    def test_repeated_independent_conflicts_propose_revised_ground(self):
        old = GroundHypothesis(3, "inflow_A", "demand_A", 1, 1, 1)
        revised = old.revised(inflow_name="inflow_B")
        monitor = ChangeEvidence()
        p1 = Probe(State(0, 0, 0), "HOLD", "FULL")
        p2 = Probe(State(0, 0, 1), "HOLD", "FULL")
        o1 = observe(revised.step(p1.initial, p1.action)[0], p1.sensor)
        o2 = observe(revised.step(p2.initial, p2.action)[0], p2.sensor)
        r1 = monitor.ingest([old], p1, o1, [revised])
        self.assertEqual(r1["status"], "quarantined_single_conflict")
        r2 = monitor.ingest([old], p2, o2, [revised])
        self.assertEqual(r2["status"], "ground_revision_candidate")
        self.assertTrue(monitor.proposed)

    def test_current_ground_consistency_resets_conflict_streak(self):
        h = self.models[0]
        monitor = ChangeEvidence()
        p = Probe(State(0, 0, 0), "HOLD", "FULL")
        bad = (9, 9, 9)
        monitor.ingest([h], p, bad, [])
        good = observe(h.step(p.initial, p.action)[0], p.sensor)
        result = monitor.ingest([h], p, good, [])
        self.assertEqual(result["status"], "consistent_with_current_ground")
        self.assertEqual(monitor.conflict_streak, 0)

    def test_phase_and_level_outputs_are_distinct_sensor_abstractions(self):
        h = GroundHypothesis(3, "inflow_A", "demand_A", 1, 1)
        p = Probe(State(1, 1, 0), "HOLD", "FULL")
        state = h.step(p.initial, p.action)[0]
        self.assertEqual(observe(state, "FULL"), (2, 1, 1))
        self.assertEqual(observe(state, "LEVELS"), (2, 1))
        self.assertEqual(observe(state, "TOTAL"), (3,))

    def test_reset_probe_catalog_covers_calibrated_initial_states(self):
        probes = probe_catalog()
        self.assertEqual(len(probes), 3 * 3 * 4 * 3 * 3)
        self.assertTrue(all(p.initial.a <= 2 and p.initial.b <= 2 for p in probes))


if __name__ == "__main__":
    unittest.main()
