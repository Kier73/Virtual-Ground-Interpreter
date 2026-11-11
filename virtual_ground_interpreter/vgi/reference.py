"""Independent semantic reference for captured Signal8 executions.

This module deliberately does not execute through Signal8Backend,
SignalStateMachine, or Program. It interprets the retained instruction
description over an abstract Z/8Z value plus a separate angular residual.
The runtime's phasors are checked against this independent representation.

The reference is bounded to the declared Signal8 instruction set and its
finite algebra. It is not a proof about external hardware or provenance.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any


TAU = 2.0 * math.pi
EPSILON = 1e-12
SUPPORTED_OPCODES = frozenset({
    "LOAD", "STORE", "MOVE", "REFRAME", "ADD", "SUB",
    "BRANCH_EQ", "BRANCH_IDENTITY", "JUMP", "EMIT", "HALT",
})


class ReferenceExecutionError(ValueError):
    """Invalid request to the independent Signal8 reference verifier."""


class _ReferenceUnsupported(Exception):
    """The retained observations do not justify a unique reference meaning."""


class _ReferenceFault(Exception):
    def __init__(self, exception_type: str):
        self.exception_type = exception_type
        super().__init__(exception_type)


@dataclass(frozen=True, slots=True)
class ReferenceExecutionReport:
    trace_id: str
    trace_fingerprint: str
    program_fingerprint: str
    ground_fingerprint: str
    numerical_tolerance_rad: float
    status: str
    checked_steps: int
    checked_writes: int
    decoded_inputs: int
    mismatches: tuple[str, ...] = ()
    unsupported_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("trace_fingerprint", "program_fingerprint", "ground_fingerprint"):
            value = getattr(self, name)
            if (not isinstance(value, str) or len(value) != 64
                    or value.lower() != value):
                raise ReferenceExecutionError(f"{name} must be a lowercase SHA-256 digest")
            try:
                int(value, 16)
            except ValueError as exc:
                raise ReferenceExecutionError(f"{name} must be a lowercase SHA-256 digest") from exc
        if (not isinstance(self.numerical_tolerance_rad, (int, float))
                or isinstance(self.numerical_tolerance_rad, bool)
                or not math.isfinite(float(self.numerical_tolerance_rad))
                or not 0.0 < float(self.numerical_tolerance_rad) <= 1e-3):
            raise ReferenceExecutionError("numerical_tolerance_rad must be in (0, 1e-3]")
        if self.status not in ("match", "mismatch", "unsupported"):
            raise ReferenceExecutionError("status must be match, mismatch, or unsupported")
        if self.status == "match" and self.mismatches:
            raise ReferenceExecutionError("a matching report cannot contain mismatches")
        if self.status == "mismatch" and not self.mismatches:
            raise ReferenceExecutionError("a mismatch report must contain a discrepancy")
        if self.status == "unsupported" and not self.unsupported_reason:
            raise ReferenceExecutionError("an unsupported report must explain its boundary")

    @property
    def matched(self) -> bool:
        return self.status == "match"

    @property
    def fingerprint(self) -> str:
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-IndependentSignal8Reference-1",
            "trace_id": self.trace_id,
            "trace_fingerprint": self.trace_fingerprint,
            "program_fingerprint": self.program_fingerprint,
            "ground_fingerprint": self.ground_fingerprint,
            "numerical_tolerance_rad": self.numerical_tolerance_rad,
            "status": self.status,
            "checked_steps": self.checked_steps,
            "checked_writes": self.checked_writes,
            "decoded_inputs": self.decoded_inputs,
            "mismatches": list(self.mismatches),
            "unsupported_reason": self.unsupported_reason,
            "scope": (
                "independent finite Z/8Z instruction semantics checked against the "
                "retained Signal8 execution events and final signal state"
            ),
            "limitations": [
                "the reference shares the declared instruction and Ground contract",
                "the reference does not authenticate the source or transport",
                "the reference does not establish behavior outside this finite Signal8 model",
            ],
        }


@dataclass(frozen=True, slots=True)
class _Meaning:
    """A semantic symbol, observer coordinate, residual angle, and bound."""

    symbol: int
    observer: int
    residual_rad: float
    error_bound_rad: float
    magnitude: float = 1.0

    def to_signal_record(self) -> dict[str, float | int]:
        centre = _phase_centre(self.symbol, self.observer)
        angle = centre + self.residual_rad
        return {
            "real": self.magnitude * math.cos(angle),
            "imag": self.magnitude * math.sin(angle),
            "observer": self.observer,
            "phase_error_bound": self.error_bound_rad,
        }


@dataclass(slots=True)
class _State:
    memory: dict[str, _Meaning]
    registers: dict[str, _Meaning]
    pc: int = 0
    halted: bool = False
    outputs: list[tuple[str, _Meaning]] | None = None

    def __post_init__(self) -> None:
        if self.outputs is None:
            self.outputs = []


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _wrap(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def _phase_centre(symbol: int, observer: int) -> float:
    return TAU * ((observer * symbol) % 8) / 8.0


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _ReferenceUnsupported(f"{label} is not a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise _ReferenceUnsupported(f"{label} is not finite")
    return result


def _decode_record(
    record: Mapping[str, Any],
    allowed_observers: tuple[int, ...],
    *,
    label: str,
) -> _Meaning:
    """Decode only a uniquely justified C8 symbol, retaining its residual."""
    try:
        real = _number(record["real"], f"{label}.real")
        imag = _number(record["imag"], f"{label}.imag")
        observer_value = record["observer"]
        if isinstance(observer_value, bool) or not isinstance(observer_value, int):
            raise _ReferenceUnsupported(f"{label}.observer is not an integer")
        observer = int(observer_value)
        error = _number(record.get("phase_error_bound", 0.0), f"{label}.phase_error_bound")
    except (KeyError, TypeError) as exc:
        raise _ReferenceUnsupported(f"{label} is not a complete signal record") from exc

    magnitude = math.hypot(real, imag)
    if not math.isfinite(magnitude) or abs(magnitude - 1.0) > 1e-7:
        raise _ReferenceUnsupported(f"{label} is not a normalized unit phasor")
    if observer not in allowed_observers:
        raise _ReferenceUnsupported(f"{label} uses an observer outside the declared Ground")
    if not 0.0 <= error <= math.pi:
        raise _ReferenceUnsupported(f"{label} has an invalid phase-error bound")

    angle = math.atan2(imag, real)
    candidates: list[tuple[int, float]] = []
    for symbol in range(8):
        residual = _wrap(angle - _phase_centre(symbol, observer))
        if abs(residual) <= math.pi / 8.0 + error + 1e-10:
            candidates.append((symbol, residual))

    if len(candidates) != 1:
        raise _ReferenceUnsupported(
            f"{label} does not identify one Z/8Z symbol under its phase bound "
            f"(candidate_count={len(candidates)})"
        )
    symbol, residual = candidates[0]
    if abs(residual) > error + 1e-8:
        raise _ReferenceUnsupported(
            f"{label} phase-error bound does not cover its measured residual"
        )
    return _Meaning(symbol, observer, residual, error, magnitude)


def _reframe(value: _Meaning, target: int, allowed_observers: tuple[int, ...]) -> _Meaning:
    if isinstance(target, bool) or not isinstance(target, int) or target not in allowed_observers:
        raise _ReferenceFault("ValueErrorVGI")
    exponent = (target * pow(value.observer, -1, 8)) % 8
    # The residue exponent transports the ideal C8 character exactly.
    # The continuous residual is multiplied by the integer exponent and can grow.
    return _Meaning(
        value.symbol,
        target,
        _wrap(exponent * value.residual_rad),
        min(math.pi, exponent * value.error_bound_rad),
    )


def _align(left: _Meaning, right: _Meaning,
           allowed_observers: tuple[int, ...]) -> tuple[_Meaning, _Meaning]:
    if left.observer == right.observer:
        return left, right
    return left, _reframe(right, left.observer, allowed_observers)


def _add(left: _Meaning, right: _Meaning,
         allowed_observers: tuple[int, ...]) -> _Meaning:
    a, b = _align(left, right, allowed_observers)
    return _Meaning(
        (a.symbol + b.symbol) % 8,
        a.observer,
        _wrap(a.residual_rad + b.residual_rad),
        min(math.pi, a.error_bound_rad + b.error_bound_rad),
    )


def _subtract(left: _Meaning, right: _Meaning,
              allowed_observers: tuple[int, ...]) -> _Meaning:
    a, b = _align(left, right, allowed_observers)
    return _Meaning(
        (a.symbol - b.symbol) % 8,
        a.observer,
        _wrap(a.residual_rad - b.residual_rad),
        min(math.pi, a.error_bound_rad + b.error_bound_rad),
    )


def _compare(left: _Meaning, right: _Meaning,
             tolerance: float,
             allowed_observers: tuple[int, ...]) -> tuple[bool | None, float, float, float, int]:
    a, b = _align(left, right, allowed_observers)
    phase_difference = (
        TAU * a.observer * (a.symbol - b.symbol) / 8.0
        + a.residual_rad - b.residual_rad
    )
    distance = abs(_wrap(phase_difference))
    uncertainty = min(math.pi, a.error_bound_rad + b.error_bound_rad)
    lower = max(0.0, distance - uncertainty)
    upper = min(math.pi, distance + uncertainty)
    if upper <= tolerance + EPSILON:
        result: bool | None = True
    elif lower > tolerance + EPSILON:
        result = False
    else:
        result = None
    return result, distance, uncertainty, lower, a.observer


def _get_register(state: _State, name: str) -> _Meaning:
    try:
        return state.registers[name]
    except KeyError as exc:
        raise _ReferenceFault("MissingRegister") from exc


def _event_for_step(
    state: _State,
    instruction: Mapping[str, Any],
    step_index: int,
    allowed_observers: tuple[int, ...],
) -> dict[str, Any]:
    op = instruction.get("op")
    args = {key: value for key, value in instruction.items() if key != "op"}
    if not isinstance(op, str) or op not in SUPPORTED_OPCODES:
        raise _ReferenceUnsupported(f"unsupported instruction {op!r}")

    pc_before = state.pc
    next_pc = pc_before + 1
    branch_result: bool | None = None
    branch_distance: float | None = None
    branch_uncertainty: float | None = None
    branch_lower: float | None = None
    branch_upper: float | None = None
    branch_tolerance: float | None = None
    branch_observer: int | None = None
    branch_operands: list[dict[str, float | int]] = []
    writes: list[str] = []
    write_values: list[dict[str, Any]] = []

    def record_write(location: str, value: _Meaning) -> None:
        writes.append(location)
        write_values.append({"location": location, "value": value.to_signal_record()})

    if op == "LOAD":
        address, destination = args["address"], args["dst"]
        if address not in state.memory:
            raise _ReferenceFault("MissingMemoryCell")
        value = state.memory[address]
        state.registers[destination] = value
        record_write(f"register:{destination}", value)

    elif op == "STORE":
        address, source = args["address"], args["src"]
        value = _get_register(state, source)
        state.memory[address] = value
        record_write(f"memory:{address}", value)

    elif op == "MOVE":
        destination, source = args["dst"], args["src"]
        value = _get_register(state, source)
        state.registers[destination] = value
        record_write(f"register:{destination}", value)

    elif op == "REFRAME":
        destination, source = args["dst"], args["src"]
        value = _reframe(
            _get_register(state, source), args["observer"], allowed_observers,
        )
        state.registers[destination] = value
        record_write(f"register:{destination}", value)

    elif op in ("ADD", "SUB"):
        destination = args["dst"]
        left = _get_register(state, args["left"])
        right = _get_register(state, args["right"])
        value = (
            _add(left, right, allowed_observers)
            if op == "ADD"
            else _subtract(left, right, allowed_observers)
        )
        state.registers[destination] = value
        record_write(f"register:{destination}", value)

    elif op == "BRANCH_EQ":
        left = _get_register(state, args["left"])
        right = _get_register(state, args["right"])
        tolerance = _number(args["tolerance_rad"], "BRANCH_EQ.tolerance_rad")
        decision, distance, uncertainty, lower, observer = _compare(
            left, right, tolerance, allowed_observers,
        )
        if decision is None:
            raise _ReferenceFault("AmbiguousBranchError")
        branch_operands = [left.to_signal_record(), right.to_signal_record()]
        branch_result = decision
        branch_distance = distance
        branch_uncertainty = uncertainty
        branch_lower = lower
        branch_upper = min(math.pi, distance + uncertainty)
        branch_tolerance = tolerance
        branch_observer = observer
        if decision:
            next_pc = int(args["target"])

    elif op == "BRANCH_IDENTITY":
        value = _get_register(state, args["src"])
        identity = _Meaning(0, value.observer, 0.0, 0.0)
        tolerance = _number(args["tolerance_rad"], "BRANCH_IDENTITY.tolerance_rad")
        decision, distance, uncertainty, lower, observer = _compare(
            value, identity, tolerance, allowed_observers,
        )
        if decision is None:
            raise _ReferenceFault("AmbiguousBranchError")
        branch_operands = [value.to_signal_record(), identity.to_signal_record()]
        branch_result = decision
        branch_distance = distance
        branch_uncertainty = uncertainty
        branch_lower = lower
        branch_upper = min(math.pi, distance + uncertainty)
        branch_tolerance = tolerance
        branch_observer = observer
        if decision:
            next_pc = int(args["target"])

    elif op == "JUMP":
        next_pc = int(args["target"])

    elif op == "EMIT":
        source = args["src"]
        label = str(args.get("label", source))
        value = _get_register(state, source)
        state.outputs.append((label, value))
        record_write(f"output:{label}", value)

    elif op == "HALT":
        state.halted = True

    state.pc = next_pc
    return {
        "step": step_index,
        "pc_before": pc_before,
        "opcode": op,
        "pc_after": state.pc,
        "branch_result": branch_result,
        "branch_distance_rad": branch_distance,
        "branch_uncertainty_rad": branch_uncertainty,
        "branch_lower_bound_rad": branch_lower,
        "branch_upper_bound_rad": branch_upper,
        "branch_tolerance_rad": branch_tolerance,
        "branch_observer": branch_observer,
        "branch_operands": branch_operands,
        "writes": writes,
        "write_values": write_values,
    }


def _deep_differences(expected: Any, actual: Any, path: str,
                      tolerance: float, limit: int = 40) -> list[str]:
    differences: list[str] = []

    def visit(left: Any, right: Any, current: str) -> None:
        if len(differences) >= limit:
            return
        if isinstance(left, Mapping) and isinstance(right, Mapping):
            left_keys, right_keys = set(left), set(right)
            for key in sorted(left_keys - right_keys):
                differences.append(f"{current}.{key}: missing from observed record")
            for key in sorted(right_keys - left_keys):
                differences.append(f"{current}.{key}: unexpected observed field")
            for key in sorted(left_keys & right_keys):
                visit(left[key], right[key], f"{current}.{key}")
            return
        if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
            if len(left) != len(right):
                differences.append(f"{current}: sequence length {len(right)} != expected {len(left)}")
                return
            for index, (a, b) in enumerate(zip(left, right)):
                visit(a, b, f"{current}[{index}]")
            return
        if (isinstance(left, (int, float)) and not isinstance(left, bool)
                and isinstance(right, (int, float)) and not isinstance(right, bool)):
            if not math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance):
                differences.append(f"{current}: observed {right!r} != reference {left!r}")
            return
        if left != right:
            differences.append(f"{current}: observed {right!r} != reference {left!r}")

    visit(expected, actual, path)
    return differences


def _reference_snapshot(state: _State, initial_memory: Mapping[str, _Meaning]) -> dict[str, Any]:
    return {
        "pc": state.pc,
        "halted": state.halted,
        "initial_memory": {
            key: value.to_signal_record() for key, value in sorted(initial_memory.items())
        },
        "memory": {
            key: value.to_signal_record() for key, value in sorted(state.memory.items())
        },
        "registers": {
            key: value.to_signal_record() for key, value in sorted(state.registers.items())
        },
        "outputs": [
            {"label": label, "value": value.to_signal_record()}
            for label, value in state.outputs
        ],
    }


def verify_execution_reference(
    trace: Any,
    *,
    angular_tolerance_rad: float = 1e-8,
) -> ReferenceExecutionReport:
    """Check a retained Signal8 trace against independent Z/8Z semantics.

    The initial phasor of each memory cell must uniquely identify one C8
    symbol under its declared phase-error bound. Once admitted at that
    boundary, operations are interpreted in the abstract cyclic group while
    continuous residual phase and uncertainty are propagated separately.

    Returns unsupported rather than guessing when the initial representation
    has no unique semantic symbol.
    """
    required = (
        "trace_id", "fingerprint", "program_fingerprint", "ground_fingerprint",
        "status", "max_steps", "program_definition", "ground_definition",
        "initial_memory", "entries", "exchange", "final_snapshot",
    )
    if any(not hasattr(trace, name) for name in required):
        raise ReferenceExecutionError("trace is not a canonical Signal8ExecutionTrace")
    if (isinstance(angular_tolerance_rad, bool)
            or not isinstance(angular_tolerance_rad, (int, float))
            or not math.isfinite(float(angular_tolerance_rad))):
        raise ReferenceExecutionError("angular_tolerance_rad must be a finite number")
    tolerance = float(angular_tolerance_rad)
    if tolerance <= 0.0 or tolerance > 1e-3:
        raise ReferenceExecutionError("angular_tolerance_rad must be in (0, 1e-3]")

    trace_id = str(trace.trace_id)
    trace_fingerprint = str(trace.fingerprint)
    program_fingerprint = str(trace.program_fingerprint)
    ground_fingerprint = str(trace.ground_fingerprint)
    try:
        program = _plain(trace.program_definition)
        ground = _plain(trace.ground_definition)
        initial_records = _plain(trace.initial_memory)
        instructions = program["instructions"]
        if not isinstance(instructions, list) or not instructions:
            raise _ReferenceUnsupported("program has no retained instruction sequence")
        if ground.get("domain_id") != "signal.phase.cyclic.z8.v1":
            raise _ReferenceUnsupported("reference executor supports only signal.phase.cyclic.z8.v1")
        allowed_observers = tuple(ground.get("observer_profiles", ()))
        if not allowed_observers or any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in allowed_observers
        ):
            raise _ReferenceUnsupported("Ground has no valid finite observer profile")
        if any(value not in (1, 3, 5, 7) for value in allowed_observers):
            raise _ReferenceUnsupported(
                "the declared observer profiles are not units of Z/8Z"
            )
        declared_ops = set(ground.get("instruction_set", ()))
        for index, instruction in enumerate(instructions):
            if not isinstance(instruction, Mapping):
                raise _ReferenceUnsupported(f"instruction {index} is not an object")
            opcode = instruction.get("op")
            if opcode not in SUPPORTED_OPCODES or opcode not in declared_ops:
                raise _ReferenceUnsupported(f"instruction {index} is outside the reference contract")
        initial_memory = {
            key: _decode_record(value, allowed_observers, label=f"initial_memory[{key!r}]")
            for key, value in initial_records.items()
        }
    except _ReferenceUnsupported as exc:
        return ReferenceExecutionReport(
            trace_id=trace_id,
            trace_fingerprint=trace_fingerprint,
            program_fingerprint=program_fingerprint,
            ground_fingerprint=ground_fingerprint,
            numerical_tolerance_rad=tolerance,
            status="unsupported",
            checked_steps=0,
            checked_writes=0,
            decoded_inputs=0,
            unsupported_reason=str(exc),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ReferenceExecutionError(f"invalid retained Signal8 trace: {exc}") from exc

    state = _State(dict(initial_memory), {})
    messages = {message.message_id: message for message in trace.exchange.messages}
    mismatches: list[str] = []
    checked_steps = 0
    checked_writes = 0
    failure: tuple[int, str] | None = None

    for step_index in range(int(trace.max_steps)):
        if state.halted:
            break
        if not 0 <= state.pc < len(instructions):
            failure = (state.pc, "RuntimeErrorVGI")
            break

        instruction = instructions[state.pc]
        before_memory = dict(state.memory)
        before_registers = dict(state.registers)
        before_pc = state.pc
        before_halted = state.halted
        before_outputs = list(state.outputs)

        try:
            expected_event = _event_for_step(
                state, instruction, step_index, allowed_observers,
            )
        except _ReferenceFault as exc:
            state.memory = before_memory
            state.registers = before_registers
            state.pc = before_pc
            state.halted = before_halted
            state.outputs = before_outputs
            failure = (state.pc, exc.exception_type)
        except _ReferenceUnsupported as exc:
            state.memory = before_memory
            state.registers = before_registers
            state.pc = before_pc
            state.halted = before_halted
            state.outputs = before_outputs
            return ReferenceExecutionReport(
                trace_id=trace_id,
                trace_fingerprint=trace_fingerprint,
                program_fingerprint=program_fingerprint,
                ground_fingerprint=ground_fingerprint,
                numerical_tolerance_rad=tolerance,
                status="mismatch" if mismatches else "unsupported",
                checked_steps=checked_steps,
                checked_writes=checked_writes,
                decoded_inputs=len(initial_memory),
                mismatches=tuple(mismatches[:80]),
                unsupported_reason=None if mismatches else str(exc),
            )

        if failure is not None:
            if checked_steps >= len(trace.entries):
                mismatches.append("reference fault occurred without a retained failure frame")
                break
            frame = trace.entries[checked_steps]
            message = messages.get(frame.message_id)
            payload = None if message is None else _plain(message.payload)
            if frame.record_type != "execution_failure":
                mismatches.append(
                    f"step {step_index}: reference fault {failure[1]} but runtime retained a successful step"
                )
            elif payload is None:
                mismatches.append(f"step {step_index}: failed attempt has no retained message")
            else:
                if payload.get("exception_type") != failure[1]:
                    mismatches.append(
                        f"step {step_index}: exception type {payload.get('exception_type')!r} "
                        f"!= reference {failure[1]!r}"
                    )
                if payload.get("pc") != failure[0]:
                    mismatches.append(f"step {step_index}: failed PC differs")
                if payload.get("step_index") != step_index:
                    mismatches.append(f"step {step_index}: failed attempt index differs")
                if _plain(payload.get("instruction", {})) != _plain(instruction):
                    mismatches.append(f"step {step_index}: failed instruction differs")
            checked_steps += 1
            break

        if checked_steps >= len(trace.entries):
            mismatches.append(f"step {step_index}: reference produced an unretained successful step")
            break

        frame = trace.entries[checked_steps]
        message = messages.get(frame.message_id)
        payload = None if message is None else _plain(message.payload)
        checked_steps += 1
        if frame.record_type != "execution_step":
            mismatches.append(f"step {step_index}: runtime retained a failure where reference succeeded")
            continue
        if payload is None:
            mismatches.append(f"step {step_index}: successful step has no retained message")
            continue
        if frame.step_index != step_index or frame.sequence != step_index + 1:
            mismatches.append(f"step {step_index}: frame sequence or instruction index differs")
        if payload.get("step_index") != step_index:
            mismatches.append(f"step {step_index}: message instruction index differs")
        if _plain(payload.get("instruction", {})) != _plain(instruction):
            mismatches.append(f"step {step_index}: retained instruction differs")
        mismatches.extend(_deep_differences(
            expected_event, payload.get("event"), f"step[{step_index}].event", tolerance,
        ))
        if payload.get("pc_before") != expected_event["pc_before"]:
            mismatches.append(f"step {step_index}: pc_before differs")
        if payload.get("pc_after") != expected_event["pc_after"]:
            mismatches.append(f"step {step_index}: pc_after differs")
        if payload.get("opcode") != expected_event["opcode"]:
            mismatches.append(f"step {step_index}: opcode differs")
        checked_writes += len(expected_event["writes"])

    if len(trace.entries) != checked_steps:
        mismatches.append(
            f"trace frame count {len(trace.entries)} != independently checked attempts {checked_steps}"
        )

    expected_status = (
        "failed" if failure is not None
        else "completed" if state.halted
        else "step_limit"
    )
    if trace.status != expected_status:
        mismatches.append(
            f"trace status {trace.status!r} != reference status {expected_status!r}"
        )

    expected_snapshot = _reference_snapshot(state, initial_memory)
    supplied_snapshot = _plain(trace.final_snapshot)
    for field in ("pc", "halted", "initial_memory", "memory", "registers", "outputs"):
        mismatches.extend(_deep_differences(
            expected_snapshot[field], supplied_snapshot.get(field),
            f"final_snapshot.{field}", tolerance,
        ))

    return ReferenceExecutionReport(
        trace_id=trace_id,
        trace_fingerprint=trace_fingerprint,
        program_fingerprint=program_fingerprint,
        ground_fingerprint=ground_fingerprint,
        numerical_tolerance_rad=tolerance,
        status="mismatch" if mismatches else "match",
        checked_steps=checked_steps,
        checked_writes=checked_writes,
        decoded_inputs=len(initial_memory),
        mismatches=tuple(mismatches[:80]),
    )
