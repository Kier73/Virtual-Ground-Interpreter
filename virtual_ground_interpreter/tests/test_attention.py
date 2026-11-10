import json
from pathlib import Path
import unittest

from vgi.attention import (
    AttentionCandidate, AttentionError, exhaustive_attention_plan,
    greedy_attention_plan, rank_attention_probes, unresolved_pair_count,
)
from vgi.relational import ObserverContext
from vgi.transitions import GroundTransitionSystem, TransitionObservation, TransitionOutcome

ROOT = Path(__file__).resolve().parents[1]


def delayed_six():
    data = json.loads(
        (ROOT / "examples" / "delayed_six_predictive_ground.json").read_text(encoding="utf-8")
    )
    return GroundTransitionSystem.from_predictive_mealy_dict(data)


def complementary_probe_ground():
    """B's y channel is the only observation that distinguishes p0 from p1."""
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


class ActiveAttentionTests(unittest.TestCase):
    def test_delayed_six_ranks_the_missing_probe_as_high_value(self):
        ground = delayed_six()
        observer = ObserverContext("routine", ("HOLD", "PROBE_B"), ("channel_0",))
        candidate = AttentionCandidate("action", "PROBE_A", cost=1.0)
        scores = rank_attention_probes(ground, observer, (candidate,), horizon=5)
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].reduction, 15)
        self.assertEqual(scores[0].unresolved_after, 0)
        self.assertEqual(scores[0].gain_per_cost, 15.0)

        plan = greedy_attention_plan(ground, observer, (candidate,), 5, budget=1.0)
        self.assertEqual(plan.selected, (candidate,))
        self.assertEqual(plan.reduction, 15)
        self.assertEqual(plan.quotient.class_count, 6)

    def test_single_probe_greedy_search_misses_complementary_information(self):
        ground = complementary_probe_ground()
        observer = ObserverContext("initial", ("A",), ("x",))
        candidates = (
            AttentionCandidate("action", "B", cost=1.0),
            AttentionCandidate("channel", "y", cost=1.0),
        )

        scores = rank_attention_probes(ground, observer, candidates, horizon=1)
        self.assertEqual({score.reduction for score in scores}, {0})

        greedy = greedy_attention_plan(ground, observer, candidates, 1, budget=2.0)
        self.assertEqual(greedy.selected, ())
        self.assertEqual(greedy.initial_unresolved_pairs, 1)
        self.assertEqual(greedy.final_unresolved_pairs, 1)

        after_action = ObserverContext("after-B", ("A", "B"), ("x",))
        delayed_score = rank_attention_probes(
            ground, after_action, (candidates[1],), horizon=1
        )[0]
        self.assertEqual(delayed_score.reduction, 1)

        exact = exhaustive_attention_plan(ground, observer, candidates, 1, budget=2.0)
        self.assertEqual(exact.selected, candidates)
        self.assertEqual(exact.total_cost, 2.0)
        self.assertEqual(exact.initial_unresolved_pairs, 1)
        self.assertEqual(exact.final_unresolved_pairs, 0)
        self.assertEqual(exact.reduction, 1)
        self.assertEqual(exact.quotient.class_count, 2)

    def test_budget_constrains_complementary_probe_selection(self):
        ground = complementary_probe_ground()
        observer = ObserverContext("initial", ("A",), ("x",))
        candidates = (
            AttentionCandidate("action", "B"),
            AttentionCandidate("channel", "y"),
        )
        exact = exhaustive_attention_plan(ground, observer, candidates, 1, budget=1.0)
        self.assertEqual(exact.selected, ())
        self.assertEqual(exact.total_cost, 0.0)
        self.assertEqual(exact.final_unresolved_pairs, 1)

    def test_exhaustive_and_greedy_agree_when_information_is_separable(self):
        ground = delayed_six()
        observer = ObserverContext("routine", ("HOLD", "PROBE_B"), ("channel_0",))
        candidates = (AttentionCandidate("action", "PROBE_A", cost=2.0),)
        greedy = greedy_attention_plan(ground, observer, candidates, 5, budget=2.0)
        exact = exhaustive_attention_plan(ground, observer, candidates, 5, budget=2.0)
        self.assertEqual(greedy.final_unresolved_pairs, exact.final_unresolved_pairs)
        self.assertEqual(greedy.selected, (candidates[0],))
        self.assertEqual(exact.selected, (candidates[0],))

    def test_candidate_costs_and_budgets_are_validated(self):
        with self.assertRaises(AttentionError):
            AttentionCandidate("action", "B", cost=0)
        with self.assertRaises(AttentionError):
            AttentionCandidate("sensor", "B", cost=1)
        ground = complementary_probe_ground()
        observer = ObserverContext("initial", ("A",), ("x",))
        with self.assertRaises(AttentionError):
            greedy_attention_plan(
                ground, observer, (AttentionCandidate("action", "B"),), 1, budget=-1
            )
        with self.assertRaises(AttentionError):
            exhaustive_attention_plan(
                ground, observer,
                (AttentionCandidate("action", "B"),),
                1, budget=1, max_candidates=0,
            )

    def test_candidates_cannot_repeat_observed_or_duplicate_capabilities(self):
        ground = complementary_probe_ground()
        observer = ObserverContext("initial", ("A",), ("x",))
        with self.assertRaises(AttentionError):
            rank_attention_probes(
                ground, observer, (AttentionCandidate("action", "A"),), 1
            )
        with self.assertRaises(AttentionError):
            rank_attention_probes(
                ground, observer,
                (AttentionCandidate("channel", "y"), AttentionCandidate("channel", "y")),
                1,
            )

    def test_unresolved_pair_count_is_partition_invariant(self):
        ground = complementary_probe_ground()
        observer = ObserverContext("initial", ("A",), ("x",))
        one_class = exhaustive_attention_plan(
            ground, observer, (), 1, budget=0
        ).quotient
        self.assertEqual(unresolved_pair_count(one_class), 1)


if __name__ == "__main__":
    unittest.main()
