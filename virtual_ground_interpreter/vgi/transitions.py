"""First-class partial predictive grounds and a bounded VGI IR compiler."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .ir import Instruction, Program
from .values import Signal8Backend, SignalValue


class TransitionSystemError(ValueError):
    """Invalid or unresolved predictive transition-system operation."""


class UnknownTransitionError(TransitionSystemError):
    def __init__(self, source: str, action: str):
        self.source, self.action = source, action
        super().__init__(f"transition is unknown for state={source!r}, action={action!r}")


class AmbiguousTransitionError(TransitionSystemError):
    def __init__(self, source: str, action: str, outcomes: tuple["TransitionOutcome", ...]):
        self.source, self.action, self.outcomes = source, action, outcomes
        super().__init__(f"transition is ambiguous for state={source!r}, action={action!r}")


class TransitionCompileError(TransitionSystemError):
    """The current Signal8 compiler cannot faithfully lower this Ground."""


class TransitionExecutionError(RuntimeError):
    """A compiled path did not emit the complete semantic trace it promised."""


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TransitionSystemError("metadata keys must be strings")
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        raise TransitionSystemError("metadata numbers must be finite")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TransitionSystemError(f"metadata must be JSON-compatible, got {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class TransitionOutcome:
    target: str
    output: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.target, str) or not self.target:
            raise TransitionSystemError("transition target must be a non-empty state name")
        output = tuple(self.output)
        for value in output:
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 7:
                raise TransitionSystemError("each finite output channel must be an integer in Z/8Z")
        object.__setattr__(self, "output", output)


@dataclass(frozen=True, slots=True)
class TransitionObservation:
    source: str
    action: str
    outcomes: tuple[TransitionOutcome, ...]
    support_count: int = 1
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source:
            raise TransitionSystemError("transition source must be a non-empty state name")
        if not isinstance(self.action, str) or not self.action:
            raise TransitionSystemError("transition action must be a non-empty action name")
        outcomes = tuple(self.outcomes)
        if not outcomes or any(not isinstance(item, TransitionOutcome) for item in outcomes):
            raise TransitionSystemError("an observation must contain at least one TransitionOutcome")
        if len(set(outcomes)) != len(outcomes):
            raise TransitionSystemError("duplicate outcomes must be consolidated, not repeated")
        if isinstance(self.support_count, bool) or not isinstance(self.support_count, int):
            raise TransitionSystemError("support_count must be an integer")
        if self.support_count < len(outcomes):
            raise TransitionSystemError("support_count cannot be smaller than the number of alternatives")
        evidence = tuple(self.evidence)
        if any(not isinstance(item, str) or not item for item in evidence):
            raise TransitionSystemError("evidence references must be non-empty strings")
        object.__setattr__(self, "outcomes", outcomes)
        object.__setattr__(self, "evidence", evidence)

    @property
    def status(self) -> str:
        return "known" if len(self.outcomes) == 1 else "ambiguous"


@dataclass(frozen=True, slots=True)
class TransitionStep:
    index: int
    source: str
    action: str
    target: str
    output: tuple[int, ...]
    support_count: int
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TransitionRun:
    initial_state: str
    final_state: str
    steps: tuple[TransitionStep, ...]

    @property
    def state_trace(self) -> tuple[str, ...]:
        return tuple(step.target for step in self.steps)

    @property
    def outputs(self) -> tuple[tuple[int, ...], ...]:
        return tuple(step.output for step in self.steps)


@dataclass(frozen=True, slots=True)
class GroundTransitionSystem:
    """Predictive contexts and evidence-backed action/output transitions.

    Predictive contexts are observer-relative distinctions, not assertions about
    physical hidden-state identity. Missing pairs are unknown; multiple
    alternatives are ambiguous; only singleton outcomes are executable.
    """

    states: tuple[str, ...]
    actions: tuple[str, ...]
    initial_state: str
    channels: tuple[str, ...]
    observations: tuple[TransitionObservation, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    _lookup: Mapping[tuple[str, str], TransitionObservation] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        states, actions = tuple(self.states), tuple(self.actions)
        channels, observations = tuple(self.channels), tuple(self.observations)
        if not states or any(not isinstance(x, str) or not x for x in states):
            raise TransitionSystemError("states must contain non-empty names")
        if len(set(states)) != len(states):
            raise TransitionSystemError("state names must be unique")
        if not actions or any(not isinstance(x, str) or not x for x in actions):
            raise TransitionSystemError("actions must contain non-empty names")
        if len(set(actions)) != len(actions):
            raise TransitionSystemError("action names must be unique")
        if any(not isinstance(x, str) or not x for x in channels) or len(set(channels)) != len(channels):
            raise TransitionSystemError("channel names must be unique non-empty strings")
        if self.initial_state not in states:
            raise TransitionSystemError("initial_state must be declared in states")
        lookup: dict[tuple[str, str], TransitionObservation] = {}
        for item in observations:
            if not isinstance(item, TransitionObservation):
                raise TransitionSystemError("observations must be TransitionObservation instances")
            if item.source not in states or item.action not in actions:
                raise TransitionSystemError("observation refers to an undeclared state or action")
            if any(outcome.target not in states for outcome in item.outcomes):
                raise TransitionSystemError("outcome refers to an undeclared successor state")
            if any(len(outcome.output) != len(channels) for outcome in item.outcomes):
                raise TransitionSystemError("outcome width does not match the declared channel schema")
            key = (item.source, item.action)
            if key in lookup:
                raise TransitionSystemError(f"duplicate observation record for {key!r}")
            lookup[key] = item
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "metadata", _freeze_json(dict(self.metadata)))
        object.__setattr__(self, "_lookup", MappingProxyType(lookup))

    @property
    def complete(self) -> bool:
        return (
            len(self._lookup) == len(self.states) * len(self.actions)
            and all(item.status == "known" for item in self.observations)
        )

    @property
    def unknown_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (state, action) for state in self.states for action in self.actions
            if (state, action) not in self._lookup
        )

    @property
    def ambiguous_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (item.source, item.action) for item in self.observations
            if item.status == "ambiguous"
        )

    def status(self, source: str, action: str) -> str:
        if source not in self.states or action not in self.actions:
            raise TransitionSystemError("query uses an undeclared state or action")
        item = self._lookup.get((source, action))
        return "unknown" if item is None else item.status

    def step(self, source: str, action: str, *, index: int = 0) -> TransitionStep:
        if source not in self.states:
            raise TransitionSystemError(f"unknown predictive state {source!r}")
        if action not in self.actions:
            raise TransitionSystemError(f"unknown action {action!r}")
        item = self._lookup.get((source, action))
        if item is None:
            raise UnknownTransitionError(source, action)
        if item.status == "ambiguous":
            raise AmbiguousTransitionError(source, action, item.outcomes)
        outcome = item.outcomes[0]
        return TransitionStep(index, source, action, outcome.target, outcome.output,
                              item.support_count, item.evidence)

    def run(self, actions: Sequence[str]) -> TransitionRun:
        if isinstance(actions, str):
            raise TransitionSystemError("actions must be a sequence of action names, not one string")
        current = self.initial_state
        steps = []
        for index, action in enumerate(actions):
            event = self.step(current, action, index=index)
            steps.append(event)
            current = event.target
        return TransitionRun(self.initial_state, current, tuple(steps))

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-TransitionSystem-1",
            "states": list(self.states),
            "actions": list(self.actions),
            "initial_state": self.initial_state,
            "channels": list(self.channels),
            "observations": [
                {
                    "source": item.source, "action": item.action,
                    "outcomes": [
                        {"target": outcome.target, "output": list(outcome.output)}
                        for outcome in item.outcomes
                    ],
                    "support_count": item.support_count,
                    "evidence": list(item.evidence),
                }
                for item in self.observations
            ],
            "metadata": _thaw_json(self.metadata),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GroundTransitionSystem":
        if not isinstance(data, Mapping) or data.get("format") != "VGI-TransitionSystem-1":
            raise TransitionSystemError("expected VGI-TransitionSystem-1")
        observations = []
        for raw in data.get("observations", ()):
            outcomes = tuple(
                TransitionOutcome(str(row["target"]), tuple(row["output"]))
                for row in raw.get("outcomes", ())
            )
            observations.append(TransitionObservation(
                str(raw["source"]), str(raw["action"]), outcomes,
                int(raw.get("support_count", 1)), tuple(raw.get("evidence", ())),
            ))
        return cls(
            tuple(data["states"]), tuple(data["actions"]), str(data["initial_state"]),
            tuple(data.get("channels", ())), tuple(observations), data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, source: str) -> "GroundTransitionSystem":
        try:
            return cls.from_dict(json.loads(source))
        except json.JSONDecodeError as exc:
            raise TransitionSystemError(f"invalid transition-system JSON: {exc}") from exc

    @classmethod
    def from_predictive_mealy_dict(cls, data: Mapping[str, Any]) -> "GroundTransitionSystem":
        """Import a Build 24 VG-PredictiveMealy-1 model without hidden state."""
        if not isinstance(data, Mapping):
            raise TransitionSystemError("predictive Mealy input must be an object")
        payload = data.get("specification", data)
        if not isinstance(payload, Mapping) or payload.get("format") != "VG-PredictiveMealy-1":
            raise TransitionSystemError("expected legacy format VG-PredictiveMealy-1")
        transitions, outputs = payload.get("transitions"), payload.get("outputs")
        actions = tuple(payload.get("actions", ()))
        if not isinstance(transitions, Mapping) or not isinstance(outputs, Mapping):
            raise TransitionSystemError("predictive Mealy input requires transitions and outputs maps")
        states = tuple(str(state) for state in transitions.keys())
        if not states:
            raise TransitionSystemError("predictive Mealy input declares no states")
        width = None
        for state in transitions:
            row = outputs.get(state, {})
            if isinstance(row, Mapping):
                for vector in row.values():
                    if isinstance(vector, (list, tuple)):
                        width = len(vector)
                        break
            if width is not None:
                break
        raw_channels = payload.get("channels")
        channels = tuple(raw_channels) if raw_channels is not None else tuple(
            f"channel_{index}" for index in range(width or 0)
        )
        observations = []
        for raw_state in transitions:
            source = str(raw_state)
            transition_row = transitions.get(raw_state, {})
            output_row = outputs.get(raw_state, {})
            for action in actions:
                target = transition_row.get(action) if isinstance(transition_row, Mapping) else None
                output = output_row.get(action) if isinstance(output_row, Mapping) else None
                if target is None or output is None:
                    continue
                observations.append(TransitionObservation(
                    source, str(action), (TransitionOutcome(str(target), tuple(output)),),
                    evidence=("imported from VG-PredictiveMealy-1",),
                ))
        root_metadata = data.get("metadata", {})
        legacy_metadata = payload.get("metadata", {})
        metadata = {
            "adapter": "Build 24 VG-PredictiveMealy-1",
            "source_metadata": dict(legacy_metadata) if isinstance(legacy_metadata, Mapping) else {},
            "wrapper_metadata": dict(root_metadata) if isinstance(root_metadata, Mapping) else {},
        }
        return cls(
            states, tuple(str(x) for x in actions), str(payload["initial"]),
            tuple(str(x) for x in channels), tuple(observations), metadata,
        )


@dataclass(frozen=True, slots=True)
class CompiledTransitionRun:
    state_trace: tuple[str, ...]
    outputs: tuple[tuple[int, ...], ...]
    final_state: str
    system_fingerprint: str
    program_fingerprint: str
    runtime_ground_fingerprint: str


@dataclass(frozen=True, slots=True)
class CompiledTransitionProgram:
    system_fingerprint: str
    program: Program
    initial_memory: Mapping[str, SignalValue]
    states: tuple[str, ...]
    actions: tuple[str, ...]
    channels: tuple[str, ...]
    action_count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "initial_memory", MappingProxyType(dict(self.initial_memory)))

    def execute(self, actions: Sequence[str], *, interpreter: Any = None,
                max_steps: int = 100_000) -> CompiledTransitionRun:
        from .machine import VirtualGroundInterpreter

        action_word = tuple(actions)
        if len(action_word) != self.action_count:
            raise TransitionExecutionError(
                f"compiled program expects {self.action_count} actions, received {len(action_word)}"
            )
        action_index = {name: index for index, name in enumerate(self.actions)}
        memory = dict(self.initial_memory)
        backend = interpreter.backend if interpreter is not None else Signal8Backend()
        for index, action in enumerate(action_word):
            if action not in action_index:
                raise TransitionExecutionError(f"action {action!r} is outside the compiled Ground")
            memory[f"input.action.{index}"] = backend.encode_symbol(action_index[action], observer=1)

        runtime = interpreter or VirtualGroundInterpreter()
        result = runtime.execute(self.program, memory, max_steps=max_steps)
        observed = result.observed_outputs(runtime.backend)
        required = {
            *(f"state_after_{index}" for index in range(self.action_count)),
            *(f"output_{index}_{channel}" for index in range(self.action_count)
              for channel in range(len(self.channels))),
            "final_state",
        }
        missing = required - set(observed)
        if missing:
            raise TransitionExecutionError(
                "compiled dispatch stopped before completing the requested trace; "
                f"missing emissions: {sorted(missing)}"
            )
        try:
            state_trace = tuple(self.states[observed[f"state_after_{i}"]]
                                for i in range(self.action_count))
            output_trace = tuple(
                tuple(observed[f"output_{i}_{channel}"] for channel in range(len(self.channels)))
                for i in range(self.action_count)
            )
            final_state = self.states[observed["final_state"]]
        except (IndexError, KeyError) as exc:
            raise TransitionExecutionError(f"compiled output is outside its Ground: {exc}") from exc
        return CompiledTransitionRun(
            state_trace, output_trace, final_state, self.system_fingerprint,
            result.program_fingerprint, result.ground_fingerprint,
        )


class TransitionCompiler:
    """Compile complete finite grounds to the existing Signal8 instruction IR."""

    def compile(self, system: GroundTransitionSystem, action_count: int, *,
                backend: Signal8Backend | None = None) -> CompiledTransitionProgram:
        if isinstance(action_count, bool) or not isinstance(action_count, int) or action_count < 0:
            raise TransitionCompileError("action_count must be a non-negative integer")
        if not system.complete:
            raise TransitionCompileError(
                "only complete, single-valued grounds can be compiled; "
                f"unknown={list(system.unknown_pairs)}, ambiguous={list(system.ambiguous_pairs)}"
            )
        if len(system.states) > 8 or len(system.actions) > 8:
            raise TransitionCompileError("Signal8 lowering supports at most eight states and eight actions")
        backend = backend or Signal8Backend()
        if backend.domain_id != "signal.phase.cyclic.z8.v1":
            raise TransitionCompileError("this compiler currently targets Signal8 Z/8Z")
        if tuple(backend.observer_profiles) != (1, 3, 5, 7):
            raise TransitionCompileError("unsupported Signal8 observer family")

        state_code = {name: index for index, name in enumerate(system.states)}
        action_code = {name: index for index, name in enumerate(system.actions)}
        memory: dict[str, SignalValue] = {
            "state": backend.encode_symbol(state_code[system.initial_state], observer=1)
        }
        for symbol in range(8):
            memory[f"const.symbol.{symbol}"] = backend.encode_symbol(symbol, observer=1)
        for name, index in state_code.items():
            memory[f"const.state.{index}"] = backend.encode_symbol(index, observer=1)
        for name, index in action_code.items():
            memory[f"const.action.{index}"] = backend.encode_symbol(index, observer=1)
        for index in range(action_count):
            memory[f"input.action.{index}"] = backend.encode_symbol(0, observer=1)

        instructions: list[Instruction] = []

        def emit(opcode: str, **args: Any) -> int:
            instructions.append(Instruction(opcode, args))
            return len(instructions) - 1

        def patch(index: int, target: int) -> None:
            old = instructions[index]
            if old.opcode not in ("BRANCH_EQ", "JUMP"):
                raise TransitionCompileError("internal compiler target patch hit a non-branch")
            args = dict(old.args)
            args["target"] = target
            instructions[index] = Instruction(old.opcode, args)

        edge_lookup = {(item.source, item.action): item.outcomes[0] for item in system.observations}
        for step_index in range(action_count):
            emit("LOAD", dst="dispatch_state", address="state")
            emit("LOAD", dst="dispatch_action", address=f"input.action.{step_index}")
            success_jumps: list[int] = []
            for source in system.states:
                for action in system.actions:
                    outcome = edge_lookup[(source, action)]
                    emit("LOAD", dst="expected_state", address=f"const.state.{state_code[source]}")
                    state_branch = emit(
                        "BRANCH_EQ", left="dispatch_state", right="expected_state",
                        target=-1, tolerance_rad=1e-8,
                    )
                    state_miss = emit("JUMP", target=-1)
                    action_test = len(instructions)
                    patch(state_branch, action_test)
                    emit("LOAD", dst="expected_action", address=f"const.action.{action_code[action]}")
                    action_branch = emit(
                        "BRANCH_EQ", left="dispatch_action", right="expected_action",
                        target=-1, tolerance_rad=1e-8,
                    )
                    action_miss = emit("JUMP", target=-1)
                    matched = len(instructions)
                    patch(action_branch, matched)

                    emit("LOAD", dst="next_state", address=f"const.state.{state_code[outcome.target]}")
                    emit("STORE", src="next_state", address="state")
                    emit("EMIT", src="next_state", label=f"state_after_{step_index}")
                    for channel_index, value in enumerate(outcome.output):
                        emit("LOAD", dst="channel_output", address=f"const.symbol.{value}")
                        emit("EMIT", src="channel_output", label=f"output_{step_index}_{channel_index}")
                    success_jumps.append(emit("JUMP", target=-1))
                    next_pair = len(instructions)
                    patch(state_miss, next_pair)
                    patch(action_miss, next_pair)

            # A corrupted state/action input cannot fall through as a valid transition.
            emit("HALT")
            next_step = len(instructions)
            for jump_index in success_jumps:
                patch(jump_index, next_step)

        emit("LOAD", dst="final_state", address="state")
        emit("EMIT", src="final_state", label="final_state")
        emit("HALT")
        program = Program(
            name=f"ground-transition-{system.fingerprint[:12]}",
            instructions=tuple(instructions),
            metadata={
                "source": "vgi.transition-compiler.v1",
                "system_fingerprint": system.fingerprint,
                "action_count": action_count,
                "state_encoding": "finite indices embedded in Signal8 Z/8Z",
                "semantic_trace": "state_after_i and output_i_channel emissions",
            },
        )
        return CompiledTransitionProgram(
            system.fingerprint, program, memory, system.states, system.actions,
            system.channels, action_count,
        )


def differential_verify(
    system: GroundTransitionSystem, action_sequences: Sequence[Sequence[str]]
) -> dict[str, Any]:
    """Compare direct predictive semantics with compiled VGI execution."""
    if not system.complete:
        raise TransitionCompileError("differential verification requires a complete Ground")
    compiler = TransitionCompiler()
    compiled_by_length: dict[int, CompiledTransitionProgram] = {}
    errors: list[dict[str, Any]] = []
    checked = 0
    for raw_actions in action_sequences:
        actions = tuple(raw_actions)
        if len(actions) not in compiled_by_length:
            compiled_by_length[len(actions)] = compiler.compile(system, len(actions))
        direct = system.run(actions)
        realized = compiled_by_length[len(actions)].execute(actions)
        checked += 1
        if realized.state_trace != direct.state_trace or realized.outputs != direct.outputs:
            errors.append({
                "actions": list(actions),
                "expected_states": list(direct.state_trace),
                "actual_states": list(realized.state_trace),
                "expected_outputs": [list(x) for x in direct.outputs],
                "actual_outputs": [list(x) for x in realized.outputs],
            })
    return {
        "status": "PASS" if not errors else "FAIL",
        "cases_checked": checked,
        "errors": errors,
        "system_fingerprint": system.fingerprint,
        "compiled_instruction_counts": {
            str(length): len(item.program.instructions)
            for length, item in sorted(compiled_by_length.items())
        },
        "scope": "agreement for supplied finite action sequences; not a proof for untested domains",
    }
