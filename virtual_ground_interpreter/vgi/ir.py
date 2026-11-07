"""Small typed instruction representation for the Virtual Ground Interpreter."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from types import MappingProxyType
from typing import Any, Mapping


class ProgramError(ValueError):
    pass


_SCHEMAS: dict[str, tuple[set[str], set[str]]] = {
    "LOAD": ({"dst", "address"}, set()),
    "STORE": ({"src", "address"}, set()),
    "MOVE": ({"dst", "src"}, set()),
    "REFRAME": ({"dst", "src", "observer"}, set()),
    "ADD": ({"dst", "left", "right"}, set()),
    "SUB": ({"dst", "left", "right"}, set()),
    "BRANCH_EQ": ({"left", "right", "target", "tolerance_rad"}, set()),
    "BRANCH_IDENTITY": ({"src", "target", "tolerance_rad"}, set()),
    "JUMP": ({"target"}, set()),
    "EMIT": ({"src"}, {"label"}),
    "HALT": (set(), set()),
}
_REGISTER_FIELDS = {"dst", "src", "left", "right"}
_ADDRESS_FIELDS = {"address"}


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze_json(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(v) for v in value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ProgramError("metadata floats must be finite")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ProgramError(f"metadata must contain only JSON-compatible values, got {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw_json(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(v) for v in value]
    return value


@dataclass(frozen=True, slots=True)
class Instruction:
    opcode: str
    args: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        op = self.opcode.upper()
        object.__setattr__(self, "opcode", op)
        if op not in _SCHEMAS:
            raise ProgramError(f"unsupported instruction: {op}")
        required, optional = _SCHEMAS[op]
        keys = set(self.args)
        missing, extra = required - keys, keys - required - optional
        if missing:
            raise ProgramError(f"{op} missing arguments: {sorted(missing)}")
        if extra:
            raise ProgramError(f"{op} has unknown arguments: {sorted(extra)}")
        clean = dict(self.args)
        for key in _REGISTER_FIELDS & keys:
            if not isinstance(clean[key], str) or not clean[key]:
                raise ProgramError(f"{op}.{key} must be a non-empty register name")
        for key in _ADDRESS_FIELDS & keys:
            if not isinstance(clean[key], str) or not clean[key]:
                raise ProgramError(f"{op}.{key} must be a non-empty address")
        if "target" in clean and (isinstance(clean["target"], bool) or not isinstance(clean["target"], int)):
            raise ProgramError(f"{op}.target must be an integer instruction index")
        if "observer" in clean and (isinstance(clean["observer"], bool) or not isinstance(clean["observer"], int)):
            raise ProgramError("REFRAME.observer must be an integer observer id")
        if "tolerance_rad" in clean:
            t = clean["tolerance_rad"]
            if isinstance(t, bool) or not isinstance(t, (int, float)):
                raise ProgramError(f"{op}.tolerance_rad must be numeric")
            if not 0.0 <= float(t) <= 3.141592653589793:
                raise ProgramError(f"{op}.tolerance_rad must be in [0, pi]")
            clean["tolerance_rad"] = float(t)
        if "label" in clean and (not isinstance(clean["label"], str) or not clean["label"]):
            raise ProgramError("EMIT.label must be a non-empty string")
        object.__setattr__(self, "args", MappingProxyType(clean))

    def to_dict(self) -> dict[str, Any]:
        return {"op": self.opcode, **dict(self.args)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Instruction":
        if not isinstance(data, Mapping) or "op" not in data:
            raise ProgramError("each instruction must be an object with an 'op' field")
        return cls(str(data["op"]), {k: v for k, v in data.items() if k != "op"})


@dataclass(frozen=True, slots=True)
class Program:
    name: str
    instructions: tuple[Instruction, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ProgramError("program name must be non-empty")
        instructions = tuple(self.instructions)
        if not instructions:
            raise ProgramError("program must contain at least one instruction")
        if any(not isinstance(ins, Instruction) for ins in instructions):
            raise ProgramError("instructions must be Instruction instances")
        if not isinstance(self.metadata, Mapping):
            raise ProgramError("program metadata must be a mapping")
        object.__setattr__(self, "instructions", instructions)
        object.__setattr__(self, "metadata", _freeze_json(self.metadata))
        n = len(self.instructions)
        for index, ins in enumerate(self.instructions):
            if ins.opcode not in _SCHEMAS:
                raise ProgramError(f"instruction {index}: unsupported operation {ins.opcode}")
            if "target" in ins.args and not 0 <= ins.args["target"] < n:
                raise ProgramError(f"instruction {index}: target {ins.args['target']} is outside [0, {n-1}]")
        if not any(ins.opcode == "HALT" for ins in self.instructions):
            raise ProgramError("program must contain at least one HALT instruction")

    @property
    def instruction_set(self) -> frozenset[str]:
        return frozenset(ins.opcode for ins in self.instructions)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "instructions": [i.to_dict() for i in self.instructions],
                "metadata": _thaw_json(self.metadata)}

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Program":
        try:
            instructions = tuple(Instruction.from_dict(x) for x in data["instructions"])
            return cls(str(data["name"]), instructions, dict(data.get("metadata", {})))
        except (KeyError, TypeError) as exc:
            raise ProgramError(f"invalid program definition: {exc}") from exc

    @classmethod
    def from_json(cls, source: str) -> "Program":
        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise ProgramError(f"invalid program JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ProgramError("program JSON root must be an object")
        return cls.from_dict(data)
