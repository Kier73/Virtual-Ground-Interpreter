import math
import unittest
from unittest.mock import patch

from vgi import (
    Instruction,
    Program,
    Signal8Backend,
    Signal8ExecutionAdapter,
    SignalValue,
    SignalStateMachine,
    VirtualGroundInterpreter,
    verify_execution_reference,
)


def add_program():
    return Program("reference-add", (
        Instruction("LOAD", {"dst": "a", "address": "a"}),
        Instruction("LOAD", {"dst": "b", "address": "b"}),
        Instruction("ADD", {"dst": "sum", "left": "a", "right": "b"}),
        Instruction("EMIT", {"src": "sum", "label": "sum"}),
        Instruction("HALT"),
    ))


def branch_program(tolerance):
    return Program("reference-branch", (
        Instruction("LOAD", {"dst": "a", "address": "a"}),
        Instruction("LOAD", {"dst": "b", "address": "b"}),
        Instruction("BRANCH_EQ", {
            "left": "a", "right": "b", "target": 5,
            "tolerance_rad": tolerance,
        }),
        Instruction("MOVE", {"dst": "choice", "src": "a"}),
        Instruction("JUMP", {"target": 6}),
        Instruction("MOVE", {"dst": "choice", "src": "b"}),
        Instruction("EMIT", {"src": "choice", "label": "choice"}),
        Instruction("HALT"),
    ))


