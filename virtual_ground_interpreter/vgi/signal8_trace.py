"""Capture Signal8 machine execution as provenance-linked observations."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from .channels import ChannelContract, ChannelExchangeLedger, ChannelMessage
from .encounters import EncounterLedger, EncounterProvenance
from .evidence import TransitionEvidence, TransportFrameReceipt
from .machine import ExecutionEvent, ExecutionResult, SignalStateMachine


class Signal8TraceError(ValueError):
    """Invalid execution-trace capture request or record."""


SOURCE_ID = "vgi.signal8.machine"
TRANSPORT_ID = "vgi.signal8.in-process"
SIGNAL8_EXECUTION_CONTRACT = ChannelContract(
    channel_id="vgi.signal8.execution",
    protocol_id="vgi.signal8.execution-trace/1",
    observation_schema="vgi.signal8.execution-event/1",
)


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise Signal8TraceError(f"cannot canonicalize execution record: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _runtime_state_payload(machine: SignalStateMachine) -> dict[str, Any]:
    """Project future-relevant configuration, excluding trace and undo history."""
    return {
        "schema": "vgi.signal8-runtime-state/1",
        "program_fingerprint": machine._program_fingerprint,
        "ground_fingerprint": machine.interpreter.ground.fingerprint,
        "pc": machine.pc,
        "halted": machine.halted,
        "initial_memory": {k: v.to_dict() for k, v in sorted(machine.initial_memory.items())},
        "memory": {k: v.to_dict() for k, v in sorted(machine.memory.items())},
        "registers": {k: v.to_dict() for k, v in sorted(machine.registers.items())},
        "outputs": [{"label": x.label, "value": x.value.to_dict()} for x in machine.outputs],
    }


def runtime_state_id(machine: SignalStateMachine) -> str:
    """Stable ID for the declared runtime-configuration projection."""
    return "signal8-runtime/1:" + _digest(_runtime_state_payload(machine))


def _action_id(machine: SignalStateMachine, pc: int) -> str:
    instruction = machine.program.instructions[pc]
    return f"pc:{pc}:{instruction.opcode}:{_digest(instruction.to_dict())[:16]}"


@dataclass(frozen=True, slots=True)
class Signal8ExecutionCapture:
    run_id: str
    status: str
    context_digest: str
    program_fingerprint: str
    ground_id: str
    ground_fingerprint: str
    events: tuple[ExecutionEvent, ...]
    result: ExecutionResult
    exchange: ChannelExchangeLedger
    encounters: EncounterLedger
    frame_receipts: tuple[TransportFrameReceipt, ...]
    transition_evidence: tuple[TransitionEvidence, ...]
    fault_type: str | None = None
    fault_message: str | None = None

    def __post_init__(self) -> None:
        if self.status not in ("halted", "step_limit", "faulted"):
            raise Signal8TraceError("status must be halted, step_limit, or faulted")
        if self.status == "faulted" and not self.fault_type:
            raise Signal8TraceError("faulted capture requires a fault type")
        if self.status != "faulted" and self.fault_type is not None:
            raise Signal8TraceError("only faulted captures may carry a fault type")
        object.__setattr__(self, "events", tuple(self.events))
        object.__setattr__(self, "frame_receipts", tuple(self.frame_receipts))
        object.__setattr__(self, "transition_evidence", tuple(self.transition_evidence))

    @property
    def halted(self) -> bool:
        return self.result.halted

    @property
    def step_count(self) -> int:
        return len(self.events)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "vgi.signal8-execution-capture/1",
            "run_id": self.run_id,
            "status": self.status,
            "context_digest": self.context_digest,
            "program_fingerprint": self.program_fingerprint,
            "ground_id": self.ground_id,
            "ground_fingerprint": self.ground_fingerprint,
            "step_count": self.step_count,
            "final_pc": self.result.final_pc,
            "halted": self.result.halted,
            "captured_events": [x.to_dict() for x in self.events],
            "machine_trace_length": len(self.result.trace),
            "outputs": [{"label": x.label, "value": x.value.to_dict()}
                        for x in self.result.outputs],
            "channel_contracts": [x.to_dict() for x in self.exchange.contracts],
            "channel_messages": [x.to_dict() for x in self.exchange.messages],
            "encounters": [x.to_dict() for x in self.encounters.encounters],
            "frame_receipts": [x.to_dict() for x in self.frame_receipts],
            "transition_evidence": [x.to_dict() for x in self.transition_evidence],
            "fault": None if self.fault_type is None else {
                "type": self.fault_type, "message": self.fault_message,
            },
            "admission": "not_attempted",
        }


class Signal8ExecutionAdapter:
    """Capture actual SignalStateMachine steps without changing execution semantics.

    Successful steps produce concrete runtime-transition claims. The raw event
    retains signal values and branch evidence; this adapter never integer-decodes
    them. Runtime faults are generic observations with no transition status.
    """

    contract = SIGNAL8_EXECUTION_CONTRACT

    def capture(
        self,
        machine: SignalStateMachine,
        *,
        run_id: str,
        transport_id: str = TRANSPORT_ID,
        max_steps: int = 10_000,
    ) -> Signal8ExecutionCapture:
        if not isinstance(machine, SignalStateMachine):
            raise TypeError("capture expects a SignalStateMachine")
        if not isinstance(run_id, str) or not run_id.strip():
            raise Signal8TraceError("run_id must be a non-empty string")
        if not isinstance(transport_id, str) or not transport_id.strip():
            raise Signal8TraceError("transport_id must be a non-empty string")
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
            raise Signal8TraceError("max_steps must be a positive integer")

        program_fp = machine._program_fingerprint
        ground_id = machine.interpreter.ground.ground_id
        ground_fp = machine.interpreter.ground.fingerprint
        initial_state = runtime_state_id(machine)
        context_digest = _digest({
            "schema": "vgi.signal8-execution-context/1",
            "adapter": "Signal8ExecutionAdapter/1",
            "run_id": run_id,
            "ground_id": ground_id,
            "ground_fingerprint": ground_fp,
            "program_fingerprint": program_fp,
            "initial_runtime_state": initial_state,
        })

        exchange = ChannelExchangeLedger().register(self.contract)
        frames: list[TransportFrameReceipt] = []
        transition_messages: list[tuple[ChannelMessage, TransportFrameReceipt]] = []
        events: list[ExecutionEvent] = []
        fault_type = fault_message = None

        def retain(payload: dict[str, Any], suffix: str, source_ref: str):
            nonlocal exchange
            sequence = len(frames) + 1
            message = ChannelMessage(
                message_id=f"signal8:{run_id}:{suffix}",
                channel_id=self.contract.channel_id,
                protocol_id=self.contract.protocol_id,
                direction="observation",
                payload=payload,
                provenance=EncounterProvenance(
                    source=SOURCE_ID, source_ref=source_ref,
                    collector="Signal8ExecutionAdapter",
                ),
            )
            exchange = exchange.record_observation(self.contract, message)
            receipt = TransportFrameReceipt.capture(
                message, transport_id=transport_id, sequence=sequence,
            )
            frames.append(receipt)
            return message, receipt

        while not machine.halted and len(events) < max_steps:
            before = runtime_state_id(machine)
            pc_before = machine.pc
            try:
                instruction = machine.program.instructions[pc_before]
                event = machine.step()
            except Exception as exc:
                fault_type, fault_message = type(exc).__name__, str(exc)
                retain({
                    "kind": "execution_fault",
                    "run_id": run_id,
                    "pc": machine.pc,
                    "step_index": len(events),
                    "runtime_state": before,
                    "program_fingerprint": program_fp,
                    "ground_fingerprint": ground_fp,
                    "fault_type": fault_type,
                    "fault_message": fault_message,
                }, f"fault:{len(frames) + 1}", f"vgi-signal8://{run_id}/fault/{len(events)}")
                break

            if event is None:
                break
            events.append(event)
            after = runtime_state_id(machine)
            payload = {
                "kind": "instruction_transition",
                "status": "known",
                "scope": "one_concrete_execution_step",
                "run_id": run_id,
                "step_index": event.step,
                "pc_before": event.pc_before,
                "pc_after": event.pc_after,
                "source_state": before,
                "action": _action_id(machine, pc_before),
                "target": after,
                # Raw SignalValue data stays in raw_event; no symbol decoding here.
                "output": [],
                "raw_event": event.to_dict(),
                "instruction": instruction.to_dict(),
                "program_fingerprint": program_fp,
                "ground_fingerprint": ground_fp,
            }
            message, receipt = retain(
                payload, f"step:{len(events)}",
                f"vgi-signal8://{run_id}/step/{event.step}",
            )
            transition_messages.append((message, receipt))

        status = "faulted" if fault_type is not None else (
            "halted" if machine.halted else "step_limit"
        )
        encounters = exchange.to_encounter_ledger()
        evidence = tuple(
            TransitionEvidence.from_channel_message(
                exchange, message.message_id, receipt, encounters,
                ground_id=ground_id, context_digest=context_digest,
            )
            for message, receipt in transition_messages
        )
        return Signal8ExecutionCapture(
            run_id, status, context_digest, program_fp, ground_id, ground_fp,
            tuple(events), machine.result(), exchange, encounters,
            tuple(frames), evidence, fault_type, fault_message,
        )
