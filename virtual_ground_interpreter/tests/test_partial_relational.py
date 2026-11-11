import json
from pathlib import Path
import unittest

from vgi.relational import (
    ObserverContext,
    RelationalError,
    contextual_quotient,
    partial_contextual_comparison,
    partial_refinement_series,
    refinement_series,
)
from vgi.transitions import (
    GroundTransitionSystem,
    TransitionObservation,
    TransitionOutcome,
)


ROOT = Path(__file__).resolve().parents[1]


def delayed_six():
    data = json.loads(
        (ROOT / "examples" / "delayed_six_predictive_ground.json").read_text(encoding="utf-8")
    )
    return GroundTransitionSystem.from_predictive_mealy_dict(data)


def partial_cycle():
    return GroundTransitionSystem(
        states=("p0", "p1"),
        actions=("A", "B"),
        initial_state="p0",
        channels=("y",),
        observations=(
            TransitionObservation("p0", "A", (TransitionOutcome("p1", (0,)),)),
            TransitionObservation("p1", "A", (TransitionOutcome("p0", (0,)),)),
        ),
    )


class PartialRelationalTests(unittest.TestCase):
    def test_delayed_six_distinction_arrives_at_exact_bounded_horizon(self):
        ground = delayed_six()
        observer = ObserverContext.full(ground, "all-actions")
        series = partial_refinement_series(ground, observer, 6)

        self.assertEqual(series[4].status("q0", "q1"), "equivalent")
        self.assertEqual(series[5].status("q0", "q1"), "distinguishable")
        self.assertEqual(
            series[5].witness("q0", "q1"),
            ("HOLD", "HOLD", "HOLD", "HOLD", "PROBE_A"),
        )
        self.assertEqual(series[5].witness("q1", "q0"), series[5].witness("q0", "q1"))
        self.assertEqual(series[5].status("q0", "q0"), "equivalent")

    def test_observer_profile_can_hide_or_reveal_a_delayed_distinction(self):
        ground = delayed_six()
        routine = ObserverContext("routine-only", ("HOLD", "PROBE_B"), ("channel_0",))
        focused = ObserverContext("target-probe", ("PROBE_A",), ("channel_0",))
        routine_comparison = partial_contextual_comparison(ground, routine, 8)
        focused_comparison = partial_contextual_comparison(ground, focused, 1)
        self.assertEqual(routine_comparison.status("q0", "q5"), "equivalent")
        self.assertEqual(focused_comparison.status("q0", "q5"), "distinguishable")
        self.assertEqual(focused_comparison.witness("q0", "q5"), ("PROBE_A",))

    def test_partial_cycle_does_not_turn_unknown_actions_into_equivalence(self):
        ground = partial_cycle()
        full_observer = ObserverContext("A-and-B", ("A", "B"), ("y",))
        series = partial_refinement_series(ground, full_observer, 4)
        for comparison in series[1:]:
            self.assertEqual(comparison.status("p0", "p1"), "unresolved")
        self.assertEqual(series[1].blocked("p0", "p1"), ("B",))
        self.assertEqual(
            series[1].blockers("p0", "p1")[0].reason,
            "missing_edge",
        )
        self.assertEqual(series[2].blocked("p0", "p1"), ("A", "B"))
        self.assertEqual(
            [(item.action, item.reason) for item in series[2].blockers("p0", "p1")],
            [("A", "unresolved_successor"), ("B", "missing_edge")],
        )

        observed_only = ObserverContext("A-only", ("A",), ("y",))
        bounded = partial_contextual_comparison(ground, observed_only, 4)
        self.assertEqual(bounded.status("p0", "p1"), "equivalent")

    def test_known_counterexample_proves_distinguishability_despite_other_unknowns(self):
        ground = GroundTransitionSystem(
            states=("left", "right"),
            actions=("A", "B"),
            initial_state="left",
            channels=("y",),
            observations=(
                TransitionObservation("left", "A", (TransitionOutcome("left", (0,)),)),
                TransitionObservation("right", "A", (TransitionOutcome("right", (1,)),)),
            ),
        )
        observer = ObserverContext("A-and-B", ("A", "B"), ("y",))
        comparison = partial_contextual_comparison(ground, observer, 1)
        self.assertEqual(comparison.status("left", "right"), "distinguishable")
        self.assertEqual(comparison.witness("left", "right"), ("A",))

    def test_new_evidence_can_resolve_without_rewriting_the_old_comparison(self):
        observer = ObserverContext("A-and-B", ("A", "B"), ("y",))
        before = partial_contextual_comparison(partial_cycle(), observer, 2)
        self.assertEqual(before.status("p0", "p1"), "unresolved")

        equivalent_ground = GroundTransitionSystem(
            states=("p0", "p1"),
            actions=("A", "B"),
            initial_state="p0",
            channels=("y",),
            observations=(
                TransitionObservation("p0", "A", (TransitionOutcome("p1", (0,)),)),
                TransitionObservation("p1", "A", (TransitionOutcome("p0", (0,)),)),
                TransitionObservation("p0", "B", (TransitionOutcome("p0", (1,)),)),
                TransitionObservation("p1", "B", (TransitionOutcome("p1", (1,)),)),
            ),
        )
        distinguishable_ground = GroundTransitionSystem(
            states=("p0", "p1"),
            actions=("A", "B"),
            initial_state="p0",
            channels=("y",),
            observations=(
                TransitionObservation("p0", "A", (TransitionOutcome("p1", (0,)),)),
                TransitionObservation("p1", "A", (TransitionOutcome("p0", (0,)),)),
                TransitionObservation("p0", "B", (TransitionOutcome("p0", (0,)),)),
                TransitionObservation("p1", "B", (TransitionOutcome("p1", (1,)),)),
            ),
        )
        now_equivalent = partial_contextual_comparison(equivalent_ground, observer, 1)
        now_distinguishable = partial_contextual_comparison(distinguishable_ground, observer, 1)
        self.assertEqual(now_equivalent.status("p0", "p1"), "equivalent")
        self.assertEqual(now_distinguishable.status("p0", "p1"), "distinguishable")
        self.assertEqual(now_distinguishable.witness("p0", "p1"), ("B",))
        self.assertEqual(before.status("p0", "p1"), "unresolved")

    def test_ambiguous_edge_is_unresolved_not_a_guessed_distinction(self):
        ground = GroundTransitionSystem(
            states=("p0", "p1"),
            actions=("A",),
            initial_state="p0",
            channels=("y",),
            observations=(
                TransitionObservation(
                    "p0",
                    "A",
                    (
                        TransitionOutcome("p0", (0,)),
                        TransitionOutcome("p1", (1,)),
                    ),
                    support_count=2,
                    evidence=("encounter-a", "encounter-b"),
                ),
                TransitionObservation("p1", "A", (TransitionOutcome("p1", (0,)),)),
            ),
        )
        observer = ObserverContext("A", ("A",), ("y",))
        comparison = partial_contextual_comparison(ground, observer, 2)
        self.assertEqual(comparison.status("p0", "p1"), "unresolved")
        self.assertIsNone(comparison.witness("p0", "p1"))
        self.assertEqual(comparison.blocked("p0", "p1"), ("A",))
        self.assertEqual(comparison.blockers("p0", "p1")[0].reason, "ambiguous_edge")
        self.assertEqual(comparison.blockers("p0", "p1")[0].left_edge_status, "ambiguous")
        self.assertEqual(comparison.blockers("p0", "p1")[0].right_edge_status, "known")

    def test_shortest_witness_is_composed_from_the_previous_horizon(self):
        ground = GroundTransitionSystem(
            states=("p0", "p1", "p2", "p3"),
            actions=("A",),
            initial_state="p0",
            channels=("y",),
            observations=(
                TransitionObservation("p0", "A", (TransitionOutcome("p1", (0,)),)),
                TransitionObservation("p2", "A", (TransitionOutcome("p3", (0,)),)),
                TransitionObservation("p1", "A", (TransitionOutcome("p1", (0,)),)),
                TransitionObservation("p3", "A", (TransitionOutcome("p3", (1,)),)),
            ),
        )
        observer = ObserverContext("single-probe", ("A",), ("y",))
        series = partial_refinement_series(ground, observer, 2)
        self.assertEqual(series[1].status("p0", "p2"), "equivalent")
        self.assertEqual(series[2].status("p0", "p2"), "distinguishable")
        self.assertEqual(series[2].witness("p0", "p2"), ("A", "A"))

    def test_partial_refinement_is_monotone_in_knowledge(self):
        fixtures = (
            (
                partial_cycle(),
                ObserverContext("A-and-B", ("A", "B"), ("y",)),
                6,
            ),
            (
                delayed_six(),
                ObserverContext.full(delayed_six(), "all-actions"),
                6,
            ),
        )
        order = {"equivalent": 0, "unresolved": 1, "distinguishable": 2}
        for ground, observer, horizon in fixtures:
            series = partial_refinement_series(ground, observer, horizon)
            for previous, current in zip(series, series[1:]):
                for left in ground.states:
                    for right in ground.states:
                        self.assertGreaterEqual(
                            order[current.status(left, right)],
                            order[previous.status(left, right)],
                        )

    def test_complete_ground_partial_comparison_matches_exact_quotient(self):
        ground = delayed_six()
        observer = ObserverContext.full(ground, "all-actions")
        partial = partial_refinement_series(ground, observer, 5)
        exact = refinement_series(ground, observer, 5)
        for horizon, (partial_item, exact_item) in enumerate(zip(partial, exact)):
            self.assertEqual(partial_item.horizon, horizon)
            for left in ground.states:
                for right in ground.states:
                    expected = (
                        "equivalent" if exact_item.equivalent(left, right)
                        else "distinguishable"
                    )
                    self.assertEqual(partial_item.status(left, right), expected)

    def test_channel_selection_changes_only_the_observed_relation(self):
        ground = GroundTransitionSystem(
            states=("left", "right"),
            actions=("STEP",),
            initial_state="left",
            channels=("coarse", "detail"),
            observations=(
                TransitionObservation("left", "STEP", (TransitionOutcome("left", (0, 0)),)),
                TransitionObservation("right", "STEP", (TransitionOutcome("right", (0, 1)),)),
            ),
        )
        coarse = ObserverContext("coarse-only", ("STEP",), ("coarse",))
        detailed = ObserverContext("detail-only", ("STEP",), ("detail",))
        self.assertEqual(partial_contextual_comparison(ground, coarse, 1).status("left", "right"),
                         "equivalent")
        self.assertEqual(partial_contextual_comparison(ground, detailed, 1).status("left", "right"),
                         "distinguishable")

    def test_partial_comparison_json_preserves_unresolved_blockers_and_witnesses(self):
        ground = delayed_six()
        observer = ObserverContext.full(ground, "all-actions")
        comparison = partial_contextual_comparison(ground, observer, 5)
        payload = comparison.to_dict()
        self.assertEqual(payload["format"], "VGI-PartialContextualComparison-1")
        row = next(
            item for item in payload["pairs"]
            if item["left"] == "q0" and item["right"] == "q1"
        )
        self.assertEqual(row["status"], "distinguishable")
        self.assertEqual(
            row["witness"],
            ["HOLD", "HOLD", "HOLD", "HOLD", "PROBE_A"],
        )

        partial = partial_contextual_comparison(
            partial_cycle(),
            ObserverContext("A-and-B", ("A", "B"), ("y",)),
            1,
        )
        partial_payload = partial.to_dict()
        partial_row = next(
            item for item in partial_payload["pairs"]
            if item["left"] == "p0" and item["right"] == "p1"
        )
        self.assertEqual(partial_row["status"], "unresolved")
        self.assertEqual(partial_row["blockers"], [{
            "action": "B",
            "left_edge_status": "unknown",
            "right_edge_status": "unknown",
            "successor_status": None,
            "reason": "missing_edge",
        }])

    def test_unknown_horizon_and_observer_validation_remain_explicit(self):
        ground = partial_cycle()
        with self.assertRaises(RelationalError):
            partial_refinement_series(
                ground, ObserverContext("bad", ("missing",), ("y",)), 1
            )
        with self.assertRaises(RelationalError):
            partial_refinement_series(ground, ObserverContext("ok", ("A",), ("y",)), -1)


if __name__ == "__main__":
    unittest.main()
