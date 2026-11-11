"""Verified execution-orbit ingestion and time-indexed navigation.

This module joins retained Signal8 execution traces to the existing partial
Ground and evidence-policy layers, then exposes exact logical-time navigation
under an explicitly declared deterministic policy.

A captured trace is observation, not a law. A reference match is not source
authentication. Evidence must still be explicitly finalized before a transition
appears in the constructed Ground. Future skipping is permitted only after a
closed deterministic orbit has been witnessed and replay-checked.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import hashlib
import json
from types import MappingProxyType
from typing import Any

from .evidence import (
    EvidenceError,
    ObservedOutcome,
    TransitionEvidence,
    TransitionEvidenceLedger,
    TransitionEvidencePolicy,
)
from .execution import Signal8ExecutionTrace
from .reference import ReferenceExecutionReport
from .transitions import (
    AmbiguousTransitionError,
    GroundTransitionSystem,
    TransitionStep,
    UnknownTransitionError,
)


class OrbitError(ValueError):
    """Invalid trace ingestion, orbit policy, or time-navigation request."""


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            _plain(value), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise OrbitError(f"value is not finite canonical JSON: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrbitError(f"{label} must be non-empty text")
    return value


def _require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise OrbitError(f"{label} must be a lowercase SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise OrbitError(f"{label} must be a lowercase SHA-256 digest") from exc
    return value


def _require_tick(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OrbitError(f"{label} must be a non-negative integer logical coordinate")
    return value


def _action_descriptor(pc: int, opcode: str, instruction_digest: str) -> str:
    return f"pc:{pc}:{opcode}:{instruction_digest}"


def _semantic_effect(event: Mapping[str, Any]) -> dict[str, Any]:
    """Project occurrence identity away while retaining the complete operation effect.

    Step index is a temporal coordinate, not part of the operation's semantic
    output. The pre-PC and opcode are already bound to the action descriptor.
    Post-PC remains in the effect because branch/control outcome is semantic.
    The original, unprojected event remains preserved and digest-checked in its
    source execution frame and Encounter.
    """
    if not isinstance(event, Mapping):
        raise OrbitError("semantic effect projection requires an ExecutionEvent object")
    excluded = {"step", "pc_before", "opcode"}
    return {key: _plain(value) for key, value in event.items() if key not in excluded}


@dataclass(frozen=True, slots=True)
class OrbitTimeCoordinate:
    """A logical tick in one named virtual orbit; never a wall-clock duration."""

    clock_id: str
    tick: int

    def __post_init__(self) -> None:
        _require_text(self.clock_id, "clock_id")
        _require_tick(self.tick, "tick")

    def advance(self, transitions: int) -> "OrbitTimeCoordinate":
        _require_tick(transitions, "transitions")
        return OrbitTimeCoordinate(self.clock_id, self.tick + transitions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clock_id": self.clock_id,
            "tick": self.tick,
            "basis": "logical_transition_coordinate",
        }


@dataclass(frozen=True, slots=True)
class EventToken:
    """One occurrence-normalized semantic effect encoded over base-eight channels."""

    code: int
    effect_digest: str
    canonical_effect_json: str

    def __post_init__(self) -> None:
        _require_tick(self.code, "event token code")
        _require_sha(self.effect_digest, "effect_digest")
        try:
            event = json.loads(self.canonical_effect_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise OrbitError("semantic-effect token JSON is malformed") from exc
        if _canonical(event) != self.canonical_effect_json:
            raise OrbitError("semantic-effect token JSON must be canonical")
        if _digest(event) != self.effect_digest:
            raise OrbitError("effect token digest does not identify its canonical semantic effect")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "effect_digest": self.effect_digest,
            "semantic_effect": json.loads(self.canonical_effect_json),
        }


@dataclass(frozen=True, slots=True)
class FrameDeliveryRecord:
    """One adapter-boundary delivery, duplicate, omission, or retained failure."""

    trace_id: str
    sequence: int
    logical_tick: int
    arrival_index: int | None
    disposition: str
    message_id: str | None = None
    encounter_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.trace_id, "trace_id")
        _require_tick(self.sequence, "sequence")
        if self.sequence < 1:
            raise OrbitError("frame sequence must be positive")
        _require_tick(self.logical_tick, "logical_tick")
        if self.arrival_index is not None:
            _require_tick(self.arrival_index, "arrival_index")
        if self.disposition not in (
            "accepted_transition", "retained_failure", "duplicate", "missing",
        ):
            raise OrbitError("unsupported frame delivery disposition")
        if self.disposition == "missing":
            if self.message_id is not None or self.encounter_id is not None or self.arrival_index is not None:
                raise OrbitError("missing frame cannot claim a message, Encounter, or arrival index")
        else:
            if self.arrival_index is None:
                raise OrbitError("delivered frame must retain its arrival index")
            _require_text(self.message_id, "delivered message_id")
            _require_text(self.encounter_id, "delivered encounter_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "sequence": self.sequence,
            "logical_tick": self.logical_tick,
            "arrival_index": self.arrival_index,
            "disposition": self.disposition,
            "message_id": self.message_id,
            "encounter_id": self.encounter_id,
        }


@dataclass(frozen=True, slots=True)
class TraceDeliverySummary:
    trace_id: str
    trace_fingerprint: str
    reference_fingerprint: str
    arrival_order: tuple[int, ...]
    accepted_sequences: tuple[int, ...]
    duplicate_sequences: tuple[int, ...]
    missing_sequences: tuple[int, ...]
    failure_sequences: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_text(self.trace_id, "trace_id")
        _require_sha(self.trace_fingerprint, "trace_fingerprint")
        _require_sha(self.reference_fingerprint, "reference_fingerprint")
        for field_name in (
            "arrival_order", "accepted_sequences", "duplicate_sequences",
            "missing_sequences", "failure_sequences",
        ):
            values = tuple(getattr(self, field_name))
            if any(isinstance(x, bool) or not isinstance(x, int) or x < 1 for x in values):
                raise OrbitError(f"{field_name} must contain positive frame sequences")
            object.__setattr__(self, field_name, values)
        if len(set(self.accepted_sequences)) != len(self.accepted_sequences):
            raise OrbitError("accepted frame sequences must be unique")
        if len(set(self.failure_sequences)) != len(self.failure_sequences):
            raise OrbitError("failed frame sequences must be unique")
        if len(set(self.missing_sequences)) != len(self.missing_sequences):
            raise OrbitError("missing frame sequences must be unique")
        if set(self.accepted_sequences) & set(self.failure_sequences):
            raise OrbitError("one frame cannot be both an accepted transition and a failure")
        if set(self.accepted_sequences) & set(self.missing_sequences):
            raise OrbitError("one frame cannot be both accepted and missing")
        if set(self.failure_sequences) & set(self.missing_sequences):
            raise OrbitError("one frame cannot be both failed and missing")
        first_seen: set[int] = set()
        derived_duplicates = []
        for sequence in self.arrival_order:
            if sequence in first_seen:
                derived_duplicates.append(sequence)
            else:
                first_seen.add(sequence)
        if tuple(derived_duplicates) != self.duplicate_sequences:
            raise OrbitError("duplicate sequence records do not match delivery arrival order")
        if set(self.accepted_sequences) | set(self.failure_sequences) != first_seen:
            raise OrbitError("every first-seen delivered frame must be accepted or retained as failure")
        maximum = max((*self.arrival_order, *self.missing_sequences), default=0)
        if set(range(1, maximum + 1)) != first_seen | set(self.missing_sequences):
            raise OrbitError("delivery and missing sequences must partition the contiguous frame range")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "trace_fingerprint": self.trace_fingerprint,
            "reference_fingerprint": self.reference_fingerprint,
            "arrival_order": list(self.arrival_order),
            "accepted_sequences": list(self.accepted_sequences),
            "duplicate_sequences": list(self.duplicate_sequences),
            "missing_sequences": list(self.missing_sequences),
            "failure_sequences": list(self.failure_sequences),
        }


@dataclass(frozen=True, slots=True)
class ExecutionOrbitIngestion:
    """Observed-only transition evidence plus the context needed to build a partial Ground."""

    ground_id: str
    context_digest: str
    clock_id: str
    base_tick: int
    program_fingerprint: str
    machine_ground_fingerprint: str
    initial_state_digest: str
    states: tuple[str, ...]
    actions: tuple[str, ...]
    channels: tuple[str, ...]
    event_tokens: tuple[EventToken, ...]
    deliveries: tuple[FrameDeliveryRecord, ...]
    trace_summaries: tuple[TraceDeliverySummary, ...]
    evidence_ledger: TransitionEvidenceLedger

    def __post_init__(self) -> None:
        _require_text(self.ground_id, "ground_id")
        _require_sha(self.context_digest, "context_digest")
        _require_text(self.clock_id, "clock_id")
        _require_tick(self.base_tick, "base_tick")
        _require_sha(self.program_fingerprint, "program_fingerprint")
        _require_sha(self.machine_ground_fingerprint, "machine_ground_fingerprint")
        _require_sha(self.initial_state_digest, "initial_state_digest")
        states = tuple(self.states)
        actions = tuple(self.actions)
        channels = tuple(self.channels)
        if not states or any(not isinstance(state, str) for state in states):
            raise OrbitError("execution-orbit states must be non-empty strings")
        if len(states) != len(set(states)):
            raise OrbitError("execution-orbit states must be unique")
        for state in states:
            _require_sha(state, "execution-orbit state digest")
        if self.initial_state_digest not in states:
            raise OrbitError("initial state digest must be retained in the state vocabulary")
        if not actions or any(not isinstance(action, str) or not action.strip() for action in actions):
            raise OrbitError("execution-orbit actions must be non-empty strings")
        if len(actions) != len(set(actions)):
            raise OrbitError("execution-orbit actions must be unique")
        if not channels or any(not isinstance(channel, str) or not channel.strip() for channel in channels):
            raise OrbitError("execution-orbit output channels must be non-empty strings")
        if len(channels) != len(set(channels)):
            raise OrbitError("execution-orbit output channels must be unique")
        expected_width = 1
        while 8 ** expected_width < max(1, len(self.event_tokens)):
            expected_width += 1
        if len(channels) != expected_width:
            raise OrbitError("output channel width does not encode the complete event-token codebook")
        if any(not isinstance(token, EventToken) for token in self.event_tokens):
            raise OrbitError("event_tokens must contain EventToken records")
        if tuple(token.code for token in self.event_tokens) != tuple(range(len(self.event_tokens))):
            raise OrbitError("event token codes must be contiguous and canonical")
        if any(not isinstance(item, FrameDeliveryRecord) for item in self.deliveries):
            raise OrbitError("deliveries must contain FrameDeliveryRecord records")
        if any(not isinstance(item, TraceDeliverySummary) for item in self.trace_summaries):
            raise OrbitError("trace_summaries must contain TraceDeliverySummary records")
        summary_ids = tuple(item.trace_id for item in self.trace_summaries)
        if not summary_ids or len(summary_ids) != len(set(summary_ids)):
            raise OrbitError("trace summaries must have unique trace identities")
        if any(item.trace_id not in set(summary_ids) for item in self.deliveries):
            raise OrbitError("delivery record refers to a trace outside the summary set")
        if any(item.logical_tick < self.base_tick for item in self.deliveries):
            raise OrbitError("delivery logical tick precedes the orbit origin")
        if not isinstance(self.evidence_ledger, TransitionEvidenceLedger):
            raise OrbitError("evidence_ledger must be a TransitionEvidenceLedger")
        for item in self.evidence_ledger.evidence:
            if item.source_state not in states or item.action not in actions:
                raise OrbitError("evidence event lies outside the execution-orbit vocabulary")
            if any(outcome.target not in states for outcome in item.outcomes):
                raise OrbitError("evidence successor lies outside the execution-orbit vocabulary")
            if any(len(outcome.output) != len(channels) for outcome in item.outcomes):
                raise OrbitError("evidence output width differs from the orbit codebook")
        if (
            self.evidence_ledger.policy.ground_id != self.ground_id
            or self.evidence_ledger.policy.context_digest != self.context_digest
        ):
            raise OrbitError("evidence policy does not bind this orbit Ground/context")
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "event_tokens", tuple(self.event_tokens))
        object.__setattr__(self, "deliveries", tuple(self.deliveries))
        object.__setattr__(self, "trace_summaries", tuple(self.trace_summaries))

    @property
    def initial_time(self) -> OrbitTimeCoordinate:
        return OrbitTimeCoordinate(self.clock_id, self.base_tick)

    @property
    def duplicate_count(self) -> int:
        return sum(item.disposition == "duplicate" for item in self.deliveries)

    @property
    def missing_count(self) -> int:
        return sum(item.disposition == "missing" for item in self.deliveries)

    @property
    def ignored_failure_count(self) -> int:
        return sum(item.disposition == "retained_failure" for item in self.deliveries)

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def time_for(self, trace_id: str, sequence: int) -> OrbitTimeCoordinate:
        _require_text(trace_id, "trace_id")
        _require_tick(sequence, "sequence")
        if sequence < 1:
            raise OrbitError("sequence must be positive")
        summary = next((item for item in self.trace_summaries if item.trace_id == trace_id), None)
        if summary is None:
            raise OrbitError("unknown trace_id")
        maximum = max((*summary.arrival_order, *summary.missing_sequences), default=0)
        if sequence > maximum:
            raise OrbitError("sequence lies outside the retained trace delivery envelope")
        return OrbitTimeCoordinate(self.clock_id, self.base_tick + sequence - 1)

    def decision(self, source_state: str, action: str):
        return self.evidence_ledger.status(source_state, action)

    def finalize(self, source_state: str, action: str) -> "ExecutionOrbitIngestion":
        """Explicitly finalize one observed event under the configured evidence policy."""
        return replace(
            self,
            evidence_ledger=self.evidence_ledger.finalize(source_state, action),
        )

    def build_ground(self) -> GroundTransitionSystem:
        """Build a partial Ground from AUTHORIZED finalizations only."""
        metadata = {
            "model": "vgi.signal8-execution-orbit.v1",
            "ground_id": self.ground_id,
            "context_digest": self.context_digest,
            "program_fingerprint": self.program_fingerprint,
            "machine_ground_fingerprint": self.machine_ground_fingerprint,
            "initial_state_digest": self.initial_state_digest,
            "clock": {
                "clock_id": self.clock_id,
                "basis": "logical_instruction_attempt",
                "base_tick": self.base_tick,
            },
            "ingestion_fingerprint": self.fingerprint,
            "trace_summaries": [item.to_dict() for item in self.trace_summaries],
            "event_tokens": [item.to_dict() for item in self.event_tokens],
            "delivery_counts": {
                "duplicates": self.duplicate_count,
                "missing": self.missing_count,
                "retained_failures_excluded_from_transitions": self.ignored_failure_count,
            },
        }
        try:
            return self.evidence_ledger.build_ground(
                states=self.states,
                actions=self.actions,
                initial_state=self.initial_state_digest,
                channels=self.channels,
                metadata=metadata,
            )
        except EvidenceError as exc:
            raise OrbitError(f"authorized execution evidence cannot build Ground: {exc}") from exc

    def derive_policy(self, system: GroundTransitionSystem | None = None) -> "OrbitPolicy":
        """Derive a state-to-action policy only from the supplied finalized Ground."""
        return OrbitPolicy.derive(self.build_ground() if system is None else system)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-ExecutionOrbitIngestion-1",
            "ground_id": self.ground_id,
            "context_digest": self.context_digest,
            "clock_id": self.clock_id,
            "base_tick": self.base_tick,
            "time_basis": "logical_instruction_attempt",
            "program_fingerprint": self.program_fingerprint,
            "machine_ground_fingerprint": self.machine_ground_fingerprint,
            "initial_state_digest": self.initial_state_digest,
            "states": list(self.states),
            "actions": list(self.actions),
            "channels": list(self.channels),
            "event_tokens": [item.to_dict() for item in self.event_tokens],
            "deliveries": [item.to_dict() for item in self.deliveries],
            "trace_summaries": [item.to_dict() for item in self.trace_summaries],
            "evidence_ledger": self.evidence_ledger.to_dict(),
            "scope": (
                "successful, independently reference-matched instruction frames delivered to this adapter; "
                "missing frames remain unknown and failed attempts are retained but not executable"
            ),
        }


class ExecutionOrbitAdapter:
    """Translate independently verified execution traces into policy-gated observations."""

    def ingest(
        self,
        traces: Sequence[Signal8ExecutionTrace],
        reference_reports: Sequence[ReferenceExecutionReport],
        *,
        delivery_orders: Mapping[str, Sequence[int]] | None = None,
        allowed_sources: Sequence[str] | None = None,
        quorum: int = 1,
        strict: bool = True,
        clock_id: str | None = None,
        base_tick: int = 0,
    ) -> ExecutionOrbitIngestion:
        if isinstance(traces, (str, bytes)) or not isinstance(traces, Sequence):
            raise OrbitError("traces must be a finite sequence of Signal8ExecutionTrace records")
        if isinstance(reference_reports, (str, bytes)) or not isinstance(reference_reports, Sequence):
            raise OrbitError("reference_reports must be a finite sequence")
        trace_items = tuple(traces)
        reports = tuple(reference_reports)
        if not trace_items or len(trace_items) != len(reports):
            raise OrbitError("one independent reference report is required for every trace")
        if delivery_orders is not None and not isinstance(delivery_orders, Mapping):
            raise OrbitError("delivery_orders must map trace IDs to delivery sequences")
        if delivery_orders is not None:
            unknown_trace_ids = set(delivery_orders) - {item.trace_id for item in trace_items}
            if unknown_trace_ids:
                raise OrbitError(
                    f"delivery_orders refers to unknown traces: {sorted(unknown_trace_ids)}"
                )
            if any(
                isinstance(order, (str, bytes)) or not isinstance(order, Sequence)
                for order in delivery_orders.values()
            ):
                raise OrbitError("each delivery order must be a finite sequence of frame numbers")
        if allowed_sources is not None and isinstance(allowed_sources, (str, bytes)):
            raise OrbitError("allowed_sources must be a sequence of source identities")
        if allowed_sources is not None and any(
            not isinstance(source, str) or not source.strip()
            for source in allowed_sources
        ):
            raise OrbitError("allowed_sources must contain non-empty source identity strings")
        if isinstance(quorum, bool) or not isinstance(quorum, int) or quorum < 1:
            raise OrbitError("quorum must be a positive integer")
        if not isinstance(strict, bool):
            raise OrbitError("strict must be Boolean")
        if any(not isinstance(item, Signal8ExecutionTrace) for item in trace_items):
            raise OrbitError("all traces must be Signal8ExecutionTrace records")
        if any(not isinstance(item, ReferenceExecutionReport) for item in reports):
            raise OrbitError("all reference reports must be ReferenceExecutionReport records")
        if len({item.trace_id for item in trace_items}) != len(trace_items):
            raise OrbitError("trace identifiers must be unique within an ingestion")
        _require_tick(base_tick, "base_tick")

        first = trace_items[0]
        for trace, report in zip(trace_items, reports):
            if report.status != "match":
                raise OrbitError("only an independently matched execution trace may enter orbit ingestion")
            if (
                report.trace_id != trace.trace_id
                or report.trace_fingerprint != trace.fingerprint
                or report.program_fingerprint != trace.program_fingerprint
                or report.ground_fingerprint != trace.ground_fingerprint
            ):
                raise OrbitError("reference report does not bind the exact trace, Program, and Ground")
            if (
                trace.program_fingerprint != first.program_fingerprint
                or trace.ground_fingerprint != first.ground_fingerprint
                or trace.initial_state_digest != first.initial_state_digest
            ):
                raise OrbitError("all traces must share Program, machine Ground, and initial state")

        program = _plain(first.program_definition)
        instructions = program.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise OrbitError("retained Program has no instruction sequence")
        action_by_pc = {}
        for pc, instruction in enumerate(instructions):
            if not isinstance(instruction, Mapping):
                raise OrbitError(f"Program instruction {pc} is not an object")
            opcode = instruction.get("op")
            if not isinstance(opcode, str):
                raise OrbitError(f"Program instruction {pc} has no opcode")
            instruction_digest = _digest(instruction)
            action_by_pc[pc] = _action_descriptor(pc, opcode, instruction_digest)
        actions = tuple(action_by_pc[index] for index in range(len(action_by_pc)))

        all_sources = sorted({
            message.provenance.source
            for trace in trace_items
            for message in trace.exchange.messages
        })
        sources = tuple(sorted(set(all_sources if allowed_sources is None else allowed_sources)))
        if not sources or any(not isinstance(item, str) or not item for item in sources):
            raise OrbitError("allowed_sources must contain at least one source identity")
        if any(message_source not in sources for message_source in all_sources):
            raise OrbitError("allowed_sources excludes a source retained by one of the traces")

        raw_deliveries: list[FrameDeliveryRecord] = []
        summaries: list[TraceDeliverySummary] = []
        accepted: list[tuple[Signal8ExecutionTrace, ReferenceExecutionReport, Any, Any, str]] = []
        state_names = {first.initial_state_digest}
        effect_signatures: set[str] = set()

        for trace, report in zip(trace_items, reports):
            entries_by_sequence = {item.sequence: item for item in trace.entries}
            messages = {item.message_id: item for item in trace.exchange.messages}
            order = (
                tuple(range(1, len(trace.entries) + 1))
                if delivery_orders is None or trace.trace_id not in delivery_orders
                else tuple(delivery_orders[trace.trace_id])
            )
            if any(
                isinstance(sequence, bool) or not isinstance(sequence, int)
                or sequence < 1 or sequence > len(trace.entries)
                for sequence in order
            ):
                raise OrbitError(f"delivery order for {trace.trace_id!r} contains an unknown sequence")
            seen: set[int] = set()
            accepted_sequences: list[int] = []
            duplicate_sequences: list[int] = []
            failure_sequences: list[int] = []
            for arrival_index, sequence in enumerate(order):
                entry = entries_by_sequence[sequence]
                if sequence in seen:
                    duplicate_sequences.append(sequence)
                    raw_deliveries.append(FrameDeliveryRecord(
                        trace.trace_id, sequence, base_tick + entry.step_index,
                        arrival_index, "duplicate", entry.message_id, entry.encounter_id,
                    ))
                    continue
                seen.add(sequence)
                if entry.record_type == "execution_failure":
                    failure_sequences.append(sequence)
                    raw_deliveries.append(FrameDeliveryRecord(
                        trace.trace_id, sequence, base_tick + entry.step_index,
                        arrival_index, "retained_failure", entry.message_id, entry.encounter_id,
                    ))
                    continue
                message = messages.get(entry.message_id)
                if message is None:
                    raise OrbitError("delivered frame has no retained channel message")
                encounter = trace.encounters.get(entry.encounter_id)
                if encounter.payload != message.payload or encounter.provenance != message.provenance:
                    raise OrbitError("delivered Encounter does not preserve its exact channel message")
                payload = _plain(message.payload)
                event = payload.get("event")
                if not isinstance(event, Mapping):
                    raise OrbitError("successful frame has no raw ExecutionEvent")
                if _digest(event) != entry.event_digest:
                    raise OrbitError("ExecutionEvent digest differs from its retained frame")
                # Keep the exact event in the source trace/Encounter, but remove
                # occurrence-only coordinates from the semantic output token.
                event_json = _canonical(_semantic_effect(event))
                pc = payload.get("pc_before")
                if isinstance(pc, bool) or not isinstance(pc, int) or pc not in action_by_pc:
                    raise OrbitError("frame program counter is outside its retained Program")
                if payload.get("instruction_digest") != entry.instruction_digest:
                    raise OrbitError("frame instruction digest differs from its retained definition")
                action = action_by_pc[pc]
                if (
                    payload.get("opcode") != instructions[pc].get("op")
                    or action != _action_descriptor(pc, payload["opcode"], entry.instruction_digest)
                ):
                    raise OrbitError("frame action does not match the retained Program instruction")
                effect_signatures.add(event_json)
                state_names.update((entry.state_before_digest, entry.state_after_digest))
                accepted.append((trace, report, entry, event_json, action))
                accepted_sequences.append(sequence)
                raw_deliveries.append(FrameDeliveryRecord(
                    trace.trace_id, sequence, base_tick + entry.step_index,
                    arrival_index, "accepted_transition", entry.message_id, entry.encounter_id,
                ))
            missing_sequences = tuple(
                sequence for sequence in range(1, len(trace.entries) + 1)
                if sequence not in seen
            )
            for sequence in missing_sequences:
                raw_deliveries.append(FrameDeliveryRecord(
                    trace.trace_id, sequence, base_tick + sequence - 1,
                    None, "missing",
                ))
            summaries.append(TraceDeliverySummary(
                trace_id=trace.trace_id,
                trace_fingerprint=trace.fingerprint,
                reference_fingerprint=report.fingerprint,
                arrival_order=tuple(order),
                accepted_sequences=tuple(accepted_sequences),
                duplicate_sequences=tuple(duplicate_sequences),
                missing_sequences=missing_sequences,
                failure_sequences=tuple(failure_sequences),
            ))

        signatures = tuple(sorted(effect_signatures))
        event_tokens = tuple(
            EventToken(code, _digest(json.loads(signature)), signature)
            for code, signature in enumerate(signatures)
        )
        token_by_effect_json = {item.canonical_effect_json: item.code for item in event_tokens}
        output_width = 1
        while 8 ** output_width < max(1, len(event_tokens)):
            output_width += 1
        channels = tuple(f"event_token_base8_{index}" for index in range(output_width))

        report_by_trace = {trace.trace_id: report for trace, report in zip(trace_items, reports)}
        trace_fingerprints = [
            {"trace_id": trace.trace_id, "trace_fingerprint": trace.fingerprint,
             "reference_fingerprint": report_by_trace[trace.trace_id].fingerprint}
            for trace in trace_items
        ]
        clock_identifier = clock_id or (
            "vgi-orbit:" + _digest({
                "program_fingerprint": first.program_fingerprint,
                "ground_fingerprint": first.ground_fingerprint,
                "initial_state_digest": first.initial_state_digest,
            })
        )
        _require_text(clock_identifier, "clock_id")
        context_payload = {
            "format": "VGI-ExecutionOrbitContext-1",
            "program_fingerprint": first.program_fingerprint,
            "machine_ground_fingerprint": first.ground_fingerprint,
            "initial_state_digest": first.initial_state_digest,
            "clock_id": clock_identifier,
            "base_tick": base_tick,
            "trace_fingerprints": trace_fingerprints,
            "event_tokens": [item.to_dict() for item in event_tokens],
            "channels": list(channels),
            "allowed_sources": list(sources),
            "quorum": quorum,
            "strict": strict,
        }
        context_digest = _digest(context_payload)
        ground_id = "signal8-orbit:" + _digest({
            "program_fingerprint": first.program_fingerprint,
            "machine_ground_fingerprint": first.ground_fingerprint,
            "initial_state_digest": first.initial_state_digest,
            "context_digest": context_digest,
        })
        try:
            policy = TransitionEvidencePolicy(
                ground_id, context_digest, sources, quorum, strict,
            )
            ledger = TransitionEvidenceLedger(policy)
            reference_by_trace = {trace.trace_id: report for trace, report in zip(trace_items, reports)}
            for trace, report, entry, event_json, action in accepted:
                message = next(
                    item for item in trace.exchange.messages
                    if item.message_id == entry.message_id
                )
                code = token_by_effect_json[event_json]
                output = tuple((code // (8 ** index)) % 8 for index in range(output_width))
                evidence_id = _digest({
                    "trace_id": trace.trace_id,
                    "sequence": entry.sequence,
                    "message_id": entry.message_id,
                    "event_digest": entry.event_digest,
                })
                evidence = TransitionEvidence(
                    evidence_id=evidence_id,
                    encounter_id=entry.encounter_id,
                    message_id=entry.message_id,
                    channel_id=entry.receipt.channel_id,
                    protocol_id=message.protocol_id,
                    transport_id=entry.receipt.transport_id,
                    frame_id=entry.receipt.frame_id,
                    transport_sequence=entry.receipt.sequence,
                    source=message.provenance.source,
                    ground_id=ground_id,
                    context_digest=context_digest,
                    source_state=entry.state_before_digest,
                    action=action,
                    status="known",
                    outcomes=(ObservedOutcome(entry.state_after_digest, output),),
                    payload_digest=entry.receipt.payload_digest,
                    correlation_id=message.correlation_id,
                    source_model_fingerprint=trace.ground_fingerprint,
                )
                ledger = ledger.ingest(evidence)
        except (EvidenceError, StopIteration) as exc:
            raise OrbitError(f"execution observations could not enter the policy ledger: {exc}") from exc

        return ExecutionOrbitIngestion(
            ground_id=ground_id,
            context_digest=context_digest,
            clock_id=clock_identifier,
            base_tick=base_tick,
            program_fingerprint=first.program_fingerprint,
            machine_ground_fingerprint=first.ground_fingerprint,
            initial_state_digest=first.initial_state_digest,
            states=tuple(sorted(state_names)),
            actions=actions,
            channels=channels,
            event_tokens=event_tokens,
            deliveries=tuple(raw_deliveries),
            trace_summaries=tuple(summaries),
            evidence_ledger=ledger,
        )


@dataclass(frozen=True, slots=True)
class OrbitPolicy:
    """A deterministic state-to-action choice, separate from transition semantics."""

    system_fingerprint: str
    actions_by_state: Mapping[str, str]
    policy_ambiguous_states: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        _require_sha(self.system_fingerprint, "system_fingerprint")
        if not isinstance(self.actions_by_state, Mapping):
            raise OrbitError("actions_by_state must be a mapping")
        if not isinstance(self.policy_ambiguous_states, Mapping):
            raise OrbitError("policy_ambiguous_states must be a mapping")
        actions = dict(self.actions_by_state)
        ambiguous = {}
        for state, values in self.policy_ambiguous_states.items():
            if isinstance(values, (str, bytes)):
                raise OrbitError("ambiguous policy alternatives must be a sequence of action names")
            try:
                ambiguous[state] = tuple(values)
            except TypeError as exc:
                raise OrbitError("ambiguous policy alternatives must be finite sequences") from exc
        if set(actions) & set(ambiguous):
            raise OrbitError("a state cannot have both a selected action and an ambiguous policy")
        if any(not isinstance(state, str) or not state
               or not isinstance(action, str) or not action
               for state, action in actions.items()):
            raise OrbitError("policy states and actions must be non-empty strings")
        if any(
            not isinstance(state, str) or not state
            or len(values) < 2 or len(set(values)) != len(values)
            or any(not isinstance(action, str) or not action for action in values)
            for state, values in ambiguous.items()
        ):
            raise OrbitError("ambiguous policy states require at least two distinct action names")
        object.__setattr__(self, "actions_by_state", MappingProxyType(actions))
        object.__setattr__(self, "policy_ambiguous_states", MappingProxyType(ambiguous))

    @classmethod
    def derive(cls, system: GroundTransitionSystem) -> "OrbitPolicy":
        """Choose the sole observed action per state; transition status is checked separately."""
        if not isinstance(system, GroundTransitionSystem):
            raise OrbitError("OrbitPolicy.derive requires a GroundTransitionSystem")
        by_state: dict[str, list[str]] = {state: [] for state in system.states}
        for item in system.observations:
            by_state[item.source].append(item.action)
        selected: dict[str, str] = {}
        ambiguous: dict[str, tuple[str, ...]] = {}
        for state, actions in by_state.items():
            choices = tuple(sorted(set(actions)))
            if len(choices) == 1:
                # A single selected action may still have an ambiguous outcome;
                # OrbitNavigator checks edge status separately before advancing.
                selected[state] = choices[0]
            elif len(choices) > 1:
                ambiguous[state] = choices
        return cls(system.fingerprint, selected, ambiguous)

    @classmethod
    def from_mapping(
        cls, system: GroundTransitionSystem, actions_by_state: Mapping[str, str],
    ) -> "OrbitPolicy":
        if not isinstance(system, GroundTransitionSystem):
            raise OrbitError("OrbitPolicy.from_mapping requires a GroundTransitionSystem")
        if not isinstance(actions_by_state, Mapping):
            raise OrbitError("actions_by_state must be a mapping")
        mapping = dict(actions_by_state)
        for state, action in mapping.items():
            if state not in system.states or action not in system.actions:
                raise OrbitError("policy refers to an undeclared state or action")
        return cls(system.fingerprint, mapping, {})

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-OrbitPolicy-1",
            "system_fingerprint": self.system_fingerprint,
            "actions_by_state": dict(self.actions_by_state),
            "policy_ambiguous_states": {
                key: list(value) for key, value in self.policy_ambiguous_states.items()
            },
        }


@dataclass(frozen=True, slots=True)
class OrbitPathStep:
    source_state: str
    action: str
    target_state: str
    output: tuple[int, ...]
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.source_state, "source_state")
        _require_text(self.action, "action")
        _require_text(self.target_state, "target_state")
        output = tuple(self.output)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in output):
            raise OrbitError("orbit path outputs must be integer tuples")
        evidence = tuple(self.evidence)
        if any(not isinstance(item, str) or not item for item in evidence):
            raise OrbitError("orbit path evidence references must be non-empty strings")
        object.__setattr__(self, "output", output)
        object.__setattr__(self, "evidence", evidence)

    @classmethod
    def from_transition(cls, step: TransitionStep) -> "OrbitPathStep":
        return cls(step.source, step.action, step.target, step.output, step.evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_state": self.source_state,
            "action": self.action,
            "target_state": self.target_state,
            "output": list(self.output),
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class OrbitNavigationResult:
    status: str
    clock_id: str
    requested_time: OrbitTimeCoordinate | None
    resolved_time: OrbitTimeCoordinate | None
    state: str | None
    target_state: str | None
    method: str | None
    skipped_cycles: int
    skipped_steps: int
    cycle_start_time: OrbitTimeCoordinate | None
    cycle_period: int | None
    path_fingerprint: str
    evidence: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        allowed = {
            "located", "unreachable_on_closed_orbit", "blocked_unknown",
            "blocked_ambiguous", "policy_missing", "policy_ambiguous",
            "horizon_exhausted", "clock_mismatch", "before_origin",
            "undeclared_target",
        }
        if self.status not in allowed:
            raise OrbitError("unsupported orbit-navigation result status")
        _require_text(self.clock_id, "clock_id")
        _require_sha(self.path_fingerprint, "path_fingerprint")
        if self.requested_time is not None and not isinstance(self.requested_time, OrbitTimeCoordinate):
            raise OrbitError("requested_time must be an OrbitTimeCoordinate")
        if self.resolved_time is not None and not isinstance(self.resolved_time, OrbitTimeCoordinate):
            raise OrbitError("resolved_time must be an OrbitTimeCoordinate")
        if self.cycle_start_time is not None and not isinstance(self.cycle_start_time, OrbitTimeCoordinate):
            raise OrbitError("cycle_start_time must be an OrbitTimeCoordinate")
        for name in ("skipped_cycles", "skipped_steps"):
            _require_tick(getattr(self, name), name)
        if self.resolved_time is not None and self.resolved_time.clock_id != self.clock_id:
            raise OrbitError("resolved time belongs to another orbit clock")
        if self.cycle_start_time is not None and self.cycle_start_time.clock_id != self.clock_id:
            raise OrbitError("cycle start belongs to another orbit clock")
        if self.requested_time is not None and self.status != "clock_mismatch":
            if self.requested_time.clock_id != self.clock_id:
                raise OrbitError("requested time belongs to another orbit clock")
        if self.status == "located" and (
            self.state is None or self.resolved_time is None
            or self.requested_time is None
            or self.method not in ("compiled_prefix", "cycle_skip")
        ):
            raise OrbitError("located result must retain its state, requested/resolved times, and method")
        if self.status == "located":
            _require_text(self.state, "located state")
        if self.status != "located" and self.resolved_time is not None:
            raise OrbitError("non-located result cannot claim a resolved logical time")
        if self.method == "cycle_skip" and self.skipped_cycles < 1:
            raise OrbitError("cycle_skip must report at least one skipped cycle")
        if self.method == "compiled_prefix" and (self.skipped_cycles or self.skipped_steps):
            raise OrbitError("compiled-prefix navigation cannot report skipped work")
        if self.status == "unreachable_on_closed_orbit" and (
            self.cycle_start_time is None or self.cycle_period is None
        ):
            raise OrbitError("unreachable_on_closed_orbit requires a closed-cycle certificate")
        if (self.cycle_start_time is None) != (self.cycle_period is None):
            raise OrbitError("cycle start and period must either both be present or both absent")
        if self.target_state is not None:
            _require_text(self.target_state, "target_state")
        if self.method is not None:
            _require_text(self.method, "method")
        if self.cycle_period is not None:
            _require_tick(self.cycle_period, "cycle_period")
            if self.cycle_period < 1:
                raise OrbitError("cycle_period must be positive")
        evidence = tuple(self.evidence)
        if any(not isinstance(item, str) or not item for item in evidence):
            raise OrbitError("evidence references must be non-empty strings")
        object.__setattr__(self, "evidence", tuple(sorted(set(evidence))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-OrbitNavigationResult-1",
            "status": self.status,
            "clock_id": self.clock_id,
            "requested_time": None if self.requested_time is None else self.requested_time.to_dict(),
            "resolved_time": None if self.resolved_time is None else self.resolved_time.to_dict(),
            "state": self.state,
            "target_state": self.target_state,
            "method": self.method,
            "skipped_cycles": self.skipped_cycles,
            "skipped_steps": self.skipped_steps,
            "cycle_start_time": None if self.cycle_start_time is None else self.cycle_start_time.to_dict(),
            "cycle_period": self.cycle_period,
            "path_fingerprint": self.path_fingerprint,
            "evidence": list(self.evidence),
            "reason": self.reason,
        }

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class OrbitIndex:
    """A replay-checked finite prefix and, when found, one closed deterministic cycle."""

    system: GroundTransitionSystem
    policy: OrbitPolicy
    start_state: str
    start_time: OrbitTimeCoordinate
    states: tuple[str, ...]
    steps: tuple[OrbitPathStep, ...]
    cycle_start_index: int | None
    cycle_period: int | None
    stop_status: str

    def __post_init__(self) -> None:
        if not isinstance(self.system, GroundTransitionSystem) or not isinstance(self.policy, OrbitPolicy):
            raise OrbitError("OrbitIndex requires a Ground and OrbitPolicy")
        if self.policy.system_fingerprint != self.system.fingerprint:
            raise OrbitError("orbit policy belongs to a different Ground")
        if self.start_state not in self.system.states:
            raise OrbitError("orbit start state is outside the Ground")
        if not isinstance(self.start_time, OrbitTimeCoordinate):
            raise OrbitError("orbit start time must be an OrbitTimeCoordinate")
        states, steps = tuple(self.states), tuple(self.steps)
        if len(states) != len(steps) + 1 or not states or states[0] != self.start_state:
            raise OrbitError("orbit path state/step cardinalities are inconsistent")
        for index, step in enumerate(steps):
            if step.source_state != states[index] or step.target_state != states[index + 1]:
                raise OrbitError("orbit path is discontinuous")
            if self.policy.actions_by_state.get(step.source_state) != step.action:
                raise OrbitError("orbit path step does not follow its declared policy")
            observed = self.system.step(step.source_state, step.action, index=index)
            if (
                observed.target != step.target_state
                or observed.output != step.output
                or observed.evidence != step.evidence
            ):
                raise OrbitError("orbit path step does not replay against its Ground")
        if self.cycle_start_index is not None:
            if (isinstance(self.cycle_start_index, bool)
                    or not isinstance(self.cycle_start_index, int)
                    or self.cycle_start_index < 0
                    or self.cycle_start_index >= len(steps)):
                raise OrbitError("cycle_start_index must identify an existing retained transition")
            if (isinstance(self.cycle_period, bool)
                    or not isinstance(self.cycle_period, int)
                    or self.cycle_period < 1):
                raise OrbitError("cycle_period must be a positive integer")
        if self.cycle_start_index is None:
            if self.cycle_period is not None or self.stop_status == "cycle":
                raise OrbitError("cycle status requires cycle coordinates")
            if self.stop_status not in (
                "blocked_unknown", "blocked_ambiguous", "policy_missing",
                "policy_ambiguous", "horizon_exhausted",
            ):
                raise OrbitError("non-cyclic orbit has an invalid stopping status")
        else:
            if self.cycle_period is None:
                raise OrbitError("closed orbit requires a positive cycle period")
            if self.cycle_start_index + self.cycle_period != len(steps):
                raise OrbitError("cycle period does not close at the retained path endpoint")
            if states[self.cycle_start_index] != states[-1]:
                raise OrbitError("cycle endpoint does not return to its starting state")
            if self.stop_status != "cycle":
                raise OrbitError("closed orbit stop_status must be cycle")
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "steps", steps)

    @property
    def closed(self) -> bool:
        return self.cycle_start_index is not None

    @property
    def cycle_start_time(self) -> OrbitTimeCoordinate | None:
        if self.cycle_start_index is None:
            return None
        return self.start_time.advance(self.cycle_start_index)

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-OrbitIndex-1",
            "system_fingerprint": self.system.fingerprint,
            "policy": self.policy.to_dict(),
            "start_state": self.start_state,
            "start_time": self.start_time.to_dict(),
            "states": list(self.states),
            "steps": [item.to_dict() for item in self.steps],
            "cycle_start_index": self.cycle_start_index,
            "cycle_period": self.cycle_period,
            "stop_status": self.stop_status,
            "scope": (
                "logical-time navigation under one fixed state-to-action policy; "
                "all indexed edges are known singleton transitions"
            ),
        }

    def _evidence_for(self, offset: int, *, cycle_skip: bool = False) -> tuple[str, ...]:
        if cycle_skip and self.cycle_start_index is not None:
            steps = self.steps
        else:
            steps = self.steps[:max(0, min(offset, len(self.steps)))]
        return tuple(sorted({item for step in steps for item in step.evidence}))

    def state_at(self, requested_time: OrbitTimeCoordinate) -> OrbitNavigationResult:
        if not isinstance(requested_time, OrbitTimeCoordinate):
            raise OrbitError("state_at requires an OrbitTimeCoordinate")
        if requested_time.clock_id != self.start_time.clock_id:
            return OrbitNavigationResult(
                "clock_mismatch", self.start_time.clock_id, requested_time, None,
                None, None, None, 0, 0, self.cycle_start_time, self.cycle_period,
                self.fingerprint, reason="requested time belongs to another logical clock",
            )
        if requested_time.tick < self.start_time.tick:
            return OrbitNavigationResult(
                "before_origin", self.start_time.clock_id, requested_time, None,
                None, None, None, 0, 0, self.cycle_start_time, self.cycle_period,
                self.fingerprint, reason="requested time precedes the orbit origin",
            )
        offset = requested_time.tick - self.start_time.tick
        if offset < len(self.states):
            return OrbitNavigationResult(
                "located", self.start_time.clock_id, requested_time, requested_time,
                self.states[offset], None, "compiled_prefix", 0, 0,
                self.cycle_start_time, self.cycle_period, self.fingerprint,
                self._evidence_for(offset),
            )
        if self.cycle_start_index is not None:
            cycle_start = self.cycle_start_index
            period = self.cycle_period
            reduced = cycle_start + ((offset - cycle_start) % period)
            skipped = (offset - reduced) // period
            return OrbitNavigationResult(
                "located", self.start_time.clock_id, requested_time, requested_time,
                self.states[reduced], None, "cycle_skip", skipped,
                offset - reduced, self.cycle_start_time, period,
                self.fingerprint, self._evidence_for(len(self.steps), cycle_skip=True),
            )
        return OrbitNavigationResult(
            self.stop_status, self.start_time.clock_id, requested_time, None,
            None, None, None, 0, 0, None, None, self.fingerprint,
            self._evidence_for(len(self.steps)),
            reason=f"orbit compilation stopped before logical offset {offset}",
        )

    def locate_state(
        self,
        target_state: str,
        *,
        from_time: OrbitTimeCoordinate | None = None,
    ) -> OrbitNavigationResult:
        _require_text(target_state, "target_state")
        earliest = self.start_time if from_time is None else from_time
        if not isinstance(earliest, OrbitTimeCoordinate):
            raise OrbitError("from_time must be an OrbitTimeCoordinate")
        if earliest.clock_id != self.start_time.clock_id:
            return OrbitNavigationResult(
                "clock_mismatch", self.start_time.clock_id, earliest, None,
                None, target_state, None, 0, 0, self.cycle_start_time,
                self.cycle_period, self.fingerprint, reason="search origin belongs to another logical clock",
            )
        if target_state not in self.system.states:
            return OrbitNavigationResult(
                "undeclared_target", self.start_time.clock_id, earliest, None,
                None, target_state, None, 0, 0, self.cycle_start_time,
                self.cycle_period, self.fingerprint, reason="target is outside the declared Ground",
            )
        if earliest.tick < self.start_time.tick:
            return OrbitNavigationResult(
                "before_origin", self.start_time.clock_id, earliest, None,
                None, target_state, None, 0, 0, self.cycle_start_time,
                self.cycle_period, self.fingerprint, reason="search begins before the orbit origin",
            )
        lower = earliest.tick - self.start_time.tick

        if self.cycle_start_index is None:
            for offset in range(lower, len(self.states)):
                if self.states[offset] == target_state:
                    resolved = self.start_time.advance(offset)
                    return OrbitNavigationResult(
                        "located", self.start_time.clock_id, earliest, resolved,
                        target_state, target_state, "compiled_prefix", 0, 0,
                        None, None, self.fingerprint, self._evidence_for(offset),
                    )
            return OrbitNavigationResult(
                self.stop_status, self.start_time.clock_id, earliest, None,
                None, target_state, None, 0, 0, None, None, self.fingerprint,
                self._evidence_for(len(self.steps)),
                reason="target was not observed before orbit compilation stopped",
            )

        cycle_start = self.cycle_start_index
        period = self.cycle_period
        candidates: list[int] = []
        for offset in range(min(cycle_start, len(self.states))):
            if offset >= lower and self.states[offset] == target_state:
                candidates.append(offset)
        for cycle_offset in range(cycle_start, cycle_start + period):
            if self.states[cycle_offset] == target_state:
                if cycle_offset >= lower:
                    candidates.append(cycle_offset)
                else:
                    jumps = (lower - cycle_offset + period - 1) // period
                    candidates.append(cycle_offset + jumps * period)
        if not candidates:
            return OrbitNavigationResult(
                "unreachable_on_closed_orbit", self.start_time.clock_id,
                earliest, None, None, target_state, None, 0, 0,
                self.cycle_start_time, period, self.fingerprint,
                self._evidence_for(len(self.steps), cycle_skip=True),
                reason="target does not occur on this closed deterministic orbit",
            )
        offset = min(candidates)
        reduced = (
            offset if offset < len(self.states)
            else cycle_start + ((offset - cycle_start) % period)
        )
        skipped = max(0, (offset - reduced) // period)
        resolved = self.start_time.advance(offset)
        return OrbitNavigationResult(
            "located", self.start_time.clock_id, earliest, resolved,
            target_state, target_state,
            "cycle_skip" if skipped else "compiled_prefix",
            skipped, offset - reduced, self.cycle_start_time, period,
            self.fingerprint, self._evidence_for(len(self.steps), cycle_skip=True),
        )


class OrbitNavigator:
    """Compile and navigate a deterministic orbit without expanding skipped cycles."""

    @staticmethod
    def compile(
        system: GroundTransitionSystem,
        policy: OrbitPolicy,
        *,
        start_state: str,
        start_time: OrbitTimeCoordinate,
        max_transitions: int | None = None,
    ) -> OrbitIndex:
        if not isinstance(system, GroundTransitionSystem):
            raise OrbitError("OrbitNavigator requires a GroundTransitionSystem")
        if not isinstance(policy, OrbitPolicy) or policy.system_fingerprint != system.fingerprint:
            raise OrbitError("OrbitNavigator policy does not belong to this Ground")
        if not isinstance(start_time, OrbitTimeCoordinate):
            raise OrbitError("start_time must be an OrbitTimeCoordinate")
        if start_state not in system.states:
            raise OrbitError("start_state is outside the Ground")
        if max_transitions is None:
            bound = len(system.states)
        else:
            bound = _require_tick(max_transitions, "max_transitions")
            if bound < 1:
                raise OrbitError("max_transitions must be positive")
            bound = min(bound, len(system.states))

        states = [start_state]
        steps: list[OrbitPathStep] = []
        seen: dict[str, int] = {}
        current = start_state
        cycle_start = None
        cycle_period = None
        stop_status = "horizon_exhausted"

        while True:
            if current in seen:
                cycle_start = seen[current]
                cycle_period = len(steps) - cycle_start
                stop_status = "cycle"
                break
            seen[current] = len(steps)
            if len(steps) >= bound:
                stop_status = "horizon_exhausted"
                break
            action = policy.actions_by_state.get(current)
            if action is None:
                stop_status = (
                    "policy_ambiguous" if current in policy.policy_ambiguous_states
                    else "policy_missing"
                )
                break
            edge_status = system.status(current, action)
            if edge_status == "unknown":
                stop_status = "blocked_unknown"
                break
            if edge_status == "ambiguous":
                stop_status = "blocked_ambiguous"
                break
            try:
                transition = system.step(current, action, index=len(steps))
            except (UnknownTransitionError, AmbiguousTransitionError) as exc:
                raise OrbitError(f"Ground status changed during immutable navigation: {exc}") from exc
            steps.append(OrbitPathStep.from_transition(transition))
            current = transition.target
            states.append(current)

        return OrbitIndex(
            system=system,
            policy=policy,
            start_state=start_state,
            start_time=start_time,
            states=tuple(states),
            steps=tuple(steps),
            cycle_start_index=cycle_start,
            cycle_period=cycle_period,
            stop_status=stop_status,
        )


__all__ = [
    "OrbitError", "OrbitTimeCoordinate", "EventToken", "FrameDeliveryRecord",
    "TraceDeliverySummary", "ExecutionOrbitIngestion", "ExecutionOrbitAdapter",
    "OrbitPolicy", "OrbitPathStep", "OrbitNavigationResult", "OrbitIndex",
    "OrbitNavigator",
]
