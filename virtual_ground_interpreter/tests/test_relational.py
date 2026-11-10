import json
from pathlib import Path
import unittest

from vgi.relational import (
    ObserverContext, RelationalError, behavioral_distance, contextual_quotient,
    quotient_map, quotient_transition_table, refinement_series,
)
from vgi.transitions import (
    AmbiguousTransitionError, GroundTransitionSystem, TransitionObservation,
    TransitionOutcome, UnknownTransitionError,
)

ROOT = Path(__file__).resolve().parents[1]


def delayed_six():
    data = json.loads(
        (ROOT / "examples" / "delayed_six_predictive_ground.json").read_text(encoding="utf-8")
    )
    return GroundTransitionSystem.from_predictive_mealy_dict(data)


def cyclic_recurrence():
    states = ("c0", "c1", "c2", "c3")
    observations = tuple(
        TransitionObservation(
            state, "STEP",
            (TransitionOutcome(states[(index + 1) % len(states)], (index,)),),
        )
        for index, state in enumerate(states)
    )
    return GroundTransitionSystem(
        states, ("STEP",), "c0", ("phase",), observations,
        {"family": "cyclic recurrence", "modulus": 4},
    )


def non_bijective_automaton():
    states = ("left", "right", "sink")
    detail = {"left": 0, "right": 1, "sink": 2}
    observations = tuple(
        TransitionObservation(
            state, "ERASE",
            (TransitionOutcome("sink", (0, detail[state])),),
        )
        for state in states
    )
    return GroundTransitionSystem(
        states, ("ERASE",), "left", ("coarse", "detail"), observations,
        {"family": "non-bijective automaton"},
    )


