"""Finite exhaustive checks for the declared signal Ground."""
from __future__ import annotations

from itertools import product
import json
from typing import Any

from . import (
    AddExpr, ConditionalExpr, IdentityGuard, InputExpr, Instruction, OutputSpec,
    Program, SIGNAL8_GROUND, Signal8Backend, TaskCompiler, TaskSpec,
    VirtualGroundInterpreter,
)
from .values import OBSERVERS


def verify_finite_ground() -> dict[str, Any]:
    backend = Signal8Backend()
    interpreter = VirtualGroundInterpreter()
    counts = {
        "encode_observe": 0,
        "reframe_round_trip": 0,
        "binary_arithmetic": 0,
        "observer_naturality": 0,
        "two_operation_composition": 0,
        "conditional_paths": 0,
        "compiled_task_paths": 0,
    }
    errors: list[str] = []

    for u in OBSERVERS:
        for k in range(8):
            counts["encode_observe"] += 1
            if backend.observe_symbol(backend.encode_symbol(k, u)) != k:
                errors.append(f"encode/observe failed: observer={u}, symbol={k}")

    for u, v, k in product(OBSERVERS, OBSERVERS, range(8)):
        counts["reframe_round_trip"] += 1
        value = backend.encode_symbol(k, u)
        actual = backend.reframe(backend.reframe(value, v), u)
        if backend.observe_symbol(actual) != k or actual.observer != u:
            errors.append(f"reframe failed: {u}->{v}->{u}, symbol={k}")

    for u, a, b in product(OBSERVERS, range(8), range(8)):
        left = backend.encode_symbol(a, u)
        right = backend.encode_symbol(b, u)
        for op, expected in (("ADD", (a + b) % 8), ("SUB", (a - b) % 8)):
            counts["binary_arithmetic"] += 1
            result = backend.add(left, right) if op == "ADD" else backend.sub(left, right)
            if backend.observe_symbol(result) != expected:
                errors.append(f"{op} failed: observer={u}, a={a}, b={b}")

    for u, v, a, b in product(OBSERVERS, OBSERVERS, range(8), range(8)):
        source_a, source_b = backend.encode_symbol(a, u), backend.encode_symbol(b, u)
        mapped_a, mapped_b = backend.reframe(source_a, v), backend.reframe(source_b, v)
        for op in ("ADD", "SUB"):
            counts["observer_naturality"] += 1
            before = backend.add(source_a, source_b) if op == "ADD" else backend.sub(source_a, source_b)
            after = backend.add(mapped_a, mapped_b) if op == "ADD" else backend.sub(mapped_a, mapped_b)
            lhs = backend.reframe(before, v)
            if backend.observe_symbol(lhs) != backend.observe_symbol(after):
                errors.append(f"observer naturality failed: {op}, {u}->{v}, {a},{b}")

    opcode_pairs = (("ADD", "ADD"), ("ADD", "SUB"), ("SUB", "ADD"), ("SUB", "SUB"))
    for op1, op2 in opcode_pairs:
        for a, b, c in product(range(8), repeat=3):
            ua, ub, uc = OBSERVERS[a % 4], OBSERVERS[b % 4], OBSERVERS[c % 4]
            value_a, value_b, value_c = (backend.encode_symbol(a, ua),
                                         backend.encode_symbol(b, ub),
                                         backend.encode_symbol(c, uc))
            mid = backend.add(value_a, value_b) if op1 == "ADD" else backend.sub(value_a, value_b)
            mid = backend.reframe(mid, OBSERVERS[(a + b + c) % 4])
            out = backend.add(mid, value_c) if op2 == "ADD" else backend.sub(mid, value_c)
            partial = (a + b) % 8 if op1 == "ADD" else (a - b) % 8
            expected = (partial + c) % 8 if op2 == "ADD" else (partial - c) % 8
            counts["two_operation_composition"] += 1
            if backend.observe_symbol(out) != expected:
                errors.append(f"composition failed: {op1}->{op2}({a},{b},{c})")

    # The same program is exercised on both sides of its conditional transition.
    program = Program("conditional-select", (
        Instruction("LOAD", {"dst": "a", "address": "input.a"}),
        Instruction("LOAD", {"dst": "b", "address": "input.b"}),
        Instruction("ADD", {"dst": "sum", "left": "a", "right": "b"}),
        Instruction("BRANCH_IDENTITY", {"src": "sum", "target": 6, "tolerance_rad": 0.02}),
        Instruction("MOVE", {"dst": "selected", "src": "a"}),
        Instruction("JUMP", {"target": 7}),
        Instruction("MOVE", {"dst": "selected", "src": "b"}),
        Instruction("EMIT", {"src": "selected", "label": "selected"}),
        Instruction("HALT"),
    ))
    cases = ((3, 5, 5), (3, 4, 3))
    for a, b, expected in cases:
        counts["conditional_paths"] += 1
        result = interpreter.execute(program, {
            "input.a": backend.encode_symbol(a, 1),
            "input.b": backend.encode_symbol(b, 7),
        })
        actual = result.observed_outputs(backend).get("selected")
        if actual != expected:
            errors.append(f"conditional path failed: a={a}, b={b}, got={actual}, expected={expected}")

    input_a, input_b = InputExpr("input.a"), InputExpr("input.b")
    task = TaskSpec("finite-task-compiler-check", ("input.a", "input.b"), (
        OutputSpec("selected", ConditionalExpr(
            IdentityGuard(AddExpr(input_a, input_b), 0.02), input_b, input_a)),
    ))
    compiled = TaskCompiler().compile(task)
    for a, b, expected in cases:
        counts["compiled_task_paths"] += 1
        result = interpreter.execute(compiled, {
            "input.a": backend.encode_symbol(a, OBSERVERS[0]),
            "input.b": backend.encode_symbol(b, OBSERVERS[3]),
        })
        actual = result.observed_outputs(backend).get("selected")
        if actual != expected:
            errors.append(f"compiled task failed: a={a}, b={b}, got={actual}, expected={expected}")

    return {
        "ground_id": SIGNAL8_GROUND.ground_id,
        "ground_version": SIGNAL8_GROUND.version,
        "ground_fingerprint": SIGNAL8_GROUND.fingerprint,
        "status": "PASS" if not errors else "FAIL",
        "counts": counts,
        "total_cases": sum(counts.values()),
        "errors": errors,
        "scope": "finite exhaustive checks for the declared Z/8Z signal Ground; not a proof about arbitrary domains",
    }


def main() -> None:
    result = verify_finite_ground()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
