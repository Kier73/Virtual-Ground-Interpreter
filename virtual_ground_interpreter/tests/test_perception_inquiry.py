import unittest

from vgi.inquiry import inquire_unresolved_pairs
from vgi.relational import ObserverContext
from vgi.transitions import GroundTransitionSystem, TransitionObservation, TransitionOutcome


def complementary_ground():
    rows = (
        TransitionObservation("p0", "A", (TransitionOutcome("p0", (0, 0)),)),
        TransitionObservation("p1", "A", (TransitionOutcome("p1", (0, 0)),)),
        TransitionObservation("p0", "B", (TransitionOutcome("p0", (0, 0)),)),
        TransitionObservation("p1", "B", (TransitionOutcome("p1", (0, 1)),)),
    )
    return GroundTransitionSystem(("p0", "p1"), ("A", "B"), "p0", ("x", "y"), rows)


def delayed_witness_ground():
    rows = (
        TransitionObservation("p0", "A", (TransitionOutcome("p2", (0,)),)),
        TransitionObservation("p1", "A", (TransitionOutcome("p1", (0,)),)),
        TransitionObservation("p2", "A", (TransitionOutcome("p2", (1,)),)),
    )
    return GroundTransitionSystem(("p0", "p1", "p2"), ("A",), "p0", ("y",), rows)


def partially_known_ground():
    rows = (
        TransitionObservation("u0", "A", (TransitionOutcome("u0", (0,)),)),
        TransitionObservation("u1", "A", (TransitionOutcome("u1", (0,)),)),
    )
    return GroundTransitionSystem(("u0", "u1"), ("A", "B"), "u0", ("y",), rows)


def ambiguous_ground():
    rows = (
        TransitionObservation("u0", "A", (TransitionOutcome("u0", (0,)),)),
        TransitionObservation("u1", "A", (TransitionOutcome("u1", (0,)),)),
        TransitionObservation("u0", "B", (
            TransitionOutcome("u0", (0,)), TransitionOutcome("u1", (1,)),
        ), support_count=2),
        TransitionObservation("u1", "B", (TransitionOutcome("u1", (0,)),)),
    )
    return GroundTransitionSystem(("u0", "u1"), ("A", "B"), "u0", ("y",), rows)


def equivalent_ground():
    rows = (
        TransitionObservation("e0", "A", (TransitionOutcome("e0", (0,)),)),
        TransitionObservation("e1", "A", (TransitionOutcome("e1", (0,)),)),
    )
    return GroundTransitionSystem(("e0", "e1"), ("A",), "e0", ("y",), rows)


class PerceptionInquiryTests(unittest.TestCase):
    def test_finds_shortest_distinction_outside_current_projection(self):
        ground = complementary_ground()
        observer = ObserverContext("current-view", ("A",), ("x",))
        report = inquire_unresolved_pairs(ground, observer, horizon=1)
        self.assertEqual(report.unresolved_pair_count, 1)
        item = report.inquiries[0]
        self.assertEqual(item.conclusion, "witness_found")
        witness = item.witness
        self.assertEqual(witness.action_word, ("B",))
        self.assertEqual(witness.differing_channels, ("y",))
        self.assertEqual(witness.left_output, (0, 0))
        self.assertEqual(witness.right_output, (0, 1))
        self.assertEqual(witness.newly_required_actions, ("B",))
        self.assertEqual(witness.newly_required_channels, ("y",))
        self.assertTrue(witness.requires_observer_extension)
        self.assertTrue(report.boundary.is_open)

    def test_finds_a_temporally_delayed_counterexample(self):
        ground = delayed_witness_ground()
        observer = ObserverContext("short-view", ("A",), ("y",))
        bounded = inquire_unresolved_pairs(ground, observer, 1, search_horizon=1)
        item = next(x for x in bounded.inquiries
                    if (x.left_state, x.right_state) == ("p0", "p1"))
        self.assertEqual(item.conclusion, "no_witness_within_horizon")
        self.assertTrue(item.horizon_bound_reached)
        extended = inquire_unresolved_pairs(ground, observer, 1, search_horizon=2)
        item = next(x for x in extended.inquiries
                    if (x.left_state, x.right_state) == ("p0", "p1"))
        self.assertEqual(item.conclusion, "witness_found")
        self.assertEqual(item.witness.action_word, ("A", "A"))
        self.assertFalse(item.witness.requires_observer_extension)

    def test_missing_transitions_remain_inconclusive(self):
        ground = partially_known_ground()
        observer = ObserverContext("A-only", ("A",), ("y",))
        report = inquire_unresolved_pairs(ground, observer, 1)
        item = report.inquiries[0]
        self.assertEqual(item.conclusion, "inconclusive_missing_evidence")
        self.assertIsNone(item.witness)
        self.assertEqual(
            {(x.state, x.action, x.status) for x in item.blocked_transitions},
            {("u0", "B", "unknown"), ("u1", "B", "unknown")},
        )
        self.assertEqual(len(report.boundary.unknown_transition_cells), 2)

    def test_ambiguous_transitions_are_not_promoted_to_witnesses(self):
        ground = ambiguous_ground()
        observer = ObserverContext("A-only", ("A",), ("y",))
        report = inquire_unresolved_pairs(ground, observer, 1)
        item = report.inquiries[0]
        self.assertEqual(item.conclusion, "inconclusive_missing_evidence")
        self.assertIn(
            ("u0", "B", "ambiguous"),
            {(x.state, x.action, x.status) for x in item.blocked_transitions},
        )
        self.assertEqual(report.boundary.ambiguous_transition_cells, (("u0", "B"),))

    def test_equivalence_is_scoped_to_a_complete_declared_ground(self):
        ground = equivalent_ground()
        observer = ObserverContext.full(ground)
        report = inquire_unresolved_pairs(ground, observer, 1)
        item = report.inquiries[0]
        self.assertEqual(item.conclusion, "equivalent_over_declared_ground")
        self.assertTrue(report.boundary.declared_transition_system_complete)
        self.assertTrue(report.boundary.is_open)
        self.assertEqual(report.boundary.outside_declared_scope, "open_unenumerated")


if __name__ == "__main__":
    unittest.main()
