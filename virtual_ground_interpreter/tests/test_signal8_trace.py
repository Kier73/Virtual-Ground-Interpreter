import unittest
from unittest.mock import patch

from vgi import (
    Instruction, Program, Signal8Backend, Signal8ExecutionAdapter,
    VirtualGroundInterpreter,
)


def conditional_program():
    return Program("trace-select", (
        Instruction("LOAD", {"dst": "a", "address": "input.a"}),
        Instruction("LOAD", {"dst": "b", "address": "input.b"}),
        Instruction("ADD", {"dst": "sum", "left": "a", "right": "b"}),
        Instruction("BRANCH_IDENTITY", {
            "src": "sum", "target": 6, "tolerance_rad": 0.02,
        }),
        Instruction("MOVE", {"dst": "selected", "src": "a"}),
        Instruction("JUMP", {"target": 7}),
        Instruction("MOVE", {"dst": "selected", "src": "b"}),
        Instruction("STORE", {"src": "selected", "address": "persistent.result"}),
        Instruction("EMIT", {"src": "selected", "label": "selected"}),
        Instruction("HALT"),
    ))


class Signal8ExecutionAdapterTests(unittest.TestCase):
    def setUp(self):
        self.backend = Signal8Backend()
        self.interpreter = VirtualGroundInterpreter()
        self.adapter = Signal8ExecutionAdapter()

    def memory(self):
        return {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        }

    def test_captures_successful_steps_as_encounters_and_evidence(self):
        machine = self.interpreter.instantiate(conditional_program(), self.memory())
        capture = self.adapter.capture(machine, run_id="capture-001")

        self.assertEqual(capture.status, "halted")
        self.assertTrue(capture.halted)
        self.assertEqual(capture.step_count, 8)
        self.assertEqual(len(capture.exchange.messages), 8)
        self.assertEqual(len(capture.encounters.encounters), 8)
        self.assertEqual(len(capture.frame_receipts), 8)
        self.assertEqual(len(capture.transition_evidence), 8)

        for message, frame in zip(capture.exchange.messages, capture.frame_receipts):
            encounter = capture.encounters.get(f"channel-message:{message.message_id}")
            self.assertEqual(encounter.payload, message.payload)
            self.assertEqual(frame.message_id, message.message_id)
            self.assertEqual(
                frame.payload_digest,
                capture.transition_evidence[frame.sequence - 1].payload_digest,
            )

    def test_runtime_state_ids_form_a_contiguous_path(self):
        machine = self.interpreter.instantiate(conditional_program(), self.memory())
        capture = self.adapter.capture(machine, run_id="capture-chain")
        for left, right in zip(capture.transition_evidence, capture.transition_evidence[1:]):
            self.assertEqual(left.outcomes[0].target, right.event[0])
        self.assertTrue(all(item.outcomes[0].output == () for item in capture.transition_evidence))

    def test_raw_signal_values_are_preserved_without_integer_decoding(self):
        machine = self.interpreter.instantiate(conditional_program(), self.memory())
        with patch.object(
            self.backend, "observe_symbol",
            side_effect=AssertionError("capture must not decode signal values"),
        ):
            capture = self.adapter.capture(machine, run_id="capture-native")
        report = capture.to_dict()
        raw_add = next(x for x in report["captured_events"] if x["opcode"] == "ADD")
        self.assertIn("real", raw_add["write_values"][0]["value"])
        self.assertEqual(capture.transition_evidence[2].outcomes[0].output, ())

    def test_context_is_run_scoped_but_runtime_states_are_reproducible(self):
        first = self.adapter.capture(
            self.interpreter.instantiate(conditional_program(), self.memory()),
            run_id="run-A",
        )
        second = self.adapter.capture(
            self.interpreter.instantiate(conditional_program(), self.memory()),
            run_id="run-B",
        )
        self.assertNotEqual(first.context_digest, second.context_digest)
        self.assertEqual(
            [x.event for x in first.transition_evidence],
            [x.event for x in second.transition_evidence],
        )
        self.assertEqual(
            [x.outcomes for x in first.transition_evidence],
            [x.outcomes for x in second.transition_evidence],
        )

    def test_step_limit_preserves_partial_capture(self):
        machine = self.interpreter.instantiate(
            Program("loop", (Instruction("JUMP", {"target": 0}), Instruction("HALT"))), {}
        )
        capture = self.adapter.capture(machine, run_id="run-limited", max_steps=3)
        self.assertEqual(capture.status, "step_limit")
        self.assertFalse(capture.halted)
        self.assertEqual(capture.step_count, 3)
        self.assertEqual(capture.result.final_pc, 0)

    def test_fault_is_retained_without_becoming_transition_evidence(self):
        machine = self.interpreter.instantiate(
            Program("missing-input", (
                Instruction("LOAD", {"dst": "x", "address": "missing"}),
                Instruction("HALT"),
            )), {}
        )
        capture = self.adapter.capture(machine, run_id="run-fault")
        self.assertEqual(capture.status, "faulted")
        self.assertEqual(capture.fault_type, "MissingMemoryCell")
        self.assertEqual(capture.step_count, 0)
        self.assertEqual(capture.transition_evidence, ())
        self.assertEqual(len(capture.exchange.messages), 1)
        self.assertEqual(capture.exchange.messages[0].payload["kind"], "execution_fault")
        self.assertNotIn("status", capture.exchange.messages[0].payload)
        self.assertEqual(len(capture.frame_receipts), 1)
        self.assertEqual(len(capture.encounters.encounters), 1)
        self.assertEqual(len(machine.trace), 0)

    def test_capture_can_start_from_a_partially_stepped_machine(self):
        machine = self.interpreter.instantiate(conditional_program(), self.memory())
        self.assertEqual(machine.step().opcode, "LOAD")
        capture = self.adapter.capture(machine, run_id="run-resumed")
        self.assertEqual(capture.status, "halted")
        self.assertEqual(capture.step_count, 7)
        self.assertEqual(capture.events[0].step, 1)

    def test_rejects_invalid_inputs(self):
        machine = self.interpreter.instantiate(conditional_program(), self.memory())
        with self.assertRaises(ValueError):
            self.adapter.capture(machine, run_id="")
        with self.assertRaises(ValueError):
            self.adapter.capture(machine, run_id="bad-limit", max_steps=0)
        with self.assertRaises(TypeError):
            self.adapter.capture(object(), run_id="bad-machine")


if __name__ == "__main__":
    unittest.main()
