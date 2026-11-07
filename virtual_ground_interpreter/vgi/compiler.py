"""Compile a declarative task expression into the VGI instruction language.

This is a deliberately small typed task DSL, not a natural-language planner.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, TypeAlias

from .ir import Instruction, Program


class TaskCompileError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class InputExpr:
    address: str

    def __post_init__(self) -> None:
        if not isinstance(self.address, str) or not self.address:
            raise TaskCompileError("input address must be a non-empty string")


@dataclass(frozen=True, slots=True)
class AddExpr:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True, slots=True)
class SubExpr:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True, slots=True)
class ReframeExpr:
    value: "Expr"
    observer: int

    def __post_init__(self) -> None:
        if isinstance(self.observer, bool) or not isinstance(self.observer, int):
            raise TaskCompileError("observer must be an integer coordinate id")


@dataclass(frozen=True, slots=True)
class IdentityGuard:
    value: "Expr"
    tolerance_rad: float

    def __post_init__(self) -> None:
        if isinstance(self.tolerance_rad, bool) or not isinstance(self.tolerance_rad, (int, float)):
            raise TaskCompileError("identity tolerance must be numeric")
        if not 0.0 <= float(self.tolerance_rad) <= 3.141592653589793:
            raise TaskCompileError("identity tolerance must be in [0, pi]")


@dataclass(frozen=True, slots=True)
class EqualityGuard:
    left: "Expr"
    right: "Expr"
    tolerance_rad: float

    def __post_init__(self) -> None:
        if isinstance(self.tolerance_rad, bool) or not isinstance(self.tolerance_rad, (int, float)):
            raise TaskCompileError("equality tolerance must be numeric")
        if not 0.0 <= float(self.tolerance_rad) <= 3.141592653589793:
            raise TaskCompileError("equality tolerance must be in [0, pi]")


Guard: TypeAlias = IdentityGuard | EqualityGuard


@dataclass(frozen=True, slots=True)
class ConditionalExpr:
    guard: Guard
    when_true: "Expr"
    when_false: "Expr"


Expr: TypeAlias = InputExpr | AddExpr | SubExpr | ReframeExpr | ConditionalExpr


@dataclass(frozen=True, slots=True)
class OutputSpec:
    label: str
    expression: Expr

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise TaskCompileError("output label must be a non-empty string")


@dataclass(frozen=True, slots=True)
class TaskSpec:
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[OutputSpec, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "outputs", tuple(self.outputs))
        if not isinstance(self.name, str) or not self.name:
            raise TaskCompileError("task name must be a non-empty string")
        if any(not isinstance(x, str) for x in self.inputs):
            raise TaskCompileError("task input addresses must be strings")
        if len(set(self.inputs)) != len(self.inputs) or any(not x for x in self.inputs):
            raise TaskCompileError("task inputs must be unique, non-empty memory addresses")
        if not self.outputs:
            raise TaskCompileError("task must declare at least one output")
        if any(not isinstance(x, OutputSpec) for x in self.outputs):
            raise TaskCompileError("outputs must be OutputSpec instances")
        labels = [x.label for x in self.outputs]
        if len(set(labels)) != len(labels):
            raise TaskCompileError("output labels must be unique")
        reserved_outputs = {f"output.{label}" for label in labels}
        collisions = reserved_outputs & set(self.inputs)
        if collisions:
            raise TaskCompileError(f"input addresses collide with reserved output cells: {sorted(collisions)}")
        declared = set(self.inputs)
        referenced: set[str] = set()
        for output in self.outputs:
            referenced.update(_input_addresses(output.expression))
        missing = referenced - declared
        if missing:
            raise TaskCompileError(f"expressions reference undeclared inputs: {sorted(missing)}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "inputs": list(self.inputs),
            "outputs": [
                {"label": output.label, "expression": _expr_to_dict(output.expression)}
                for output in self.outputs
            ],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TaskSpec":
        if not isinstance(data, Mapping):
            raise TaskCompileError("task definition must be an object")
        _expect_keys(data, {"name", "inputs", "outputs"})
        if not isinstance(data["inputs"], (list, tuple)) or not isinstance(data["outputs"], (list, tuple)):
            raise TaskCompileError("task inputs and outputs must be arrays")
        outputs = []
        for item in data["outputs"]:
            if not isinstance(item, Mapping):
                raise TaskCompileError("each task output must be an object")
            _expect_keys(item, {"label", "expression"})
            outputs.append(OutputSpec(item["label"], _parse_expr(item["expression"])))
        return cls(data["name"], tuple(data["inputs"]), tuple(outputs))

    @classmethod
    def from_json(cls, source: str) -> "TaskSpec":
        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise TaskCompileError(f"invalid task JSON: {exc}") from exc
        return cls.from_dict(data)


def _input_addresses(expr: Expr) -> set[str]:
    if isinstance(expr, InputExpr):
        return {expr.address}
    if isinstance(expr, (AddExpr, SubExpr)):
        return _input_addresses(expr.left) | _input_addresses(expr.right)
    if isinstance(expr, ReframeExpr):
        return _input_addresses(expr.value)
    if isinstance(expr, ConditionalExpr):
        return _guard_inputs(expr.guard) | _input_addresses(expr.when_true) | _input_addresses(expr.when_false)
    raise TaskCompileError(f"unsupported expression type: {type(expr).__name__}")


def _guard_inputs(guard: Guard) -> set[str]:
    if isinstance(guard, IdentityGuard):
        return _input_addresses(guard.value)
    if isinstance(guard, EqualityGuard):
        return _input_addresses(guard.left) | _input_addresses(guard.right)
    raise TaskCompileError(f"unsupported guard type: {type(guard).__name__}")


def _expr_to_dict(expr: Expr) -> dict[str, Any]:
    if isinstance(expr, InputExpr):
        return {"type": "input", "address": expr.address}
    if isinstance(expr, AddExpr):
        return {"type": "add", "left": _expr_to_dict(expr.left), "right": _expr_to_dict(expr.right)}
    if isinstance(expr, SubExpr):
        return {"type": "sub", "left": _expr_to_dict(expr.left), "right": _expr_to_dict(expr.right)}
    if isinstance(expr, ReframeExpr):
        return {"type": "reframe", "value": _expr_to_dict(expr.value), "observer": expr.observer}
    if isinstance(expr, ConditionalExpr):
        return {"type": "if", "guard": _guard_to_dict(expr.guard),
                "when_true": _expr_to_dict(expr.when_true),
                "when_false": _expr_to_dict(expr.when_false)}
    raise TaskCompileError(f"unsupported expression type: {type(expr).__name__}")


def _guard_to_dict(guard: Guard) -> dict[str, Any]:
    if isinstance(guard, IdentityGuard):
        return {"type": "is_identity", "value": _expr_to_dict(guard.value),
                "tolerance_rad": float(guard.tolerance_rad)}
    if isinstance(guard, EqualityGuard):
        return {"type": "equal", "left": _expr_to_dict(guard.left),
                "right": _expr_to_dict(guard.right), "tolerance_rad": float(guard.tolerance_rad)}
    raise TaskCompileError(f"unsupported guard type: {type(guard).__name__}")


def _expect_keys(data: Mapping[str, Any], required: set[str], optional: set[str] = frozenset()) -> None:
    missing, extra = required - set(data), set(data) - required - set(optional)
    if missing or extra:
        raise TaskCompileError(f"invalid task node keys; missing={sorted(missing)}, extra={sorted(extra)}")


def _parse_expr(data: Any) -> Expr:
    if not isinstance(data, Mapping) or "type" not in data:
        raise TaskCompileError("expression nodes must be objects with a 'type' field")
    kind = data["type"]
    if kind == "input":
        _expect_keys(data, {"type", "address"})
        return InputExpr(data["address"])
    if kind in ("add", "sub"):
        _expect_keys(data, {"type", "left", "right"})
        cls = AddExpr if kind == "add" else SubExpr
        return cls(_parse_expr(data["left"]), _parse_expr(data["right"]))
    if kind == "reframe":
        _expect_keys(data, {"type", "value", "observer"})
        return ReframeExpr(_parse_expr(data["value"]), data["observer"])
    if kind == "if":
        _expect_keys(data, {"type", "guard", "when_true", "when_false"})
        return ConditionalExpr(_parse_guard(data["guard"]),
                               _parse_expr(data["when_true"]), _parse_expr(data["when_false"]))
    raise TaskCompileError(f"unknown expression type: {kind!r}")


def _parse_guard(data: Any) -> Guard:
    if not isinstance(data, Mapping) or "type" not in data:
        raise TaskCompileError("guard nodes must be objects with a 'type' field")
    kind = data["type"]
    if kind == "is_identity":
        _expect_keys(data, {"type", "value", "tolerance_rad"})
        return IdentityGuard(_parse_expr(data["value"]), data["tolerance_rad"])
    if kind == "equal":
        _expect_keys(data, {"type", "left", "right", "tolerance_rad"})
        return EqualityGuard(_parse_expr(data["left"]), _parse_expr(data["right"]), data["tolerance_rad"])
    raise TaskCompileError(f"unknown guard type: {kind!r}")


class TaskCompiler:
    """Lower the typed expression DSL to explicit VGI control-flow instructions."""

    def compile(self, task: TaskSpec) -> Program:
        self._instructions: list[tuple[str, dict[str, object]]] = []
        self._next_register = 0
        for output in task.outputs:
            value_reg = self._compile_expr(output.expression)
            self._emit("STORE", src=value_reg, address=f"output.{output.label}")
            self._emit("EMIT", src=value_reg, label=output.label)
        self._emit("HALT")
        instructions = tuple(Instruction(op, args) for op, args in self._instructions)
        return Program(task.name, instructions, {
            "source": "vgi.task-expression.v1",
            "declared_inputs": list(task.inputs),
            "declared_outputs": [x.label for x in task.outputs],
            "lowering": "typed expression tree to signal-state IR",
        })

    def _reg(self) -> str:
        name = f"t{self._next_register}"
        self._next_register += 1
        return name

    def _emit(self, opcode: str, **args: object) -> int:
        self._instructions.append((opcode, args))
        return len(self._instructions) - 1

    def _patch_target(self, index: int, target: int) -> None:
        opcode, args = self._instructions[index]
        if opcode not in ("BRANCH_EQ", "BRANCH_IDENTITY", "JUMP"):
            raise TaskCompileError("internal compiler error: target patch applied to non-control instruction")
        patched = dict(args)
        patched["target"] = target
        self._instructions[index] = (opcode, patched)

    def _compile_guard(self, guard: Guard) -> int:
        if isinstance(guard, IdentityGuard):
            value_reg = self._compile_expr(guard.value)
            return self._emit("BRANCH_IDENTITY", src=value_reg, target=-1,
                              tolerance_rad=float(guard.tolerance_rad))
        if isinstance(guard, EqualityGuard):
            left_reg = self._compile_expr(guard.left)
            right_reg = self._compile_expr(guard.right)
            return self._emit("BRANCH_EQ", left=left_reg, right=right_reg, target=-1,
                              tolerance_rad=float(guard.tolerance_rad))
        raise TaskCompileError(f"unsupported guard type: {type(guard).__name__}")

    def _compile_expr(self, expr: Expr) -> str:
        if isinstance(expr, InputExpr):
            dst = self._reg()
            self._emit("LOAD", dst=dst, address=expr.address)
            return dst
        if isinstance(expr, AddExpr):
            left, right = self._compile_expr(expr.left), self._compile_expr(expr.right)
            dst = self._reg()
            self._emit("ADD", dst=dst, left=left, right=right)
            return dst
        if isinstance(expr, SubExpr):
            left, right = self._compile_expr(expr.left), self._compile_expr(expr.right)
            dst = self._reg()
            self._emit("SUB", dst=dst, left=left, right=right)
            return dst
        if isinstance(expr, ReframeExpr):
            src, dst = self._compile_expr(expr.value), self._reg()
            self._emit("REFRAME", dst=dst, src=src, observer=expr.observer)
            return dst
        if isinstance(expr, ConditionalExpr):
            branch_index = self._compile_guard(expr.guard)
            result_reg = self._reg()

            # Fall through to the false arm; the guard's true edge jumps over it.
            false_reg = self._compile_expr(expr.when_false)
            self._emit("MOVE", dst=result_reg, src=false_reg)
            join_jump = self._emit("JUMP", target=-1)

            true_start = len(self._instructions)
            true_reg = self._compile_expr(expr.when_true)
            self._emit("MOVE", dst=result_reg, src=true_reg)
            join = len(self._instructions)

            self._patch_target(branch_index, true_start)
            self._patch_target(join_jump, join)
            return result_reg
        raise TaskCompileError(f"unsupported expression type: {type(expr).__name__}")
