"""Deterministic signal-state machine and interpreter runtime."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from .compiler import TaskSpec

from .ground import GroundSpec, SIGNAL8_GROUND, GroundError
from .ir import Program, Instruction, ProgramError
from .values import Signal8Backend, SignalValue, EqualityDecision, ValueErrorVGI


class RuntimeErrorVGI(RuntimeError):
    pass


class MissingRegister(RuntimeErrorVGI):
    pass


class MissingMemoryCell(RuntimeErrorVGI):
    pass


class AmbiguousBranchError(RuntimeErrorVGI):
    def __init__(self, pc: int, decision: EqualityDecision):
        self.pc = pc
        self.decision = decision
        super().__init__(
            f"branch at pc={pc} is indeterminate: distance={decision.distance_rad:.6g}, "
            f"uncertainty={decision.uncertainty_rad:.6g}, tolerance={decision.tolerance_rad:.6g} rad"
        )


class StepLimitExceeded(RuntimeErrorVGI):
    pass


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    step: int
    pc_before: int
    opcode: str
    pc_after: int
    branch_result: bool | None = None
    branch_distance_rad: float | None = None
    branch_uncertainty_rad: float | None = None
    branch_lower_bound_rad: float | None = None
    branch_upper_bound_rad: float | None = None
    branch_tolerance_rad: float | None = None
    branch_observer: int | None = None
    branch_operands: tuple[SignalValue, ...] = ()
    writes: tuple[str, ...] = ()
    write_values: tuple[tuple[str, SignalValue], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step, "pc_before": self.pc_before, "opcode": self.opcode,
            "pc_after": self.pc_after, "branch_result": self.branch_result,
            "branch_distance_rad": self.branch_distance_rad,
            "branch_uncertainty_rad": self.branch_uncertainty_rad,
            "branch_lower_bound_rad": self.branch_lower_bound_rad,
            "branch_upper_bound_rad": self.branch_upper_bound_rad,
            "branch_tolerance_rad": self.branch_tolerance_rad,
            "branch_observer": self.branch_observer,
            "branch_operands": [v.to_dict() for v in self.branch_operands],
            "writes": list(self.writes),
            "write_values": [{"location": key, "value": value.to_dict()}
                             for key, value in self.write_values],
        }


@dataclass(frozen=True, slots=True)
class Emission:
    label: str
    value: SignalValue


class VirtualGroundInterpreter:
    """Interpreter for programs running against a declared executable Ground."""

    def __init__(self, ground: GroundSpec = SIGNAL8_GROUND,
                 backend: Signal8Backend | None = None):
        self.ground = ground
        self.backend = backend or Signal8Backend()
        if self.backend.domain_id != ground.domain_id:
            raise GroundError(f"backend domain {self.backend.domain_id!r} does not match ground {ground.domain_id!r}")
        if tuple(self.backend.observer_profiles) != tuple(ground.observer_profiles):
            raise GroundError("backend observer profiles do not match GroundSpec")

    def instantiate(self, program: Program,
                    initial_memory: Mapping[str, SignalValue] | None = None) -> "SignalStateMachine":
        unsupported = program.instruction_set - set(self.ground.instruction_set)
        if unsupported:
            raise GroundError(f"program uses instructions not declared by Ground: {sorted(unsupported)}")
        memory = dict(initial_memory or {})
        for address, value in memory.items():
            if not isinstance(address, str) or not address:
                raise RuntimeErrorVGI("memory addresses must be non-empty strings")
            self._validate_value(value)
        return SignalStateMachine(self, program, memory)

    def _validate_value(self, value: SignalValue) -> None:
        if not isinstance(value, SignalValue):
            raise RuntimeErrorVGI("all memory values must be SignalValue instances")
        if value.observer not in self.ground.observer_profiles:
            raise RuntimeErrorVGI(f"observer {value.observer} is not allowed by this Ground")

    def compile_task(self, task: "TaskSpec") -> Program:
        """Lower a supported typed TaskSpec into this Ground's instruction IR."""
        from .compiler import TaskCompiler, TaskSpec
        if not isinstance(task, TaskSpec):
            raise TypeError("compile_task expects a TaskSpec")
        return TaskCompiler().compile(task)

    def interpret(self, task: "TaskSpec", initial_memory: Mapping[str, SignalValue] | None = None,
                  *, max_steps: int = 10_000) -> "ExecutionResult":
        """Compile a typed TaskSpec and execute it against this Ground."""
        program = self.compile_task(task)
        return self.execute(program, initial_memory, max_steps=max_steps)

    def execute(self, program: Program, initial_memory: Mapping[str, SignalValue] | None = None,
                *, max_steps: int = 10_000) -> "ExecutionResult":
        machine = self.instantiate(program, initial_memory)
        return machine.run(max_steps=max_steps)


