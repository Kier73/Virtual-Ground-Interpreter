import unittest

from vgi import (
    AddExpr, ConditionalExpr, EqualityGuard, IdentityGuard, InputExpr,
    OutputSpec, Signal8Backend, TaskCompileError, TaskCompiler, TaskSpec,
    VirtualGroundInterpreter,
)


class DeclarativeCompilerTests(unittest.TestCase):
    def setUp(self):
        self.backend = Signal8Backend()
        self.interpreter = VirtualGroundInterpreter()

    def make_task(self):
        a, b = InputExpr("input.a"), InputExpr("input.b")
        expression = ConditionalExpr(
            guard=IdentityGuard(AddExpr(a, b), 0.02),
            when_true=b,
            when_false=a,
        )
        return TaskSpec("select-by-signal-identity", ("input.a", "input.b"),
                        (OutputSpec("selected", expression),))

    def test_interpreter_direct_task_entrypoint(self):
        result = self.interpreter.interpret(self.make_task(), {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        self.assertEqual(result.observed_outputs(self.backend), {"selected": 5})

    def test_task_compiles_and_executes_true_branch(self):
        program = TaskCompiler().compile(self.make_task())
        result = self.interpreter.execute(program, {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(5, 3),
        })
        self.assertEqual(result.observed_outputs(self.backend), {"selected": 5})
        self.assertIn("BRANCH_IDENTITY", program.instruction_set)
        self.assertNotIn("DECODE", program.instruction_set)

    def test_task_compiles_and_executes_false_branch(self):
        program = TaskCompiler().compile(self.make_task())
        result = self.interpreter.execute(program, {
            "input.a": self.backend.encode_symbol(3, 1),
            "input.b": self.backend.encode_symbol(4, 7),
        })
        self.assertEqual(result.observed_outputs(self.backend), {"selected": 3})

    def test_equality_guard_compiles(self):
        a, b = InputExpr("a"), InputExpr("b")
        task = TaskSpec("equality", ("a", "b"), (
            OutputSpec("same", ConditionalExpr(EqualityGuard(a, b, 0.01), a, b)),
        ))
        program = TaskCompiler().compile(task)
        result = self.interpreter.execute(program, {
            "a": self.backend.encode_symbol(6, 1),
            "b": self.backend.encode_symbol(6, 7),
        })
        self.assertEqual(result.observed_outputs(self.backend), {"same": 6})

    def test_nested_conditional_control_flow(self):
        a, b = InputExpr("a"), InputExpr("b")
        inner = ConditionalExpr(IdentityGuard(a, 0.01), b, a)
        outer = ConditionalExpr(IdentityGuard(AddExpr(a, b), 0.01), inner, a)
        task = TaskSpec("nested", ("a", "b"), (OutputSpec("out", outer),))
        program = TaskCompiler().compile(task)
        result = self.interpreter.execute(program, {
            "a": self.backend.encode_symbol(0, 1),
            "b": self.backend.encode_symbol(0, 3),
        })
        self.assertEqual(result.observed_outputs(self.backend), {"out": 0})

    def test_task_spec_json_round_trip(self):
        task = self.make_task()
        loaded = type(task).from_json(task.to_json())
        program_a = TaskCompiler().compile(task)
        program_b = TaskCompiler().compile(loaded)
        self.assertEqual(program_a.to_dict(), program_b.to_dict())

    def test_task_input_contract_rejects_undeclared_address(self):
        with self.assertRaises(TaskCompileError):
            TaskSpec("bad", ("a",), (OutputSpec("out", InputExpr("b")),))

    def test_task_rejects_output_memory_collision(self):
        with self.assertRaises(TaskCompileError):
            TaskSpec("bad", ("output.value",), (OutputSpec("value", InputExpr("output.value")),))

    def test_task_requires_unique_inputs_and_outputs(self):
        with self.assertRaises(TaskCompileError):
            TaskSpec("bad", ("a", "a"), (OutputSpec("x", InputExpr("a")),))
        with self.assertRaises(TaskCompileError):
            TaskSpec("bad", ("a",), (
                OutputSpec("x", InputExpr("a")), OutputSpec("x", InputExpr("a")),
            ))


if __name__ == "__main__":
    unittest.main()