class IndependentSignal8ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.backend = Signal8Backend()
        self.interpreter = VirtualGroundInterpreter(backend=self.backend)
        self.adapter = Signal8ExecutionAdapter(self.interpreter)

    def capture_add(self, observer_a=1, observer_b=3, a=3, b=5, trace_id="ref-add"):
        return self.adapter.capture(
            add_program(),
            {
                "a": self.backend.encode_symbol(a, observer=observer_a),
                "b": self.backend.encode_symbol(b, observer=observer_b),
            },
            trace_id=trace_id,
        )

    def test_independent_reference_matches_mixed_observer_addition(self):
        trace = self.capture_add()
        report = verify_execution_reference(trace)
        self.assertEqual(report.status, "match")
        self.assertEqual(report.checked_steps, 5)
        self.assertEqual(report.checked_writes, 4)
        self.assertEqual(report.decoded_inputs, 2)
        self.assertEqual(report.trace_fingerprint, trace.fingerprint)
        self.assertEqual(report.program_fingerprint, trace.program_fingerprint)
        self.assertEqual(report.ground_fingerprint, trace.ground_fingerprint)
        self.assertEqual(report.numerical_tolerance_rad, 1e-8)
        self.assertEqual(len(report.fingerprint), 64)

    def test_reference_does_not_call_runtime_machine_or_algebra(self):
        trace = self.capture_add(trace_id="reference-isolated")
        with (
            patch.object(self.backend, "add", side_effect=AssertionError("runtime ADD called")),
            patch.object(SignalStateMachine, "step", side_effect=AssertionError("runtime step called")),
        ):
            report = verify_execution_reference(trace)
        self.assertEqual(report.status, "match")

    def test_reference_detects_a_semantically_wrong_runtime_operation(self):
        bad_result = self.backend.encode_symbol(1, observer=1)
        with patch.object(self.backend, "add", return_value=bad_result):
            trace = self.capture_add(trace_id="deliberately-wrong-add")
        report = verify_execution_reference(trace)
        self.assertEqual(report.status, "mismatch")
        self.assertTrue(any("step[2].event.write_values" in item for item in report.mismatches))
        self.assertTrue(any("final_snapshot.registers.sum" in item for item in report.mismatches))

    def test_exhaustive_c8_add_sub_for_all_sixteen_observer_pairs(self):
        checked_traces = 0
        checked_arithmetic = 0
        for observer_a in (1, 3, 5, 7):
            for observer_b in (1, 3, 5, 7):
                instructions = []
                for left in range(8):
                    for right in range(8):
                        instructions.extend((
                            Instruction("LOAD", {"dst": "a", "address": f"a{left}"}),
                            Instruction("LOAD", {"dst": "b", "address": f"b{right}"}),
                            Instruction("ADD", {"dst": "sum", "left": "a", "right": "b"}),
                            Instruction("SUB", {"dst": "difference", "left": "a", "right": "b"}),
                        ))
                instructions.append(Instruction("HALT"))
                program = Program(
                    f"exhaustive-c8-{observer_a}-{observer_b}",
                    tuple(instructions),
                )
                initial_memory = {
                    **{
                        f"a{symbol}": self.backend.encode_symbol(symbol, observer=observer_a)
                        for symbol in range(8)
                    },
                    **{
                        f"b{symbol}": self.backend.encode_symbol(symbol, observer=observer_b)
                        for symbol in range(8)
                    },
                }
                trace = self.adapter.capture(
                    program,
                    initial_memory,
                    trace_id=f"exhaustive-c8-{observer_a}-{observer_b}",
                    max_steps=300,
                )
                report = verify_execution_reference(trace)
                self.assertEqual(report.status, "match", report.mismatches)
                self.assertEqual(report.checked_steps, 257)
                self.assertEqual(report.checked_writes, 256)
                checked_traces += 1
                checked_arithmetic += 128
        self.assertEqual(checked_traces, 16)
        self.assertEqual(checked_arithmetic, 16 * 64 * 2)

    def test_branch_result_is_verified_under_a_separating_margin(self):
        for observer in (1, 3, 5, 7):
            trace = self.adapter.capture(
                branch_program(0.01),
                {
                    "a": self.backend.encode_symbol(2, observer=observer),
                    "b": self.backend.encode_symbol(2, observer=observer),
                },
                trace_id=f"same-symbol-branch-{observer}",
            )
            report = verify_execution_reference(trace)
            self.assertEqual(report.status, "match", report.mismatches)
            branch = trace.exchange.messages[2].payload["event"]
            self.assertIs(branch["branch_result"], True)

    def test_distinct_symbols_remain_separated_below_pi_over_four(self):
        for observer in (1, 3, 5, 7):
            trace = self.adapter.capture(
                branch_program(math.pi / 4 - 1e-4),
                {
                    "a": self.backend.encode_symbol(0, observer=observer),
                    "b": self.backend.encode_symbol(1, observer=observer),
                },
                trace_id=f"strict-separation-margin-{observer}",
            )
            report = verify_execution_reference(trace)
            self.assertEqual(report.status, "match", report.mismatches)
            branch = trace.exchange.messages[2].payload["event"]
            self.assertIs(branch["branch_result"], False)

    def test_branch_tolerance_has_a_real_observer_dependent_boundary(self):
        results = {}
        for observer in (1, 3):
            trace = self.adapter.capture(
                branch_program(math.pi / 4),
                {
                    "a": self.backend.encode_symbol(0, observer=observer),
                    "b": self.backend.encode_symbol(1, observer=observer),
                },
                trace_id=f"observer-boundary-{observer}",
            )
            report = verify_execution_reference(trace)
            self.assertEqual(report.status, "match", report.mismatches)
            results[observer] = trace.exchange.messages[2].payload["event"]["branch_result"]
        self.assertIs(results[1], True)
        self.assertIs(results[3], False)

    def test_ambiguous_branch_is_a_matched_trap_not_a_guessed_answer(self):
        residual = 0.10
        bound = 0.15
        left_angle = residual
        right_angle = -residual
        left = SignalValue(complex(math.cos(left_angle), math.sin(left_angle)), 1, bound)
        right = SignalValue(complex(math.cos(right_angle), math.sin(right_angle)), 1, bound)
        trace = self.adapter.capture(
            branch_program(0.20),
            {"a": left, "b": right},
            trace_id="ambiguous-reference-branch",
        )
        self.assertEqual(trace.status, "failed")
        self.assertEqual(
            trace.exchange.messages[-1].payload["exception_type"],
            "AmbiguousBranchError",
        )
        report = verify_execution_reference(trace)
        self.assertEqual(report.status, "match", report.mismatches)

    def test_wide_input_uncertainty_is_unsupported_not_misclassified(self):
        uncertain = SignalValue(1.0 + 0.0j, 1, math.pi / 4)
        program = Program("unsupported-wide-input", (
            Instruction("LOAD", {"dst": "x", "address": "x"}),
            Instruction("HALT"),
        ))
        trace = self.adapter.capture(
            program, {"x": uncertain}, trace_id="wide-input-uncertainty",
        )
        report = verify_execution_reference(trace)
        self.assertEqual(report.status, "unsupported")
        self.assertIn("does not identify one Z/8Z symbol", report.unsupported_reason)

    def test_same_observer_reframe_is_an_exact_runtime_identity(self):
        magnitude = 1.0 + 5e-8
        angle = 2.0 * math.pi * (3 * 2 % 8) / 8.0 + 0.001
        value = SignalValue(
            magnitude * complex(math.cos(angle), math.sin(angle)),
            3,
            0.002,
        )
        program = Program("same-observer-reframe", (
            Instruction("LOAD", {"dst": "source", "address": "x"}),
            Instruction("REFRAME", {"dst": "same", "src": "source", "observer": 3}),
            Instruction("EMIT", {"src": "same", "label": "same"}),
            Instruction("HALT"),
        ))
        trace = self.adapter.capture(
            program, {"x": value}, trace_id="same-observer-reframe-identity",
        )
        report = verify_execution_reference(trace)
        self.assertEqual(report.status, "match", report.mismatches)
        self.assertAlmostEqual(
            abs(complex(
                trace.final_snapshot["registers"]["same"]["real"],
                trace.final_snapshot["registers"]["same"]["imag"],
            )),
            magnitude,
            places=8,
        )

    def test_reframe_round_trip_preserves_symbol_but_expands_residual(self):
        symbol = 2
        residual = 0.001
        bound = 0.002
        angle = 2.0 * math.pi * symbol / 8.0 + residual
        initial = SignalValue(complex(math.cos(angle), math.sin(angle)), 1, bound)
        program = Program("observer-residual-transport", (
            Instruction("LOAD", {"dst": "source", "address": "x"}),
            Instruction("REFRAME", {"dst": "other", "src": "source", "observer": 3}),
            Instruction("REFRAME", {"dst": "return", "src": "other", "observer": 1}),
            Instruction("EMIT", {"src": "return", "label": "returned"}),
            Instruction("HALT"),
        ))
        trace = self.adapter.capture(program, {"x": initial}, trace_id="residual-round-trip")
        report = verify_execution_reference(trace)
        self.assertEqual(report.status, "match", report.mismatches)
        returned = trace.final_snapshot["registers"]["return"]
        returned_angle = math.atan2(returned["imag"], returned["real"])
        expected_centre = 2.0 * math.pi * symbol / 8.0
        actual_residual = math.atan2(
            math.sin(returned_angle - expected_centre),
            math.cos(returned_angle - expected_centre),
        )
        self.assertAlmostEqual(actual_residual, 0.009, places=7)
        self.assertAlmostEqual(returned["phase_error_bound"], 0.018, places=7)

    def test_sub_store_move_identity_branch_and_jump_are_independently_checked(self):
        program = Program("reference-state-path", (
            Instruction("LOAD", {"dst": "a", "address": "a"}),
            Instruction("LOAD", {"dst": "b", "address": "b"}),
            Instruction("SUB", {"dst": "difference", "left": "a", "right": "b"}),
            Instruction("STORE", {"src": "difference", "address": "saved"}),
            Instruction("MOVE", {"dst": "copy", "src": "difference"}),
            Instruction("BRANCH_IDENTITY", {
                "src": "copy", "target": 7, "tolerance_rad": 0.01,
            }),
            Instruction("JUMP", {"target": 8}),
            Instruction("EMIT", {"src": "copy", "label": "identity"}),
            Instruction("HALT"),
        ))
        for right, expected_branch in ((6, True), (5, False)):
            trace = self.adapter.capture(
                program,
                {
                    "a": self.backend.encode_symbol(6, observer=5),
                    "b": self.backend.encode_symbol(right, observer=3),
                },
                trace_id=f"reference-state-path-{right}",
            )
            report = verify_execution_reference(trace)
            self.assertEqual(report.status, "match", report.mismatches)
            self.assertIs(trace.exchange.messages[5].payload["event"]["branch_result"], expected_branch)
            self.assertEqual(trace.final_snapshot["halted"], True)

    def test_missing_memory_failure_is_independently_reproduced(self):
        program = Program("reference-missing-memory", (
            Instruction("LOAD", {"dst": "x", "address": "absent"}),
            Instruction("HALT"),
        ))
        trace = self.adapter.capture(program, {}, trace_id="reference-missing-cell")
        report = verify_execution_reference(trace)
        self.assertEqual(report.status, "match", report.mismatches)
        self.assertEqual(report.checked_steps, 1)


if __name__ == "__main__":
    unittest.main()