class SignalStateMachine:
    """Persistent memory, register file, control state, and reversible step journal."""

    def __init__(self, interpreter: VirtualGroundInterpreter, program: Program,
                 initial_memory: Mapping[str, SignalValue]):
        self.interpreter = interpreter
        self.program = program
        self.initial_memory = dict(initial_memory)
        self.memory = dict(initial_memory)
        self.registers: dict[str, SignalValue] = {}
        self.pc = 0
        self.halted = False
        self.outputs: list[Emission] = []
        self.trace: list[ExecutionEvent] = []
        self._undo_stack: list[dict[str, Any]] = []
        self._program_fingerprint = hashlib.sha256(
            json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _reg(self, name: str) -> SignalValue:
        try:
            return self.registers[name]
        except KeyError as exc:
            raise MissingRegister(f"register {name!r} has not been initialized") from exc

    def _snapshot(self) -> dict[str, Any]:
        return {
            "memory": dict(self.memory), "registers": dict(self.registers),
            "pc": self.pc, "halted": self.halted,
            "outputs_len": len(self.outputs), "trace_len": len(self.trace),
        }

    def _restore(self, snapshot: Mapping[str, Any]) -> None:
        self.memory = dict(snapshot["memory"])
        self.registers = dict(snapshot["registers"])
        self.pc = int(snapshot["pc"])
        self.halted = bool(snapshot["halted"])
        del self.outputs[int(snapshot["outputs_len"]):]
        del self.trace[int(snapshot["trace_len"]):]

    def step(self) -> ExecutionEvent | None:
        if self.halted:
            return None
        if not 0 <= self.pc < len(self.program.instructions):
            raise RuntimeErrorVGI(f"program counter {self.pc} escaped the instruction stream without HALT")
        before = self._snapshot()
        pc_before = self.pc
        ins = self.program.instructions[self.pc]
        a = ins.args
        branch_result = None
        branch_distance = None
        branch_uncertainty = None
        branch_lower_bound = None
        branch_upper_bound = None
        branch_tolerance = None
        branch_observer = None
        branch_operands: tuple[SignalValue, ...] = ()
        writes: list[str] = []
        write_values: list[tuple[str, SignalValue]] = []
        try:
            op = ins.opcode
            next_pc = self.pc + 1
            if op == "LOAD":
                address, dst = a["address"], a["dst"]
                if address not in self.memory:
                    raise MissingMemoryCell(f"memory cell {address!r} does not exist")
                value = self.memory[address]
                self.registers[dst] = value
                writes.append(f"register:{dst}")
                write_values.append((f"register:{dst}", value))
            elif op == "STORE":
                address, src = a["address"], a["src"]
                value = self._reg(src)
                self.memory[address] = value
                writes.append(f"memory:{address}")
                write_values.append((f"memory:{address}", value))
            elif op == "MOVE":
                dst, src = a["dst"], a["src"]
                value = self._reg(src)
                self.registers[dst] = value
                writes.append(f"register:{dst}")
                write_values.append((f"register:{dst}", value))
            elif op == "REFRAME":
                dst, src = a["dst"], a["src"]
                value = self.interpreter.backend.reframe(self._reg(src), int(a["observer"]))
                self.interpreter._validate_value(value)
                self.registers[dst] = value
                writes.append(f"register:{dst}")
                write_values.append((f"register:{dst}", value))
            elif op in ("ADD", "SUB"):
                dst = a["dst"]
                left, right = self._reg(a["left"]), self._reg(a["right"])
                fn = self.interpreter.backend.add if op == "ADD" else self.interpreter.backend.sub
                value = fn(left, right)
                self.registers[dst] = value
                writes.append(f"register:{dst}")
                write_values.append((f"register:{dst}", value))
            elif op == "BRANCH_EQ":
                branch_left, branch_right = self._reg(a["left"]), self._reg(a["right"])
                decision = self.interpreter.backend.compare_equal(
                    branch_left, branch_right, float(a["tolerance_rad"]))
                branch_operands = (branch_left, branch_right)
                branch_lower_bound = decision.lower_bound_rad
                branch_upper_bound = decision.upper_bound_rad
                branch_tolerance = decision.tolerance_rad
                branch_observer = branch_left.observer
                if decision.result is None:
                    raise AmbiguousBranchError(self.pc, decision)
                branch_result = decision.result
                branch_distance = decision.distance_rad
                branch_uncertainty = decision.uncertainty_rad
                if decision.result:
                    next_pc = int(a["target"])
            elif op == "BRANCH_IDENTITY":
                branch_value = self._reg(a["src"])
                decision = self.interpreter.backend.compare_identity(
                    branch_value, float(a["tolerance_rad"]))
                branch_operands = (branch_value, SignalValue(1.0 + 0.0j, branch_value.observer, 0.0))
                branch_lower_bound = decision.lower_bound_rad
                branch_upper_bound = decision.upper_bound_rad
                branch_tolerance = decision.tolerance_rad
                branch_observer = branch_value.observer
                if decision.result is None:
                    raise AmbiguousBranchError(self.pc, decision)
                branch_result = decision.result
                branch_distance = decision.distance_rad
                branch_uncertainty = decision.uncertainty_rad
                if decision.result:
                    next_pc = int(a["target"])
            elif op == "JUMP":
                next_pc = int(a["target"])
            elif op == "EMIT":
                src = a["src"]
                label = str(a.get("label", src))
                value = self._reg(src)
                self.outputs.append(Emission(label, value))
                writes.append(f"output:{label}")
                write_values.append((f"output:{label}", value))
            elif op == "HALT":
                self.halted = True
            else:  # Program validation should make this unreachable.
                raise RuntimeErrorVGI(f"unsupported opcode at runtime: {op}")

            self.pc = next_pc
            event = ExecutionEvent(len(self.trace), pc_before, op, self.pc,
                                   branch_result, branch_distance, branch_uncertainty,
                                   branch_lower_bound, branch_upper_bound,
                                   branch_tolerance, branch_observer, branch_operands,
                                   tuple(writes), tuple(write_values))
            self.trace.append(event)
            self._undo_stack.append(before)
            return event
        except Exception:
            self._restore(before)
            raise

    def run(self, *, max_steps: int = 10_000) -> "ExecutionResult":
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        steps = 0
        while not self.halted and steps < max_steps:
            self.step()
            steps += 1
        if not self.halted:
            raise StepLimitExceeded(f"execution paused after {steps} steps at pc={self.pc}")
        return self.result()

    def reset(self) -> None:
        """Return the machine to its initial memory and control state."""
        self.memory = dict(self.initial_memory)
        self.registers.clear()
        self.pc = 0
        self.halted = False
        self.outputs.clear()
        self.trace.clear()
        self._undo_stack.clear()

    def undo(self) -> ExecutionEvent:
        if not self._undo_stack:
            raise RuntimeErrorVGI("there is no execution step to undo")
        event = self.trace[-1]
        snapshot = self._undo_stack.pop()
        self._restore(snapshot)
        return event

    def result(self) -> "ExecutionResult":
        return ExecutionResult(tuple(self.outputs), tuple(self.trace), self.halted,
                               self.pc, self._program_fingerprint, self.interpreter.ground.fingerprint)

    def snapshot(self) -> dict[str, Any]:
        """Serialize a resumable machine checkpoint (program must be supplied on restore)."""
        payload = {
            "schema": "vgi.machine-snapshot.v1",
            "program_fingerprint": self._program_fingerprint,
            "ground_fingerprint": self.interpreter.ground.fingerprint,
            "pc": self.pc,
            "halted": self.halted,
            "initial_memory": {k: v.to_dict() for k, v in sorted(self.initial_memory.items())},
            "memory": {k: v.to_dict() for k, v in sorted(self.memory.items())},
            "registers": {k: v.to_dict() for k, v in sorted(self.registers.items())},
            "outputs": [{"label": x.label, "value": x.value.to_dict()} for x in self.outputs],
            "trace": [e.to_dict() for e in self.trace],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        payload["state_digest"] = hashlib.sha256(canonical).hexdigest()
        return payload

    @classmethod
    def restore(cls, interpreter: VirtualGroundInterpreter, program: Program,
                snapshot: Mapping[str, Any]) -> "SignalStateMachine":
        machine = cls(interpreter, program, {})
        expected_program = machine._program_fingerprint
        if snapshot.get("schema") != "vgi.machine-snapshot.v1":
            raise RuntimeErrorVGI("unsupported snapshot schema")
        supplied_digest = snapshot.get("state_digest")
        payload = {k: v for k, v in snapshot.items() if k != "state_digest"}
        actual_digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if supplied_digest != actual_digest:
            raise RuntimeErrorVGI("snapshot state digest mismatch")
        if snapshot.get("program_fingerprint") != expected_program:
            raise RuntimeErrorVGI("snapshot belongs to a different program")
        if snapshot.get("ground_fingerprint") != interpreter.ground.fingerprint:
            raise RuntimeErrorVGI("snapshot belongs to a different Ground specification")
        try:
            machine.pc = int(snapshot["pc"])
            machine.halted = bool(snapshot["halted"])
            machine.initial_memory = {k: SignalValue.from_dict(v) for k, v in snapshot["initial_memory"].items()}
            machine.memory = {k: SignalValue.from_dict(v) for k, v in snapshot["memory"].items()}
            machine.registers = {k: SignalValue.from_dict(v) for k, v in snapshot["registers"].items()}
            machine.outputs = [Emission(x["label"], SignalValue.from_dict(x["value"]))
                               for x in snapshot["outputs"]]
            machine.trace = [ExecutionEvent(
                int(x["step"]), int(x["pc_before"]), str(x["opcode"]), int(x["pc_after"]),
                x.get("branch_result"), x.get("branch_distance_rad"),
                x.get("branch_uncertainty_rad"), x.get("branch_lower_bound_rad"),
                x.get("branch_upper_bound_rad"), x.get("branch_tolerance_rad"),
                x.get("branch_observer"),
                tuple(SignalValue.from_dict(v) for v in x.get("branch_operands", ())),
                tuple(x.get("writes", ())),
                tuple((item["location"], SignalValue.from_dict(item["value"]))
                      for item in x.get("write_values", ())))
                for x in snapshot["trace"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeErrorVGI(f"invalid machine snapshot: {exc}") from exc
        for value in [*machine.initial_memory.values(), *machine.memory.values(),
                      *machine.registers.values(), *(x.value for x in machine.outputs),
                      *(v for event in machine.trace for _, v in event.write_values),
                      *(v for event in machine.trace for v in event.branch_operands)]:
            interpreter._validate_value(value)
        if not 0 <= machine.pc <= len(program.instructions):
            raise RuntimeErrorVGI("snapshot program counter is invalid")
        # History before the snapshot is intentionally not synthesized; new steps remain undoable.
        return machine


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    outputs: tuple[Emission, ...]
    trace: tuple[ExecutionEvent, ...]
    halted: bool
    final_pc: int
    program_fingerprint: str
    ground_fingerprint: str

    def observed_outputs(self, backend: Signal8Backend | None = None) -> dict[str, int]:
        observer = backend or Signal8Backend()
        return {item.label: observer.observe_symbol(item.value) for item in self.outputs}

    def trace_dicts(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.trace]
