import json
from pathlib import Path
import unittest

from vgi.attention import (
    AttentionCandidate, exhaustive_attention_plan, greedy_attention_plan,
)
from vgi.joint_attention import AttentionError, beam_attention_plan
from vgi.relational import ObserverContext
from vgi.transitions import GroundTransitionSystem, TransitionObservation, TransitionOutcome

ROOT = Path(__file__).resolve().parents[1]


def delayed_six():
    data = json.loads(
        (ROOT / "examples" / "delayed_six_predictive_ground.json").read_text(encoding="utf-8")
    )
    return GroundTransitionSystem.from_predictive_mealy_dict(data)


def complementary_probe_ground():
    states = ("p0", "p1")
    observations = (
        TransitionObservation("p0", "A", (TransitionOutcome("p0", (0, 0)),)),
        TransitionObservation("p1", "A", (TransitionOutcome("p1", (0, 0)),)),
        TransitionObservation("p0", "B", (TransitionOutcome("p0", (0, 0)),)),
        TransitionObservation("p1", "B", (TransitionOutcome("p1", (0, 1)),)),
    )
    return GroundTransitionSystem(
        states, ("A", "B"), "p0", ("x", "y"), observations,
        {"family": "complementary observation fixture"},
    )


class JointAttentionNavigationTests(unittest.TestCase):
    def test_beam_search_navigates_both_observer_and_predictive_spaces(self):
        ground = complementary_probe_ground()
        initial = ObserverContext("initial", ("A",), ("x",))
        candidates = (
            AttentionCandidate("action", "B", 1.0),
            AttentionCandidate("channel", "y", 1.0),
        )
        result = beam_attention_plan(
            ground, initial, candidates, horizon=1, budget=2.0,
            beam_width=2, max_depth=2,
        )

        self.assertEqual(result.final_unresolved_pairs, 0)
        self.assertEqual(result.reduction, 1)
        self.assertEqual(result.total_cost, 2.0)
        self.assertEqual(result.observer.actions, ("A", "B"))
        self.assertEqual(result.observer.channels, ("x", "y"))
        self.assertEqual(result.quotient.class_count, 2)
        self.assertEqual(
            tuple(candidate.key for candidate in result.selected),
            (("action", "B"), ("channel", "y")),
        )

        self.assertEqual(len(result.route), 2)
        self.assertEqual(result.route[0].unresolved_before, 1)
        self.assertEqual(result.route[0].unresolved_after, 1)
        self.assertEqual(result.route[0].class_count, 1)
        self.assertEqual(result.route[1].unresolved_before, 1)
        self.assertEqual(result.route[1].unresolved_after, 0)
        self.assertEqual(result.route[1].class_count, 2)

        single_action = next(r for r in result.search_records
                             if tuple(c.key for c in r.selected) == (("action", "B"),))
        single_channel = next(r for r in result.search_records
                              if tuple(c.key for c in r.selected) == (("channel", "y"),))
        self.assertTrue(single_action.retained_in_beam)
        self.assertTrue(single_channel.retained_in_beam)
        self.assertEqual(result.expanded_nodes, 3)
        self.assertEqual(result.visited_configurations, 4)
        self.assertEqual(result.termination_reason, "fully_resolved")

    def test_joint_beam_search_recovers_complement_greedy_cannot_see(self):
        ground = complementary_probe_ground()
        initial = ObserverContext("initial", ("A",), ("x",))
        candidates = (
            AttentionCandidate("action", "B"),
            AttentionCandidate("channel", "y"),
        )
        greedy = greedy_attention_plan(ground, initial, candidates, 1, 2.0)
        exact = exhaustive_attention_plan(ground, initial, candidates, 1, 2.0)
        beam = beam_attention_plan(
            ground, initial, candidates, 1, 2.0, beam_width=2, max_depth=2
        )
        self.assertEqual(greedy.selected, ())
        self.assertEqual(beam.final_unresolved_pairs, exact.final_unresolved_pairs)
        self.assertEqual(beam.selected, exact.selected)

    def test_search_preserves_delayed_six_single_probe_path(self):
        ground = delayed_six()
        initial = ObserverContext("routine", ("HOLD", "PROBE_B"), ("channel_0",))
        candidate = AttentionCandidate("action", "PROBE_A", 1.0)
        result = beam_attention_plan(
            ground, initial, (candidate,), 5, 1.0, beam_width=2, max_depth=2
        )
        self.assertEqual(result.selected, (candidate,))
        self.assertEqual(result.initial_unresolved_pairs, 15)
        self.assertEqual(result.final_unresolved_pairs, 0)
        self.assertEqual(result.route[0].actions, ("HOLD", "PROBE_B", "PROBE_A"))
        self.assertEqual(result.termination_reason, "fully_resolved")

    def test_budget_and_depth_bound_the_perception_search(self):
        ground = complementary_probe_ground()
        initial = ObserverContext("initial", ("A",), ("x",))
        candidates = (
            AttentionCandidate("action", "B"),
            AttentionCandidate("channel", "y"),
        )
        too_shallow = beam_attention_plan(
            ground, initial, candidates, 1, 2.0, beam_width=2, max_depth=1
        )
        self.assertEqual(too_shallow.final_unresolved_pairs, 1)
        self.assertEqual(too_shallow.selected, ())
        self.assertEqual(too_shallow.termination_reason, "max_depth")

        under_budget = beam_attention_plan(
            ground, initial, candidates, 1, 1.0, beam_width=2, max_depth=2
        )
        self.assertEqual(under_budget.final_unresolved_pairs, 1)
        self.assertEqual(under_budget.selected, ())

    def test_beam_width_and_depth_are_validated(self):
        ground = complementary_probe_ground()
        initial = ObserverContext("initial", ("A",), ("x",))
        candidates = (
            AttentionCandidate("action", "B"),
            AttentionCandidate("channel", "y"),
        )
        with self.assertRaises(AttentionError):
            beam_attention_plan(ground, initial, candidates, 1, 2.0, beam_width=0)
        with self.assertRaises(AttentionError):
            beam_attention_plan(ground, initial, candidates, 1, 2.0, max_depth=-1)
        with self.assertRaises(AttentionError):
            beam_attention_plan(ground, initial, candidates, 1, 2.0, max_depth=True)


if __name__ == "__main__":
    unittest.main()
