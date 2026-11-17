"""Differential and adversarial checks for wider finite Ground identities."""
from dataclasses import replace
import unittest

from vgi import Signal8Backend, VirtualGroundInterpreter
from vgi.machine import AmbiguousBranchError, StepLimitExceeded
from vgi.evidence import EvidenceError, GroundReconstructionVerifier
from vgi.transitions import (
    GroundTransitionSystem, TransitionCompiler, TransitionExecutionError,
    TransitionObservation, TransitionOutcome,
)


def table(states=9, actions=9, initial=0):
    return GroundTransitionSystem(
        states=tuple(f"s{i}" for i in range(states)),
        actions=tuple(f"a{j}" for j in range(actions)),
        initial_state=f"s{initial}", channels=("sum", "source"),
        observations=tuple(
            TransitionObservation(f"s{i}", f"a{j}", (
                TransitionOutcome(f"s{(i+j+1) % states}", ((i+j) % 8, i % 8)),
            )) for i in range(states) for j in range(actions)
        ),
    )


class MultiDigitTransitions(unittest.TestCase):
    def assert_matches(self, ground, word, **kwargs):
        direct = ground.run(word)
        compiled = TransitionCompiler().compile(ground, len(word))
        actual = compiled.execute(word, **kwargs)
        self.assertEqual(actual.state_trace, direct.state_trace)
        self.assertEqual(actual.outputs, direct.outputs)
        self.assertEqual(actual.final_state, direct.final_state)
        return compiled

    def test_every_edge_of_nine_state_nine_action_ground(self):
        # Distinguishes indices 0 and 8 in BOTH alphabets: modulo-eight
        # truncation or checking only the low digit cannot pass this corpus.
        for initial in range(9):
            ground = table(initial=initial)
            for action in ground.actions:
                with self.subTest(initial=initial, action=action):
                    self.assert_matches(ground, (action,))

    def test_cross_digit_carries_and_three_digit_states(self):
        for size, initial, count in ((8, 7, 2), (9, 7, 3), (64, 63, 2), (65, 63, 3)):
            ground = table(size, 1, initial)
            self.assert_matches(ground, ("a0",) * count)

    def test_three_digit_action_and_independent_widths(self):
        ground = table(2, 65, 1)
        self.assert_matches(ground, ("a0", "a8", "a63", "a64"))

    def test_zero_actions_preserves_wide_initial_identity(self):
        compiled = self.assert_matches(table(65, 1, 64), ())
        self.assertEqual(compiled.program.metadata["source"], "vgi.transition-compiler.v2")

    def test_width_one_retains_v1_interface(self):
        compiled = self.assert_matches(table(8, 8), ("a7",))
        self.assertIn("state", compiled.initial_memory)
        self.assertFalse(any(".digit." in key for key in compiled.initial_memory))
        self.assertEqual(compiled.program.metadata["source"], "vgi.transition-compiler.v1")

    def test_reconstruction_certificates_bind_lowering_version_and_context(self):
        verifier = GroundReconstructionVerifier()
        for size, version in ((8, 1), (9, 2)):
            ground = table(size, 1, size - 1)
            certificate = verifier.certify(ground, ((), ("a0",)), context_digest="a" * 64)
            self.assertEqual(certificate.compiler_version, version)
            self.assertTrue(verifier.verify(ground, certificate, context_digest="a" * 64))
            with self.assertRaises(EvidenceError):
                verifier.verify(ground, replace(certificate, compiler_version=3-version),
                                context_digest="a" * 64)
            with self.assertRaises(EvidenceError):
                verifier.verify(ground, certificate, context_digest="b" * 64)

    def test_observer_reframing_preserves_each_digit(self):
        ground = table(9, 9, 8)
        compiled = TransitionCompiler().compile(ground, 2)
        backend = Signal8Backend()
        memory = {key: backend.reframe(value, 3)
                  for key, value in compiled.initial_memory.items()}
        compiled = replace(compiled, initial_memory=memory)
        result = compiled.execute(("a8", "a7"))
        self.assertEqual(result.state_trace, ground.run(("a8", "a7")).state_trace)

    def test_unused_state_encoding_refuses_instead_of_aliasing(self):
        compiled = TransitionCompiler().compile(table(), 1)
        memory = dict(compiled.initial_memory)
        memory["state.digit.1"] = Signal8Backend().encode_symbol(7)
        with self.assertRaises(TransitionExecutionError):
            replace(compiled, initial_memory=memory).execute(("a0",))

    def test_uncertain_high_digit_traps_before_transition_writes(self):
        compiled = TransitionCompiler().compile(table(), 1)
        memory = dict(compiled.initial_memory)
        memory["state.digit.1"] = Signal8Backend().encode_symbol(0, phase_error_bound=0.1)
        with self.assertRaises(AmbiguousBranchError):
            replace(compiled, initial_memory=memory).execute(("a0",))
        self.assertEqual(memory["state.digit.1"].phase_error_bound, 0.1)

    def test_unused_action_encoding_refuses_instead_of_aliasing(self):
        class CorruptedIngress(VirtualGroundInterpreter):
            def execute(self, program, initial_memory=None, **kwargs):
                memory = dict(initial_memory)
                memory["input.action.0.digit.1"] = self.backend.encode_symbol(7)
                return super().execute(program, memory, **kwargs)

        compiled = TransitionCompiler().compile(table(), 1)
        with self.assertRaises(TransitionExecutionError):
            compiled.execute(("a0",), interpreter=CorruptedIngress())

    def test_unused_final_encoding_refuses_even_for_empty_word(self):
        compiled = TransitionCompiler().compile(table(), 0)
        memory = dict(compiled.initial_memory)
        memory["state.digit.1"] = Signal8Backend().encode_symbol(7)
        with self.assertRaises(TransitionExecutionError):
            replace(compiled, initial_memory=memory).execute(())

    def test_execution_budget_and_unknown_action_still_refuse(self):
        compiled = TransitionCompiler().compile(table(), 1)
        with self.assertRaises(StepLimitExceeded):
            compiled.execute(("a8",), max_steps=1)
        with self.assertRaises(TransitionExecutionError):
            compiled.execute(("outside",))


if __name__ == "__main__":
    unittest.main()
