import unittest

from vgi import (
    AddExpr,
    ConditionalExpr,
    EqualityGuard,
    InputExpr,
    OutputSpec,
    Signal8Backend,
    TaskSpec,
    VirtualGroundInterpreter,
)


class BooleanSubgroupRealizationTests(unittest.TestCase):
    """Exhaust the Boolean subgroup {0,4} of Z/8Z through the existing VGI DSL."""

    def setUp(self):
        self.backend = Signal8Backend()
        self.interpreter = VirtualGroundInterpreter()

    def _memory(self, left, right, *, include_constants=False):
        memory = {
            "input.a": self.backend.encode_symbol(4 * left, observer=1),
            "input.b": self.backend.encode_symbol(4 * right, observer=3),
        }
        if include_constants:
            memory["input.zero"] = self.backend.encode_symbol(0, observer=5)
            memory["input.one"] = self.backend.encode_symbol(4, observer=7)
        return memory

    def test_group_addition_realizes_xor_for_all_binary_inputs(self):
        a, b = InputExpr("input.a"), InputExpr("input.b")
        task = TaskSpec(
            "boolean-xor",
            ("input.a", "input.b"),
            (OutputSpec("result", AddExpr(a, b)),),
        )
        for left in (0, 1):
            for right in (0, 1):
                with self.subTest(left=left, right=right):
                    result = self.interpreter.interpret(
                        task,
                        self._memory(left, right),
                    )
                    observed = result.observed_outputs(self.backend)["result"]
                    self.assertEqual(observed, 4 * (left ^ right))

    def test_conditional_equality_realizes_and_for_all_binary_inputs(self):
        a, b = InputExpr("input.a"), InputExpr("input.b")
        zero, one = InputExpr("input.zero"), InputExpr("input.one")
        expression = ConditionalExpr(
            EqualityGuard(a, one, 0.02),
            ConditionalExpr(
                EqualityGuard(b, one, 0.02),
                one,
                zero,
            ),
            zero,
        )
        task = TaskSpec(
            "boolean-and",
            ("input.a", "input.b", "input.zero", "input.one"),
            (OutputSpec("result", expression),),
        )
        for left in (0, 1):
            for right in (0, 1):
                with self.subTest(left=left, right=right):
                    result = self.interpreter.interpret(
                        task,
                        self._memory(left, right, include_constants=True),
                    )
                    observed = result.observed_outputs(self.backend)["result"]
                    self.assertEqual(observed, 4 * (left & right))


if __name__ == "__main__":
    unittest.main()
