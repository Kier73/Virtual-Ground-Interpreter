import json
from pathlib import Path
import unittest
from unittest.mock import patch

from vgi import (
    AmbiguousBranchError, GroundSpec, Instruction, MissingMemoryCell, MissingRegister,
    Program, ProgramError, RuntimeErrorVGI, SIGNAL8_GROUND, Signal8Backend,
    StepLimitExceeded, VirtualGroundInterpreter,
)

ROOT = Path(__file__).resolve().parents[1]


def conditional_program():
    return Program("conditional-select", (
        Instruction("LOAD", {"dst": "a", "address": "input.a"}),
        Instruction("LOAD", {"dst": "b", "address": "input.b"}),
        Instruction("ADD", {"dst": "sum", "left": "a", "right": "b"}),
        Instruction("BRANCH_IDENTITY", {"src": "sum", "target": 6, "tolerance_rad": 0.02}),
        Instruction("MOVE", {"dst": "selected", "src": "a"}),
        Instruction("JUMP", {"target": 7}),
        Instruction("MOVE", {"dst": "selected", "src": "b"}),
        Instruction("STORE", {"src": "selected", "address": "persistent.result"}),
        Instruction("EMIT", {"src": "selected", "label": "selected"}),
        Instruction("HALT"),
    ))


class InterpreterMachineTests(unittest.TestCase):
    def setUp(self):
        self.backend = Signal8Backend()
        self.interpreter = VirtualGroundInterpreter()

    def test_identity_branch_true_path(self):
        memory = {"input.a": self.backend.encode_symbol(3, 1),
                  "input.b": self.backend.encode_symbol(5, 3)}
        result = self.interpreter.execute(conditional_program(), memory)
        self.assertTrue(result.halted)
        self.assertEqual(result.observed_outputs(self.backend), {"selected": 5})
        branch = next(x for x in result.trace if x.opcode == "BRANCH_IDENTITY")
        self.assertTrue(branch.branch_result)
        self.assertEqual(branch.pc_after, 6)
        self.assertEqual(branch.branch_observer, 1)
        self.assertAlmostEqual(branch.branch_tolerance_rad, 0.02)
        self.assertLessEqual(branch.branch_upper_bound_rad, branch.branch_tolerance_rad)
        self.assertEqual(len(branch.branch_operands), 2)

    def test_identity_branch_false_path(self):
        memory = {"input.a": self.backend.encode_symbol(3, 1),
                  "input.b": self.backend.encode_symbol(4, 7)}
        result = self.interpreter.execute(conditional_program(), memory)
        self.assertEqual(result.observed_outputs(self.backend), {"selected": 3})
        branch = next(x for x in result.trace if x.opcode == "BRANCH_IDENTITY")
        self.assertFalse(branch.branch_result)
        self.assertEqual(branch.pc_after, 4)

    def test_branch_eq_across_observers(self):
        p = Program("eq", (
            Instruction("LOAD", {"dst": "a", "address": "a"}),
            Instruction("LOAD", {"dst": "b", "address": "b"}),
            Instruction("BRANCH_EQ", {"left": "a", "right": "b", "target": 4, "tolerance_rad": 0.01}),
            Instruction("HALT"), Instruction("EMIT", {"src": "a"}), Instruction("HALT"),
        ))
        mem = {"a": self.backend.encode_symbol(6, 1), "b": self.backend.encode_symbol(6, 7)}
        result = self.interpreter.execute(p, mem)
        self.assertEqual(len(result.outputs), 1)

    def test_no_integer_decode_during_machine_execution(self):
        program = conditional_program()
        memory = {"input.a": self.backend.encode_symbol(3, 1),
                  "input.b": self.backend.encode_symbol(5, 3)}
        with patch.object(self.backend, "observe_symbol", side_effect=AssertionError("integer decode during run")):
            machine = self.interpreter.instantiate(program, memory)
            result = machine.run()
            self.assertTrue(result.halted)
        self.assertEqual(result.observed_outputs(self.backend), {"selected": 5})

    def test_memory_is_persistent_and_written(self):
        machine = self.interpreter.instantiate(conditional_program(), {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        result = machine.run()
        self.assertIn("persistent.result", machine.memory)
        self.assertEqual(self.backend.observe_symbol(machine.memory["persistent.result"]), 5)

    def test_stepwise_execution_can_pause_and_resume(self):
        machine = self.interpreter.instantiate(conditional_program(), {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        with self.assertRaises(StepLimitExceeded):
            machine.run(max_steps=3)
        self.assertEqual(machine.pc, 3)
        result = machine.run(max_steps=20)
        self.assertTrue(result.halted)

    def test_snapshot_restore_preserves_execution_state(self):
        program = conditional_program()
        machine = self.interpreter.instantiate(program, {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        [machine.step() for _ in range(4)]
        snap = json.loads(json.dumps(machine.snapshot()))
        restored = type(machine).restore(self.interpreter, program, snap)
        self.assertEqual(restored.trace[-1].opcode, "BRANCH_IDENTITY")
        self.assertEqual(len(restored.trace[-1].branch_operands), 2)
        result = restored.run()
        self.assertEqual(result.observed_outputs(self.backend), {"selected": 5})

    def test_snapshot_detects_state_tampering(self):
        program = conditional_program()
        machine = self.interpreter.instantiate(program, {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        machine.step()
        snap = machine.snapshot()
        snap["pc"] = 8
        with self.assertRaises(RuntimeErrorVGI):
            type(machine).restore(self.interpreter, program, snap)

    def test_snapshot_rejects_different_program(self):
        program = conditional_program()
        machine = self.interpreter.instantiate(program, {})
        snap = machine.snapshot()
        other = Program("other", (Instruction("HALT"),))
        with self.assertRaises(RuntimeErrorVGI):
            type(machine).restore(self.interpreter, other, snap)

    def test_undo_restores_pc_registers_memory_and_outputs(self):
        machine = self.interpreter.instantiate(conditional_program(), {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        for _ in range(7):
            machine.step()
        self.assertEqual(len(machine.outputs), 1)
        event = machine.undo()
        self.assertEqual(event.opcode, "EMIT")
        self.assertEqual(len(machine.outputs), 0)
        machine.undo()  # undo STORE
        self.assertNotIn("persistent.result", machine.memory)

    def test_trace_records_signal_state_written_by_operations(self):
        machine = self.interpreter.instantiate(conditional_program(), {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        machine.step(); machine.step(); add_event = machine.step()
        self.assertEqual(add_event.opcode, "ADD")
        self.assertEqual(add_event.write_values[0][0], "register:sum")
        self.assertEqual(self.backend.observe_symbol(add_event.write_values[0][1]), 0)

    def test_reset_restores_initial_memory_and_clears_execution_history(self):
        machine = self.interpreter.instantiate(conditional_program(), {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        machine.run()
        self.assertIn("persistent.result", machine.memory)
        machine.reset()
        self.assertEqual(machine.pc, 0)
        self.assertFalse(machine.halted)
        self.assertEqual(machine.trace, [])
        self.assertEqual(machine.outputs, [])
        self.assertNotIn("persistent.result", machine.memory)
        self.assertIn("input.a", machine.memory)

    def test_restored_machine_reset_uses_original_initial_memory(self):
        program = conditional_program()
        machine = self.interpreter.instantiate(program, {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        machine.step()
        restored = type(machine).restore(self.interpreter, program, json.loads(json.dumps(machine.snapshot())))
        restored.run()
        restored.reset()
        self.assertEqual(set(restored.memory), {"input.a", "input.b"})

    def test_undo_restores_branch_path(self):
        machine = self.interpreter.instantiate(conditional_program(), {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        for _ in range(4):
            machine.step()
        self.assertEqual(machine.pc, 6)
        machine.undo()
        self.assertEqual(machine.pc, 3)
        self.assertEqual(len(machine.trace), 3)

    def test_ambiguous_branch_traps_without_partial_transition(self):
        from vgi import SignalValue
        import math
        p = Program("ambiguous", (
            Instruction("LOAD", {"dst": "x", "address": "x"}),
            Instruction("BRANCH_IDENTITY", {"src": "x", "target": 3, "tolerance_rad": 0.05}),
            Instruction("HALT"), Instruction("HALT"),
        ))
        value = SignalValue(complex(math.cos(0.05), math.sin(0.05)), 1, 0.01)
        machine = self.interpreter.instantiate(p, {"x": value})
        machine.step()
        with self.assertRaises(AmbiguousBranchError):
            machine.step()
        self.assertEqual(machine.pc, 1)
        self.assertEqual(len(machine.trace), 1)

    def test_missing_memory_cell_and_register_are_explicit(self):
        p = Program("missing", (Instruction("LOAD", {"dst": "x", "address": "nope"}), Instruction("HALT")))
        machine = self.interpreter.instantiate(p, {})
        with self.assertRaises(MissingMemoryCell):
            machine.step()
        p2 = Program("missing-register", (Instruction("MOVE", {"dst": "x", "src": "nope"}), Instruction("HALT")))
        with self.assertRaises(MissingRegister):
            self.interpreter.instantiate(p2, {}).step()

    def test_instruction_and_program_validation(self):
        with self.assertRaises(ProgramError):
            Instruction("ADD", {"dst": "r"})
        with self.assertRaises(ProgramError):
            Instruction("INVENTED", {})
        with self.assertRaises(ProgramError):
            Program("bad-target", (Instruction("JUMP", {"target": 7}), Instruction("HALT")))
        with self.assertRaises(ProgramError):
            Program("no-halt", (Instruction("MOVE", {"dst": "a", "src": "b"}),))

    def test_ir_arguments_are_immutable_after_validation(self):
        args = {"dst": "r0", "src": "r1"}
        ins = Instruction("MOVE", args)
        args["src"] = "changed"
        self.assertEqual(ins.args["src"], "r1")
        with self.assertRaises(TypeError):
            ins.args["src"] = "mutated"

    def test_program_metadata_is_deeply_immutable(self):
        program = Program("metadata", (Instruction("HALT"),), {"nested": {"items": [1, 2]}})
        with self.assertRaises(TypeError):
            program.metadata["nested"]["new"] = 3
        self.assertEqual(program.to_dict()["metadata"], {"nested": {"items": [1, 2]}})

    def test_program_json_round_trip(self):
        program = conditional_program()
        loaded = Program.from_json(program.to_json())
        self.assertEqual(loaded.to_dict(), program.to_dict())

    def test_ground_rejects_unsupported_instruction(self):
        restricted = GroundSpec("restricted", "1", SIGNAL8_GROUND.domain_id,
                                SIGNAL8_GROUND.observer_profiles, ("HALT",), "trap", (), ())
        restricted_interpreter = VirtualGroundInterpreter(restricted)
        with self.assertRaises(Exception):
            restricted_interpreter.instantiate(conditional_program(), {})

    def test_ground_backend_domain_mismatch_rejected(self):
        fake_ground = GroundSpec("wrong", "1", "other-domain", (1, 3, 5, 7), ("HALT",), "trap", (), ())
        with self.assertRaises(Exception):
            VirtualGroundInterpreter(fake_ground)

    def test_infinite_loop_stops_at_step_limit(self):
        p = Program("loop", (Instruction("JUMP", {"target": 0}), Instruction("HALT")))
        machine = self.interpreter.instantiate(p, {})
        with self.assertRaises(StepLimitExceeded):
            machine.run(max_steps=10)
        self.assertEqual(machine.pc, 0)
        self.assertEqual(len(machine.trace), 10)


if __name__ == "__main__":
    unittest.main()
