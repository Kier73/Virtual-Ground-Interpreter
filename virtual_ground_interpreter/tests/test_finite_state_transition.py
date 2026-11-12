import itertools
import unittest

from vgi import (
    ConditionalExpr,
    EqualityGuard,
    InputExpr,
    OutputSpec,
    Signal8Backend,
    TaskCompiler,
    TaskSpec,
    VirtualGroundInterpreter,
)


INPUT_NAMES = ("state_1", "state_0", "advance", "reset")
OUTPUT_NAMES = ("next_state_1", "next_state_0")


def counter_rows():
    """Enumerate the total reset-dominant two-bit counter relation."""
    rows = {}
    for state_1, state_0, advance, reset in itertools.product((0, 1), repeat=4):
        state = (state_1 << 1) | state_0
        if reset:
            next_state = 0
        elif advance:
            next_state = (state + 1) % 4
        else:
            next_state = state
        rows[(state_1, state_0, advance, reset)] = (
            (next_state >> 1) & 1,
            next_state & 1,
        )
    return rows


def make_decision_tree(rows, output_index, depth=0, prefix=()):
    """Construct a nested equality task from the complete transition relation."""
    if depth == len(INPUT_NAMES):
        bit = rows[prefix][output_index]
        return InputExpr("input.one" if bit else "input.zero")
    address = InputExpr(f"input.{INPUT_NAMES[depth]}")
    one = InputExpr("input.one")
    return ConditionalExpr(
        EqualityGuard(address, one, 0.02),
        make_decision_tree(rows, output_index, depth + 1, prefix + (1,)),
        make_decision_tree(rows, output_index, depth + 1, prefix + (0,)),
    )


def make_counter_task():
    """Build both next-state outputs from the total two-bit counter table."""
    rows = counter_rows()
    outputs = tuple(
        OutputSpec(
            name,
            make_decision_tree(rows, index),
        )
        for index, name in enumerate(OUTPUT_NAMES)
    )
    inputs = tuple(f"input.{name}" for name in INPUT_NAMES) + (
        "input.zero",
        "input.one",
    )
    return TaskSpec("two-bit-counter-reset-dominant", inputs, outputs)


class FiniteStateTransitionReferenceTests(unittest.TestCase):
    """Exercise all 16 rows of the counter table through the existing VGI DSL."""

    def setUp(self):
        self.backend = Signal8Backend()
        self.interpreter = VirtualGroundInterpreter()
        self.task = make_counter_task()
        self.rows = counter_rows()

    def observe(self, pattern):
        observers = (1, 3, 5, 7)
        memory = {
            f"input.{name}": self.backend.encode_symbol(
                4 * bit,
                observer=observer,
            )
            for name, bit, observer in zip(INPUT_NAMES, pattern, observers)
        }
        memory["input.zero"] = self.backend.encode_symbol(0, observer=1)
        memory["input.one"] = self.backend.encode_symbol(4, observer=7)
        result = self.interpreter.interpret(self.task, memory)
        return result.observed_outputs(self.backend)

    def test_complete_transition_relation_over_all_sixteen_inputs(self):
        for pattern in itertools.product((0, 1), repeat=4):
            with self.subTest(pattern=pattern):
                observed = self.observe(pattern)
                expected = self.rows[pattern]
                self.assertEqual(
                    tuple(observed[name] for name in OUTPUT_NAMES),
                    tuple(4 * bit for bit in expected),
                )

    def test_task_json_round_trip_preserves_every_transition(self):
        restored = TaskSpec.from_json(self.task.to_json())
        interpreter = VirtualGroundInterpreter()
        for pattern in itertools.product((0, 1), repeat=4):
            observers = (1, 3, 5, 7)
            memory = {
                f"input.{name}": self.backend.encode_symbol(
                    4 * bit,
                    observer=observer,
                )
                for name, bit, observer in zip(INPUT_NAMES, pattern, observers)
            }
            memory["input.zero"] = self.backend.encode_symbol(0, observer=1)
            memory["input.one"] = self.backend.encode_symbol(4, observer=7)
            observed = interpreter.interpret(restored, memory).observed_outputs(self.backend)
            self.assertEqual(
                tuple(observed[name] for name in OUTPUT_NAMES),
                tuple(4 * bit for bit in self.rows[pattern]),
            )

    def test_reset_has_priority_over_advance(self):
        self.assertEqual(self.observe((0, 1, 1, 1))["next_state_1"], 0)
        self.assertEqual(self.observe((0, 1, 1, 1))["next_state_0"], 0)

    def test_advance_wraps_from_three_to_zero(self):
        self.assertEqual(self.observe((1, 1, 1, 0))["next_state_1"], 0)
        self.assertEqual(self.observe((1, 1, 1, 0))["next_state_0"], 0)


if __name__ == "__main__":
    unittest.main()