class RelationalAtlasTests(unittest.TestCase):
    def setUp(self):
        self.ground = delayed_six()
        self.full = ObserverContext.full(self.ground, "available")

    def test_delayed_six_refines_at_the_first_distinguishing_horizon(self):
        series = refinement_series(self.ground, self.full, 8)
        counts = [item.class_count for item in series]
        self.assertEqual(counts, [1, 2, 3, 4, 5, 6])
        self.assertTrue(series[-1].stable)
        h4, h5 = series[4], series[5]
        self.assertTrue(h4.equivalent("q0", "q1"))
        self.assertFalse(h5.equivalent("q0", "q1"))
        self.assertEqual(h5.classes, tuple((state,) for state in self.ground.states))

    def test_attention_profile_can_hide_a_real_distinction(self):
        restricted = ObserverContext("routine-only", ("HOLD", "PROBE_B"), ("channel_0",))
        series = refinement_series(self.ground, restricted, 12)
        self.assertEqual([item.class_count for item in series], [1, 1])
        self.assertTrue(series[-1].stable)
        self.assertTrue(series[-1].equivalent("q0", "q5"))

        focused = ObserverContext("target-probe", ("PROBE_A",), ("channel_0",))
        focused_quotient = contextual_quotient(self.ground, focused, 1)
        self.assertFalse(focused_quotient.equivalent("q0", "q5"))

    def test_quotient_maps_and_layered_transition_table_are_well_defined(self):
        series = refinement_series(self.ground, self.full, 5)
        finer, coarser = series[4], series[3]
        projection = quotient_map(finer, coarser)
        self.assertEqual(len(projection), finer.class_count)
        self.assertEqual(projection[finer.state_to_class["q0"]],
                         projection[finer.state_to_class["q1"]])

        table = quotient_transition_table(self.ground, finer, coarser)
        self.assertEqual(len(table), finer.class_count * len(self.full.actions))
        by_key = {(edge.source_class, edge.action): edge for edge in table}
        q01_class = finer.state_to_class["q0"]
        edge = by_key[(q01_class, "PROBE_A")]
        self.assertEqual(edge.target_class, coarser.state_to_class["q1"])
        self.assertEqual(edge.output, (0,))

    def test_behavioral_distance_agrees_with_bounded_equivalence(self):
        close = behavioral_distance(self.ground, self.full, "q0", "q1", 4)
        separated = behavioral_distance(self.ground, self.full, "q0", "q1", 5)
        self.assertAlmostEqual(close, 0.0)
        self.assertGreater(separated, 0.0)
        self.assertLessEqual(separated, 1.0)

        no_probe_weight = behavioral_distance(
            self.ground, self.full, "q0", "q1", 5,
            action_weights={"HOLD": 1.0, "PROBE_A": 0.0, "PROBE_B": 1.0},
        )
        self.assertAlmostEqual(no_probe_weight, 0.0)

    def test_behavioral_distance_is_a_pseudometric_on_the_finite_fixture(self):
        ground = non_bijective_automaton()
        observer = ObserverContext("detail", ("ERASE",), ("detail",))
        states = ground.states
        for a in states:
            self.assertAlmostEqual(behavioral_distance(ground, observer, a, a, 3), 0.0)
            for b in states:
                ab = behavioral_distance(ground, observer, a, b, 3)
                ba = behavioral_distance(ground, observer, b, a, 3)
                self.assertAlmostEqual(ab, ba)
                for c in states:
                    ac = behavioral_distance(ground, observer, a, c, 3)
                    bc = behavioral_distance(ground, observer, b, c, 3)
                    self.assertLessEqual(ac, ab + bc + 1e-12)

    def test_non_bijective_map_has_observer_dependent_quotients(self):
        ground = non_bijective_automaton()
        coarse = ObserverContext("coarse", ("ERASE",), ("coarse",))
        detail = ObserverContext("detail", ("ERASE",), ("detail",))
        coarse_q = contextual_quotient(ground, coarse, 1)
        detail_q = contextual_quotient(ground, detail, 1)
        self.assertEqual(coarse_q.class_count, 1)
        self.assertEqual(detail_q.class_count, 3)
        self.assertTrue(coarse_q.equivalent("left", "right"))
        self.assertFalse(detail_q.equivalent("left", "right"))

    def test_cyclic_recurrence_depends_on_the_observed_channel(self):
        ground = cyclic_recurrence()
        blind = ObserverContext("no-phase-channel", ("STEP",), ())
        phase = ObserverContext("phase-channel", ("STEP",), ("phase",))
        blind_q = contextual_quotient(ground, blind, 5)
        phase_q = contextual_quotient(ground, phase, 1)
        self.assertEqual(blind_q.class_count, 1)
        self.assertEqual(phase_q.class_count, 4)

    def test_unknown_and_ambiguous_selected_edges_are_not_filled_in(self):
        partial = GroundTransitionSystem(
            ("p0", "p1"), ("A", "B"), "p0", ("y",),
            (
                TransitionObservation("p0", "A", (TransitionOutcome("p1", (0,)),)),
                TransitionObservation("p1", "A", (TransitionOutcome("p0", (0,)),)),
            ),
        )
        observed = ObserverContext("A-only", ("A",), ("y",))
        # The observer need not request the unknown B edge.
        self.assertEqual(contextual_quotient(partial, observed, 1).class_count, 1)
        missing = ObserverContext("B", ("B",), ("y",))
        with self.assertRaises(UnknownTransitionError):
            contextual_quotient(partial, missing, 1)

        ambiguous = GroundTransitionSystem(
            ("p0", "p1"), ("A",), "p0", ("y",),
            (TransitionObservation(
                "p0", "A",
                (TransitionOutcome("p0", (0,)), TransitionOutcome("p1", (1,))),
                support_count=2,
            ),),
        )
        with self.assertRaises(AmbiguousTransitionError):
            contextual_quotient(
                ambiguous, ObserverContext("ambiguous", ("A",), ("y",)), 1
            )

    def test_incompatible_quotient_contexts_cannot_be_mapped(self):
        left = contextual_quotient(self.ground, self.full, 3)
        right_context = ObserverContext("without-A", ("HOLD", "PROBE_B"), ("channel_0",))
        right = contextual_quotient(self.ground, right_context, 2)
        with self.assertRaises(RelationalError):
            quotient_map(left, right)


if __name__ == "__main__":
    unittest.main()
