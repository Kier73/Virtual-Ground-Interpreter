"""Capture Signal8 instruction execution as provenance-bound, interpretation-neutral encounters.

The adapter records the machine's committed instruction events and failed
attempts without decoding semantic integers. A separate projection groups only
transitions actually seen in one or more traces. It does not fill missing pairs,
admit a Ground, or claim that the trace exhausts an external system.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any

from .channels import ChannelContract, ChannelExchangeLedger, ChannelMessage
from .encounters import EncounterLedger, EncounterProvenance
from .evidence import TransportFrameReceipt
from .ground import GroundSpec
from .ir import Program
from .machine import VirtualGroundInterpreter
from .values import SignalValue


class ExecutionTraceError(ValueError):
    """Invalid execution capture, trace lineage, or observed transition projection."""


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionTraceError(f"{label} must be a non-empty string")
    return value


def _positive(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExecutionTraceError(f"{label} must be a positive integer")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ExecutionTraceError(f"{label} must be a SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ExecutionTraceError(f"{label} must be a SHA-256 digest") from exc
    if value.lower() != value:
        raise ExecutionTraceError(f"{label} must use lowercase hexadecimal")
    return value


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ExecutionTraceError(f"value is not canonical JSON: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ExecutionTraceError("JSON object keys must be strings")
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ExecutionTraceError(
        f"trace payloads must be finite JSON-compatible values, got {type(value).__name__}"
    )


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _runtime_state_digest(snapshot: Mapping[str, Any]) -> str:
    """Fingerprint machine state while excluding its append-only trace history.

    Excluding trace history makes repeated visits to the same operational state
    comparable. Program, Ground, PC, memory, registers, outputs, and halt status
    remain part of the fingerprint.
    """
    state = {
        key: value for key, value in snapshot.items()
        if key not in ("trace", "state_digest")
    }
    return _digest(_thaw_json(state))


@dataclass(frozen=True, slots=True)
class ExecutionTraceFrame:
    record_type: str
    sequence: int
    step_index: int
    message_id: str
    encounter_id: str
    state_before_digest: str
    state_after_digest: str
    instruction_digest: str
    event_digest: str
    receipt: TransportFrameReceipt

    def __post_init__(self) -> None:
        if self.record_type not in ("execution_step", "execution_failure"):
            raise ExecutionTraceError("record_type must be execution_step or execution_failure")
        _positive(self.sequence, "frame sequence")
        if isinstance(self.step_index, bool) or not isinstance(self.step_index, int) or self.step_index < 0:
            raise ExecutionTraceError("step_index must be a non-negative integer")
        for value, label in (
            (self.message_id, "message_id"),
            (self.encounter_id, "encounter_id"),
        ):
            _text(value, label)
        for value, label in (
            (self.state_before_digest, "state_before_digest"),
            (self.state_after_digest, "state_after_digest"),
            (self.instruction_digest, "instruction_digest"),
            (self.event_digest, "event_digest"),
        ):
            _sha(value, label)
        if not isinstance(self.receipt, TransportFrameReceipt):
            raise ExecutionTraceError("receipt must be a TransportFrameReceipt")
        if self.receipt.sequence != self.sequence or self.receipt.message_id != self.message_id:
            raise ExecutionTraceError("frame receipt does not match the execution frame identity")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "sequence": self.sequence,
            "step_index": self.step_index,
            "message_id": self.message_id,
            "encounter_id": self.encounter_id,
            "state_before_digest": self.state_before_digest,
            "state_after_digest": self.state_after_digest,
            "instruction_digest": self.instruction_digest,
            "event_digest": self.event_digest,
            "receipt": self.receipt.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class Signal8ExecutionTrace:
    """A complete capture envelope for one execution attempt."""

    trace_id: str
    status: str
    max_steps: int
    program_fingerprint: str
    ground_fingerprint: str
    initial_state_digest: str
    final_state_digest: str
    program_definition: Mapping[str, Any]
    initial_memory: Mapping[str, Any]
    ground_definition: Mapping[str, Any]
    entries: tuple[ExecutionTraceFrame, ...]
    exchange: ChannelExchangeLedger
    encounters: EncounterLedger
    final_snapshot: Mapping[str, Any]
    failure: Mapping[str, Any] | None = None
    captured_at: str | None = None

    def __post_init__(self) -> None:
        _text(self.trace_id, "trace_id")
        if self.status not in ("completed", "failed", "step_limit"):
            raise ExecutionTraceError("status must be completed, failed, or step_limit")
        _positive(self.max_steps, "max_steps")
        for value, label in (
            (self.program_fingerprint, "program_fingerprint"),
            (self.ground_fingerprint, "ground_fingerprint"),
            (self.initial_state_digest, "initial_state_digest"),
            (self.final_state_digest, "final_state_digest"),
        ):
            _sha(value, label)
        if self.captured_at is not None:
            _text(self.captured_at, "captured_at")
        if not isinstance(self.exchange, ChannelExchangeLedger):
            raise ExecutionTraceError("exchange must be a ChannelExchangeLedger")
        if not isinstance(self.encounters, EncounterLedger):
            raise ExecutionTraceError("encounters must be an EncounterLedger")
        entries = tuple(self.entries)
        if any(not isinstance(item, ExecutionTraceFrame) for item in entries):
            raise ExecutionTraceError("entries must contain ExecutionTraceFrame records")
        sequences = tuple(item.sequence for item in entries)
        if len(sequences) != len(set(sequences)) or sequences != tuple(sorted(sequences)):
            raise ExecutionTraceError("frame sequences must be unique and increasing")
        message_ids = tuple(item.message_id for item in entries)
        encounter_ids = tuple(item.encounter_id for item in entries)
        if len(message_ids) != len(set(message_ids)) or len(encounter_ids) != len(set(encounter_ids)):
            raise ExecutionTraceError("execution frame message and Encounter identifiers must be unique")
        if len(entries) > self.max_steps:
            raise ExecutionTraceError("captured entries cannot exceed max_steps")
        if (self.status == "failed") != (self.failure is not None):
            raise ExecutionTraceError("failure details must be present exactly for failed traces")

        program_definition = _freeze_json(self.program_definition)
        memory = _freeze_json(self.initial_memory)
        ground = _freeze_json(self.ground_definition)
        final = _freeze_json(self.final_snapshot)
        failure = None if self.failure is None else _freeze_json(self.failure)
        if not all(isinstance(value, Mapping) for value in (program_definition, memory, ground, final)):
            raise ExecutionTraceError("program, memory, Ground, and final snapshot must be objects")
        if failure is not None and not isinstance(failure, Mapping):
            raise ExecutionTraceError("failure details must be an object")
        if _runtime_state_digest(final) != self.final_state_digest:
            raise ExecutionTraceError("final snapshot does not match final_state_digest")
        if final.get("schema") != "vgi.machine-snapshot.v1":
            raise ExecutionTraceError("final snapshot has an unsupported machine schema")
        try:
            parsed_program = Program.from_dict(_thaw_json(program_definition))
            ground_contract = GroundSpec(**_thaw_json(ground))
            initial_values = {
                key: SignalValue.from_dict(dict(value))
                for key, value in memory.items()
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise ExecutionTraceError(f"trace definitions or initial memory are invalid: {exc}") from exc
        program_fingerprint = hashlib.sha256(
            json.dumps(parsed_program.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if program_fingerprint != self.program_fingerprint:
            raise ExecutionTraceError("program definition does not match program_fingerprint")
        if ground_contract.fingerprint != self.ground_fingerprint:
            raise ExecutionTraceError("Ground definition does not match ground_fingerprint")
        if any(value.observer not in ground_contract.observer_profiles for value in initial_values.values()):
            raise ExecutionTraceError("initial memory contains a value outside the Ground observer profiles")
        initial_memory_dict = {
            key: value.to_dict() for key, value in sorted(initial_values.items())
        }
        initial_core = {
            "schema": "vgi.machine-snapshot.v1",
            "program_fingerprint": self.program_fingerprint,
            "ground_fingerprint": self.ground_fingerprint,
            "pc": 0,
            "halted": False,
            "initial_memory": initial_memory_dict,
            "memory": initial_memory_dict,
            "registers": {},
            "outputs": [],
        }
        if _digest(initial_core) != self.initial_state_digest:
            raise ExecutionTraceError("initial program/memory/Ground do not match initial_state_digest")
        if final.get("program_fingerprint") != self.program_fingerprint:
            raise ExecutionTraceError("final snapshot belongs to a different program")
        if final.get("ground_fingerprint") != self.ground_fingerprint:
            raise ExecutionTraceError("final snapshot belongs to a different Ground")
        if bool(final.get("halted")) != (self.status == "completed"):
            raise ExecutionTraceError("trace status does not match final machine halt state")

        messages = {item.message_id: item for item in self.exchange.messages}
        for entry in entries:
            message = messages.get(entry.message_id)
            if message is None:
                raise ExecutionTraceError("execution frame has no retained channel message")
            if message.direction != "observation":
                raise ExecutionTraceError("execution frames must be inbound observations")
            if message.payload.get("trace_id") != self.trace_id:
                raise ExecutionTraceError("channel message belongs to a different trace")
            if message.provenance.captured_at != self.captured_at or entry.receipt.received_at != self.captured_at:
                raise ExecutionTraceError("capture timestamp differs across trace, message, and frame receipt")
            if message.payload.get("record_type") != entry.record_type:
                raise ExecutionTraceError("channel message record type differs from its frame")
            if (
                message.payload.get("step_index") != entry.step_index
                or message.payload.get("state_before_digest") != entry.state_before_digest
                or message.payload.get("state_after_digest") != entry.state_after_digest
                or message.payload.get("instruction_digest") != entry.instruction_digest
            ):
                raise ExecutionTraceError("frame metadata differs from the retained execution message")
            if entry.record_type == "execution_step":
                event = message.payload.get("event")
                if not isinstance(event, Mapping):
                    raise ExecutionTraceError("successful frame lacks its raw ExecutionEvent")
                if (
                    event.get("step") != entry.step_index
                    or event.get("pc_before") != message.payload.get("pc_before")
                    or event.get("pc_after") != message.payload.get("pc_after")
                    or event.get("opcode") != message.payload.get("opcode")
                    or _digest(_thaw_json(event)) != entry.event_digest
                ):
                    raise ExecutionTraceError("raw ExecutionEvent does not match its frame metadata/digest")
            else:
                failure_signature = {
                    "exception_type": message.payload.get("exception_type"),
                    "exception_message": message.payload.get("exception_message"),
                }
                if (
                    message.payload.get("pc") is None
                    or _digest(failure_signature) != entry.event_digest
                    or entry.state_before_digest != entry.state_after_digest
                ):
                    raise ExecutionTraceError("failed attempt lacks a valid atomic rollback record")
            instruction = message.payload.get("instruction")
            if not isinstance(instruction, Mapping) or _digest(_thaw_json(instruction)) != entry.instruction_digest:
                raise ExecutionTraceError("instruction definition does not match its retained digest")
            if not self.encounters.contains(entry.encounter_id):
                raise ExecutionTraceError("execution frame has no retained Encounter")
            encounter = self.encounters.get(entry.encounter_id)
            if encounter.payload != message.payload or encounter.provenance != message.provenance:
                raise ExecutionTraceError("Encounter does not preserve the exact channel message")
            if (
                entry.receipt.message_id != message.message_id
                or entry.receipt.channel_id != message.channel_id
                or entry.receipt.source != message.provenance.source
                or entry.receipt.payload_digest != _digest(message.to_dict())
            ):
                raise ExecutionTraceError("transport receipt does not bind the retained message identity and payload")
            expected_context = {
                "channel_id": message.channel_id,
                "protocol_id": message.protocol_id,
                "direction": "observation",
                "correlation_id": None,
                "message_id": message.message_id,
            }
            if _thaw_json(encounter.context) != expected_context:
                raise ExecutionTraceError("Encounter context does not bind the exact execution message")

        failure_entries = tuple(item for item in entries if item.record_type == "execution_failure")
        if (self.status == "failed") != (len(failure_entries) == 1):
            raise ExecutionTraceError("failed trace must retain exactly one failed instruction attempt")
        if failure_entries:
            failure_entry = failure_entries[0]
            failure_message = messages[failure_entry.message_id]
            for key in ("step_index", "pc", "exception_type", "exception_message", "instruction_digest"):
                if self.failure.get(key) != (
                    failure_entry.step_index if key == "step_index"
                    else failure_entry.instruction_digest if key == "instruction_digest"
                    else failure_message.payload.get(key)
                ):
                    raise ExecutionTraceError("failure summary differs from its retained failed-attempt frame")

        object.__setattr__(self, "program_definition", program_definition)
        object.__setattr__(self, "initial_memory", memory)
        object.__setattr__(self, "ground_definition", ground)
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "final_snapshot", final)
        object.__setattr__(self, "failure", failure)

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-Signal8ExecutionTrace-1",
            "trace_id": self.trace_id,
            "status": self.status,
            "max_steps": self.max_steps,
            "captured_at": self.captured_at,
            "program_fingerprint": self.program_fingerprint,
            "ground_fingerprint": self.ground_fingerprint,
            "initial_state_digest": self.initial_state_digest,
            "final_state_digest": self.final_state_digest,
            "program_definition": _thaw_json(self.program_definition),
            "initial_memory": _thaw_json(self.initial_memory),
            "ground_definition": _thaw_json(self.ground_definition),
            "entries": [item.to_dict() for item in self.entries],
            "exchange": self.exchange.to_dict(),
            "encounters": self.encounters.to_dict(),
            "final_snapshot": _thaw_json(self.final_snapshot),
            "failure": None if self.failure is None else _thaw_json(self.failure),
        }


    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Signal8ExecutionTrace":
        if not isinstance(data, Mapping) or data.get("format") != "VGI-Signal8ExecutionTrace-1":
            raise ExecutionTraceError("expected VGI-Signal8ExecutionTrace-1")
        try:
            exchange = ChannelExchangeLedger.from_dict(data["exchange"])
            encounters = EncounterLedger.from_dict(data["encounters"])
            entries = tuple(
                ExecutionTraceFrame(
                    record_type=item["record_type"],
                    sequence=item["sequence"],
                    step_index=item["step_index"],
                    message_id=item["message_id"],
                    encounter_id=item["encounter_id"],
                    state_before_digest=item["state_before_digest"],
                    state_after_digest=item["state_after_digest"],
                    instruction_digest=item["instruction_digest"],
                    event_digest=item["event_digest"],
                    receipt=TransportFrameReceipt(**item["receipt"]),
                )
                for item in data.get("entries", ())
            )
            return cls(
                trace_id=data["trace_id"],
                status=data["status"],
                max_steps=data["max_steps"],
                captured_at=data.get("captured_at"),
                program_fingerprint=data["program_fingerprint"],
                ground_fingerprint=data["ground_fingerprint"],
                initial_state_digest=data["initial_state_digest"],
                final_state_digest=data["final_state_digest"],
                program_definition=data["program_definition"],
                initial_memory=data["initial_memory"],
                ground_definition=data["ground_definition"],
                entries=entries,
                exchange=exchange,
                encounters=encounters,
                final_snapshot=data["final_snapshot"],
                failure=data.get("failure"),
            )
        except ExecutionTraceError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ExecutionTraceError(f"invalid serialized execution trace: {exc}") from exc

    @classmethod
    def from_json(cls, source: str) -> "Signal8ExecutionTrace":
        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise ExecutionTraceError(f"invalid execution trace JSON: {exc}") from exc
        return cls.from_dict(data)


class Signal8ExecutionAdapter:
    """Capture instruction-level events from the active VGI Signal8 runtime."""

    def __init__(self, interpreter: VirtualGroundInterpreter | None = None):
        self.interpreter = interpreter or VirtualGroundInterpreter()
        self.contract = ChannelContract(
            channel_id="vgi.signal8.execution",
            protocol_id="vgi.signal8.execution-event/1",
            observation_schema="vgi.signal8.execution-event/1",
        )

    def capture(
        self,
        program: Program,
        initial_memory: Mapping[str, SignalValue] | None = None,
        *,
        trace_id: str,
        max_steps: int = 10_000,
        captured_at: str | None = None,
    ) -> Signal8ExecutionTrace:
        """Run the machine stepwise and retain every committed event or failed attempt.

        Capturing does not call observe_symbol or otherwise decode SignalValue.
        A failed step is recorded after the machine's atomic rollback; it is not
        projected as a successful transition.
        """
        if not isinstance(program, Program):
            raise ExecutionTraceError("program must be a Program")
        _text(trace_id, "trace_id")
        _positive(max_steps, "max_steps")
        if captured_at is not None:
            _text(captured_at, "captured_at")
        initial = dict(initial_memory or {})
        if any(not isinstance(value, SignalValue) for value in initial.values()):
            raise ExecutionTraceError("initial_memory values must be SignalValue instances")

        machine = self.interpreter.instantiate(program, initial)
        initial_snapshot = machine.snapshot()
        initial_state_digest = _runtime_state_digest(initial_snapshot)
        program_fingerprint = str(initial_snapshot["program_fingerprint"])
        ground_fingerprint = str(initial_snapshot["ground_fingerprint"])
        program_definition = program.to_dict()
        initial_memory_record = {
            key: value.to_dict() for key, value in sorted(initial.items())
        }
        ground_definition = self.interpreter.ground.canonical_dict()

        exchange = ChannelExchangeLedger().register(self.contract)
        entries: list[ExecutionTraceFrame] = []
        failure: dict[str, Any] | None = None
        transport_id = f"vgi-local-execution:{trace_id}"

        def retain(record_type: str, step_index: int, before_digest: str,
                   after_digest: str, instruction_digest: str,
                   event_digest: str, payload: Mapping[str, Any]) -> None:
            nonlocal exchange
            sequence = len(entries) + 1
            message_id = f"{trace_id}:frame:{sequence}"
            payload_dict = dict(payload)
            provenance = EncounterProvenance(
                source="vgi.signal8.machine",
                source_ref=f"vgi-execution://{trace_id}/frame/{sequence}",
                captured_at=captured_at,
                collector="Signal8ExecutionAdapter",
                content_digest=_digest(payload_dict),
            )
            message = ChannelMessage(
                message_id=message_id,
                channel_id=self.contract.channel_id,
                protocol_id=self.contract.protocol_id,
                direction="observation",
                payload=payload_dict,
                provenance=provenance,
            )
            exchange = exchange.record_observation(self.contract, message)
            receipt = TransportFrameReceipt.capture(
                message, transport_id=transport_id, sequence=sequence,
                received_at=captured_at,
            )
            entries.append(ExecutionTraceFrame(
                record_type=record_type,
                sequence=sequence,
                step_index=step_index,
                message_id=message_id,
                encounter_id=f"channel-message:{message_id}",
                state_before_digest=before_digest,
                state_after_digest=after_digest,
                instruction_digest=instruction_digest,
                event_digest=event_digest,
                receipt=receipt,
            ))

        for step_index in range(max_steps):
            if machine.halted:
                break
            before_snapshot = machine.snapshot()
            before_digest = _runtime_state_digest(before_snapshot)
            pc_before = machine.pc
            instruction = program.instructions[pc_before]
            instruction_dict = instruction.to_dict()
            instruction_digest = _digest(instruction_dict)
            try:
                event = machine.step()
            except Exception as exc:
                after_digest = _runtime_state_digest(machine.snapshot())
                failure_payload = {
                    "schema": "vgi.signal8.execution-event/1",
                    "record_type": "execution_failure",
                    "trace_id": trace_id,
                    "step_index": step_index,
                    "pc": pc_before,
                    "instruction": instruction_dict,
                    "instruction_digest": instruction_digest,
                    "state_before_digest": before_digest,
                    "state_after_digest": after_digest,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                }
                failure = {
                    "step_index": step_index,
                    "pc": pc_before,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "instruction_digest": instruction_digest,
                }
                retain(
                    "execution_failure", step_index, before_digest, after_digest,
                    instruction_digest, _digest({
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    }), failure_payload,
                )
                break

            if event is None:
                break
            after_snapshot = machine.snapshot()
            after_digest = _runtime_state_digest(after_snapshot)
            event_dict = event.to_dict()
            event_digest = _digest(event_dict)
            event_payload = {
                "schema": "vgi.signal8.execution-event/1",
                "record_type": "execution_step",
                "trace_id": trace_id,
                "step_index": step_index,
                "pc_before": event.pc_before,
                "pc_after": event.pc_after,
                "opcode": event.opcode,
                "instruction": instruction_dict,
                "instruction_digest": instruction_digest,
                "state_before_digest": before_digest,
                "state_after_digest": after_digest,
                "event": event_dict,
            }
            retain(
                "execution_step", step_index, before_digest, after_digest,
                instruction_digest, event_digest, event_payload,
            )
            if machine.halted:
                break

        status = "completed" if machine.halted else ("failed" if failure is not None else "step_limit")
        final_snapshot = machine.snapshot()
        encounters = exchange.to_encounter_ledger()
        return Signal8ExecutionTrace(
            trace_id=trace_id,
            status=status,
            max_steps=max_steps,
            program_fingerprint=program_fingerprint,
            ground_fingerprint=ground_fingerprint,
            initial_state_digest=initial_state_digest,
            final_state_digest=_runtime_state_digest(final_snapshot),
            program_definition=program_definition,
            initial_memory=initial_memory_record,
            ground_definition=ground_definition,
            entries=tuple(entries),
            exchange=exchange,
            encounters=encounters,
            final_snapshot=final_snapshot,
            failure=failure,
            captured_at=captured_at,
        )

    def replay(self, trace: Signal8ExecutionTrace, *, trace_id: str) -> Signal8ExecutionTrace:
        """Replay the retained program and initial signal memory in this runtime."""
        if not isinstance(trace, Signal8ExecutionTrace):
            raise ExecutionTraceError("trace must be a Signal8ExecutionTrace")
        if trace.ground_fingerprint != self.interpreter.ground.fingerprint:
            raise ExecutionTraceError("trace Ground does not match this interpreter")
        program = Program.from_dict(_thaw_json(trace.program_definition))
        memory = {
            key: SignalValue.from_dict(dict(value))
            for key, value in trace.initial_memory.items()
        }
        return self.capture(
            program, memory, trace_id=trace_id, max_steps=trace.max_steps,
        )


@dataclass(frozen=True, slots=True)
class ExecutionTransitionObservation:
    """A grouping of actually witnessed machine transitions, not an admitted law."""

    source_state_digest: str
    action_descriptor: str
    target_state_digests: tuple[str, ...]
    occurrence_count: int
    encounter_ids: tuple[str, ...]
    message_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _sha(self.source_state_digest, "source_state_digest")
        _text(self.action_descriptor, "action_descriptor")
        targets = tuple(sorted(set(self.target_state_digests)))
        if not targets:
            raise ExecutionTraceError("an observed transition requires at least one target")
        for target in targets:
            _sha(target, "target_state_digest")
        _positive(self.occurrence_count, "occurrence_count")
        encounter_ids = tuple(self.encounter_ids)
        message_ids = tuple(self.message_ids)
        if len(encounter_ids) != self.occurrence_count or len(message_ids) != self.occurrence_count:
            raise ExecutionTraceError("transition occurrence count must match retained frame references")
        if len(set(encounter_ids)) != len(encounter_ids) or len(set(message_ids)) != len(message_ids):
            raise ExecutionTraceError("transition evidence references must be unique")
        object.__setattr__(self, "target_state_digests", targets)
        object.__setattr__(self, "encounter_ids", encounter_ids)
        object.__setattr__(self, "message_ids", message_ids)

    @property
    def status(self) -> str:
        return "one_observed_successor" if len(self.target_state_digests) == 1 else "conflicting_successors"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_state_digest": self.source_state_digest,
            "action_descriptor": self.action_descriptor,
            "target_state_digests": list(self.target_state_digests),
            "occurrence_count": self.occurrence_count,
            "encounter_ids": list(self.encounter_ids),
            "message_ids": list(self.message_ids),
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ExecutionTransitionProjection:
    """Observed-only projection across one or more traces; absent pairs are not inferred."""

    trace_ids: tuple[str, ...]
    state_digests: tuple[str, ...]
    action_descriptors: tuple[str, ...]
    observations: tuple[ExecutionTransitionObservation, ...]

    def __post_init__(self) -> None:
        traces = tuple(self.trace_ids)
        states = tuple(sorted(set(self.state_digests)))
        actions = tuple(sorted(set(self.action_descriptors)))
        observations = tuple(self.observations)
        if not traces or len(traces) != len(set(traces)):
            raise ExecutionTraceError("projection trace_ids must be non-empty and unique")
        if any(not isinstance(item, ExecutionTransitionObservation) for item in observations):
            raise ExecutionTraceError("observations must contain ExecutionTransitionObservation records")
        for state in states:
            _sha(state, "projected state digest")
        if not observations:
            raise ExecutionTraceError("projection requires at least one successful execution step")
        object.__setattr__(self, "trace_ids", traces)
        object.__setattr__(self, "state_digests", states)
        object.__setattr__(self, "action_descriptors", actions)
        object.__setattr__(self, "observations", observations)

    @property
    def conflict_count(self) -> int:
        return sum(item.status == "conflicting_successors" for item in self.observations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-ExecutionTransitionProjection-1",
            "trace_ids": list(self.trace_ids),
            "state_digests": list(self.state_digests),
            "action_descriptors": list(self.action_descriptors),
            "observations": [item.to_dict() for item in self.observations],
            "conflict_count": self.conflict_count,
            "scope": (
                "only successful instruction transitions present in the supplied traces; "
                "unseen state/action pairs remain unqueried and are not classified as impossible"
            ),
        }

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


def project_execution_transitions(
    traces: Sequence[Signal8ExecutionTrace],
) -> ExecutionTransitionProjection:
    """Group observed transitions without constructing or authorizing a Ground."""
    if isinstance(traces, (str, bytes)) or not isinstance(traces, Sequence):
        raise ExecutionTraceError("traces must be a sequence of Signal8ExecutionTrace records")
    trace_items = tuple(traces)
    if not trace_items or any(not isinstance(item, Signal8ExecutionTrace) for item in trace_items):
        raise ExecutionTraceError("at least one Signal8ExecutionTrace is required")

    grouped: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    states: set[str] = set()
    actions: set[str] = set()
    message_lookup = {
        trace.trace_id: {item.message_id: item for item in trace.exchange.messages}
        for trace in trace_items
    }
    for trace in trace_items:
        for entry in trace.entries:
            if entry.record_type != "execution_step":
                continue
            message = message_lookup[trace.trace_id][entry.message_id]
            payload = message.payload
            action = (
                f"pc:{payload['pc_before']}:{payload['opcode']}:"
                f"{payload['instruction_digest']}"
            )
            source = entry.state_before_digest
            target = entry.state_after_digest
            grouped.setdefault((source, action), []).append(
                (target, entry.encounter_id, entry.message_id)
            )
            states.update((source, target))
            actions.add(action)

    observations = []
    for (source, action), records in sorted(grouped.items()):
        observations.append(ExecutionTransitionObservation(
            source_state_digest=source,
            action_descriptor=action,
            target_state_digests=tuple(sorted({item[0] for item in records})),
            occurrence_count=len(records),
            encounter_ids=tuple(item[1] for item in records),
            message_ids=tuple(item[2] for item in records),
        ))
    return ExecutionTransitionProjection(
        trace_ids=tuple(item.trace_id for item in trace_items),
        state_digests=tuple(sorted(states)),
        action_descriptors=tuple(sorted(actions)),
        observations=tuple(observations),
    )


@dataclass(frozen=True, slots=True)
class ExecutionReplayReport:
    observed_trace_id: str
    replay_trace_id: str
    status: str
    checked_entries: int
    mismatches: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.observed_trace_id, "observed_trace_id")
        _text(self.replay_trace_id, "replay_trace_id")
        if self.status not in ("match", "mismatch"):
            raise ExecutionTraceError("replay status must be match or mismatch")
        if isinstance(self.checked_entries, bool) or not isinstance(self.checked_entries, int) or self.checked_entries < 0:
            raise ExecutionTraceError("checked_entries must be a non-negative integer")
        mismatches = tuple(self.mismatches)
        if (self.status == "match") != (not mismatches):
            raise ExecutionTraceError("replay status must agree with mismatch details")
        object.__setattr__(self, "mismatches", mismatches)

    @property
    def matched(self) -> bool:
        return self.status == "match"

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_trace_id": self.observed_trace_id,
            "replay_trace_id": self.replay_trace_id,
            "status": self.status,
            "checked_entries": self.checked_entries,
            "mismatches": list(self.mismatches),
            "scope": (
                "exact replay agreement for the supplied Signal8 program, initial signal memory, "
                "Ground, and captured instruction sequence"
            ),
        }


def verify_execution_replay(
    observed: Signal8ExecutionTrace,
    replayed: Signal8ExecutionTrace,
) -> ExecutionReplayReport:
    """Compare two captures while ignoring transport IDs and capture timestamps."""
    if not isinstance(observed, Signal8ExecutionTrace) or not isinstance(replayed, Signal8ExecutionTrace):
        raise ExecutionTraceError("verify_execution_replay requires two execution traces")
    mismatches: list[str] = []
    for field_name in (
        "program_fingerprint", "ground_fingerprint", "initial_state_digest",
        "final_state_digest", "status",
    ):
        if getattr(observed, field_name) != getattr(replayed, field_name):
            mismatches.append(f"{field_name} differs")
    if len(observed.entries) != len(replayed.entries):
        mismatches.append("entry count differs")
    checked = min(len(observed.entries), len(replayed.entries))
    for index in range(checked):
        left, right = observed.entries[index], replayed.entries[index]
        for field_name in (
            "record_type", "step_index", "state_before_digest", "state_after_digest",
            "instruction_digest", "event_digest",
        ):
            if getattr(left, field_name) != getattr(right, field_name):
                mismatches.append(f"entry {index} {field_name} differs")
    return ExecutionReplayReport(
        observed.trace_id, replayed.trace_id,
        "match" if not mismatches else "mismatch",
        checked, tuple(mismatches),
    )
