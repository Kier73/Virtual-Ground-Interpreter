import itertools
import json
from pathlib import Path
import unittest

from vgi.transitions import (
    AmbiguousTransitionError, GroundTransitionSystem, TransitionCompiler,
    TransitionCompileError, TransitionObservation, TransitionOutcome,
    UnknownTransitionError, differential_verify,
)

ROOT = Path(__file__).resolve().parents[1]


def delayed_six():
    data = json.loads((ROOT / "examples" / "delayed_six_predictive_ground.json").read_text(encoding="utf-8"))
    return GroundTransitionSystem.from_predictive_mealy_dict(data)


class GroundTransitionSystemTests(unittest.TestCase):
    def setUp(self):
        self.ground = delayed_six()

    def test_build24_fixture_imports_as_complete_predictive_ground(self):
        self.assertEqual(self.ground.states, ("q0", "q1", "q2", "q3", "q4", "q5"))
        self.assertEqual(self.ground.actions, ("HOLD", "PROBE_A", "PROBE_B"))
        self.assertTrue(self.ground.complete)
        self.assertEqual(len(self.ground.observations), 18)
        self.assertEqual(self.ground.status("q5", "PROBE_A"), "known")

    def test_delayed_distinction_is_preserved_at_the_sixth_event(self):
        prefix = self.ground.run(("HOLD",) * 5)
        self.assertEqual(prefix.final_state, "q5")
        self.assertEqual(prefix.outputs, ((0,),) * 5)
        full = self.ground.run(("HOLD",) * 5 + ("PROBE_A",))
        self.assertEqual(full.final_state, "q0")
        self.assertEqual(full.outputs, ((0,),) * 5 + ((1,),))
        self.assertEqual(full.state_trace, ("q1", "q2", "q3", "q4", "q5", "q0"))

    def test_absent_edges_remain_unknown(self):
        partial = GroundTransitionSystem(
            states=("p0", "p1"), actions=("A", "B"), initial_state="p0",
            channels=("y",),
            observations=(TransitionObservation("p0", "A", (TransitionOutcome("p1", (0,)),)),),
        )
        self.assertEqual(partial.status("p0", "B"), "unknown")
        with self.assertRaises(UnknownTransitionError):
            partial.step("p0", "B")
        with self.assertRaises(TransitionCompileError):
            TransitionCompiler().compile(partial, 1)

    def test_conflicting_outcomes_remain_ambiguous(self):
        ambiguous = GroundTransitionSystem(
            states=("p0", "p1"), actions=("A",), initial_state="p0",
            channels=("y",),
            observations=(TransitionObservation(
                "p0", "A",
                (TransitionOutcome("p1", (0,)), TransitionOutcome("p0", (1,))),
                support_count=2, evidence=("observation-1", "observation-2"),
            ),),
        )
        self.assertEqual(ambiguous.status("p0", "A"), "ambiguous")
        with self.assertRaises(AmbiguousTransitionError):
            ambiguous.step("p0", "A")
        with self.assertRaises(TransitionCompileError):
            TransitionCompiler().compile(ambiguous, 1)

    def test_json_round_trip_preserves_fingerprint_and_unknowns(self):
        round_trip = GroundTransitionSystem.from_json(self.ground.to_json())
        self.assertEqual(round_trip.fingerprint, self.ground.fingerprint)
        self.assertEqual(round_trip.to_dict(), self.ground.to_dict())

    def test_signal8_compiler_rejects_domains_outside_its_finite_embedding(self):
        states = tuple(f"s{i}" for i in range(9))
        observations = tuple(
            TransitionObservation(source, "A", (TransitionOutcome(states[(i + 1) % 9], (0,)),))
            for i, source in enumerate(states)
        )
        too_large = GroundTransitionSystem(
            states=states, actions=("A",), initial_state="s0", channels=("y",),
            observations=observations,
        )
        with self.assertRaises(TransitionCompileError):
            TransitionCompiler().compile(too_large, 1)


class DifferentialCompilationTests(unittest.TestCase):
    def setUp(self):
        self.ground = delayed_six()

    def test_compiled_vgi_path_matches_delayed_six_reference(self):
        actions = ("HOLD",) * 5 + ("PROBE_A",)
        direct = self.ground.run(actions)
        compiled_program = TransitionCompiler().compile(self.ground, len(actions))
        realized = compiled_program.execute(actions)
        self.assertEqual(realized.state_trace, direct.state_trace)
        self.assertEqual(realized.outputs, direct.outputs)
        self.assertEqual(realized.final_state, direct.final_state)
        self.assertEqual(realized.system_fingerprint, self.ground.fingerprint)

    def test_compiled_program_accepts_different_action_words_of_same_length(self):
        program = TransitionCompiler().compile(self.ground, 3)
        for actions in itertools.product(self.ground.actions, repeat=3):
            direct = self.ground.run(actions)
            realized = program.execute(actions)
            self.assertEqual(realized.state_trace, direct.state_trace)
            self.assertEqual(realized.outputs, direct.outputs)
            self.assertEqual(realized.final_state, direct.final_state)

    def test_differential_verification_report(self):
        sequences = [tuple(word) for word in itertools.product(self.ground.actions, repeat=2)]
        sequences.append(("HOLD",) * 5 + ("PROBE_A",))
        report = differential_verify(self.ground, sequences)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["cases_checked"], 10)
        self.assertEqual(report["errors"], [])


if __name__ == "__main__":
    unittest.main()
