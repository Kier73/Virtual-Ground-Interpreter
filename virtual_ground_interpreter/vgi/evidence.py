"""Policy-gated transition evidence and finite Ground reconstruction certificates.

Observation, model admission, and compiled replay are three separate claims.
The module binds channel observations to retained Encounters and transport
frames, admits transitions only after explicit policy finalization, and issues
a bounded replay certificate only for complete Grounds supported by the current
VGI compiler. It never proves that a Ground exhausts an external system.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .channels import ChannelExchangeLedger
from .encounters import EncounterLedger
from .transitions import (
    GroundTransitionSystem, TransitionObservation, TransitionOutcome,
    TransitionSystemError, differential_verify,
)


class EvidenceError(ValueError):
    """Invalid evidence, policy, finalization, or reconstruction certificate."""


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{name} must be a non-empty string")
    return value


def _positive(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise EvidenceError(f"{name} must be a positive integer")
    return value


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise EvidenceError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"value is not canonical JSON: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class ObservedOutcome:
    """Reported successor and output, not yet an admitted Ground transition."""

    target: str
    output: tuple[int, ...]

    def __post_init__(self) -> None:
        _text(self.target, "outcome target")
        output = tuple(self.output)
        if any(isinstance(x, bool) or not isinstance(x, int) or not 0 <= x <= 7 for x in output):
            raise EvidenceError("output values must be integers in Z/8Z")
        object.__setattr__(self, "output", output)

    def to_dict(self) -> dict[str, Any]:
        return {"target": self.target, "output": list(self.output)}


@dataclass(frozen=True, slots=True)
class TransitionEvidencePolicy:
    """Declared source authority and quorum for one Ground/context revision."""

    ground_id: str
    context_digest: str
    allowed_sources: tuple[str, ...]
    quorum: int
    strict: bool = True

    def __post_init__(self) -> None:
        _text(self.ground_id, "ground_id")
        _sha(self.context_digest, "context_digest")
        if isinstance(self.allowed_sources, str):
            raise EvidenceError("allowed_sources must be a sequence")
        sources = tuple(self.allowed_sources)
        if not sources or any(not isinstance(x, str) or not x.strip() for x in sources):
            raise EvidenceError("allowed_sources must contain non-empty source identifiers")
        if len(sources) != len(set(sources)):
            raise EvidenceError("allowed_sources must be unique")
        object.__setattr__(self, "allowed_sources", tuple(sorted(sources)))
        _positive(self.quorum, "quorum")
        if self.quorum > len(sources):
            raise EvidenceError("quorum cannot exceed allowed source count")
        if not isinstance(self.strict, bool):
            raise EvidenceError("strict must be Boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ground_id": self.ground_id,
            "context_digest": self.context_digest,
            "allowed_sources": list(self.allowed_sources),
            "quorum": self.quorum,
            "strict": self.strict,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TransitionEvidencePolicy":
        try:
            return cls(data["ground_id"], data["context_digest"],
                       tuple(data["allowed_sources"]), data["quorum"],
                       data.get("strict", True))
        except (KeyError, TypeError) as exc:
            raise EvidenceError(f"invalid evidence policy: {exc}") from exc

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class TransportFrameReceipt:
    """Adapter-supplied identity for one received transport frame.

    The digest binds the receipt to the exact ChannelMessage. This record is
    provenance metadata, not a cryptographic source signature or proof that
    the named transport actually delivered the frame.
    """
    transport_id: str
    frame_id: str
    source: str
    channel_id: str
    message_id: str
    sequence: int
    payload_digest: str
    received_at: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.transport_id, "transport_id"), (self.frame_id, "frame_id"),
            (self.source, "source"), (self.channel_id, "channel_id"),
            (self.message_id, "message_id"),
        ):
            _text(value, name)
        _positive(self.sequence, "transport sequence")
        _sha(self.payload_digest, "frame payload digest")
        if self.received_at is not None:
            _text(self.received_at, "received_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "transport_id": self.transport_id, "frame_id": self.frame_id,
            "source": self.source, "channel_id": self.channel_id,
            "message_id": self.message_id, "sequence": self.sequence,
            "payload_digest": self.payload_digest, "received_at": self.received_at,
        }

    @classmethod
    def capture(
        cls, message, *, transport_id: str, sequence: int,
        frame_id: str | None = None, received_at: str | None = None,
    ) -> "TransportFrameReceipt":
        """Create an integrity-bound receipt at a transport receive boundary.

        This convenience constructor does not authenticate the adapter or
        transport; deployment-specific adapters may supply their own receipt.
        """
        from .channels import ChannelMessage
        if not isinstance(message, ChannelMessage):
            raise EvidenceError("frame capture requires a ChannelMessage")
        payload_digest = _digest(message.to_dict())
        identity = {
            "transport_id": transport_id, "source": message.provenance.source,
            "channel_id": message.channel_id, "message_id": message.message_id,
            "sequence": sequence, "payload_digest": payload_digest,
        }
        return cls(
            transport_id, frame_id or _digest(identity), message.provenance.source,
            message.channel_id, message.message_id, sequence, payload_digest, received_at,
        )


@dataclass(frozen=True, slots=True)
class TransitionEvidence:
    """A typed transition claim bound to a retained message and transport frame."""

    evidence_id: str
    encounter_id: str
    message_id: str
    channel_id: str
    protocol_id: str
    transport_id: str
    frame_id: str
    transport_sequence: int
    source: str
    ground_id: str
    context_digest: str
    source_state: str
    action: str
    status: str
    outcomes: tuple[ObservedOutcome, ...]
    payload_digest: str
    correlation_id: str | None = None
    source_model_fingerprint: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.evidence_id, "evidence_id"), (self.encounter_id, "encounter_id"),
            (self.message_id, "message_id"), (self.channel_id, "channel_id"),
            (self.protocol_id, "protocol_id"), (self.transport_id, "transport_id"),
            (self.frame_id, "frame_id"), (self.source, "source"),
            (self.ground_id, "ground_id"), (self.source_state, "source_state"),
            (self.action, "action"),
        ):
            _text(value, name)
        _positive(self.transport_sequence, "transport_sequence")
        _sha(self.context_digest, "context_digest")
        _sha(self.payload_digest, "payload_digest")
        if self.correlation_id is not None:
            _text(self.correlation_id, "correlation_id")
        if self.source_model_fingerprint is not None:
            _sha(self.source_model_fingerprint, "source_model_fingerprint")
        if self.status not in ("known", "unknown", "ambiguous"):
            raise EvidenceError("status must be known, unknown, or ambiguous")
        outcomes = tuple(self.outcomes)
        if any(not isinstance(x, ObservedOutcome) for x in outcomes):
            raise EvidenceError("outcomes must contain ObservedOutcome records")
        if self.status == "known" and len(outcomes) != 1:
            raise EvidenceError("known evidence requires exactly one outcome")
        if self.status == "unknown" and outcomes:
            raise EvidenceError("unknown evidence cannot claim an outcome")
        if self.status == "ambiguous" and len(outcomes) < 2:
            raise EvidenceError("ambiguous evidence must preserve at least two alternatives")
        if len(outcomes) != len(set(outcomes)):
            raise EvidenceError("duplicate alternatives must be consolidated")
        object.__setattr__(self, "outcomes", outcomes)

    @property
    def event(self) -> tuple[str, str]:
        return self.source_state, self.action

    @property
    def signature(self) -> tuple[Any, ...]:
        return self.status, tuple((x.target, x.output) for x in self.outcomes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id, "encounter_id": self.encounter_id,
            "message_id": self.message_id, "channel_id": self.channel_id,
            "protocol_id": self.protocol_id, "transport_id": self.transport_id,
            "frame_id": self.frame_id, "transport_sequence": self.transport_sequence,
            "source": self.source, "ground_id": self.ground_id,
            "context_digest": self.context_digest, "source_state": self.source_state,
            "action": self.action, "status": self.status,
            "outcomes": [x.to_dict() for x in self.outcomes],
            "payload_digest": self.payload_digest, "correlation_id": self.correlation_id,
            "source_model_fingerprint": self.source_model_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TransitionEvidence":
        try:
            return cls(
                evidence_id=data["evidence_id"], encounter_id=data["encounter_id"],
                message_id=data["message_id"], channel_id=data["channel_id"],
                protocol_id=data["protocol_id"], transport_id=data["transport_id"],
                frame_id=data["frame_id"], transport_sequence=data["transport_sequence"],
                source=data["source"], ground_id=data["ground_id"],
                context_digest=data["context_digest"], source_state=data["source_state"],
                action=data["action"], status=data["status"],
                outcomes=tuple(ObservedOutcome(x["target"], tuple(x["output"]))
                               for x in data.get("outcomes", ())),
                payload_digest=data["payload_digest"], correlation_id=data.get("correlation_id"),
                source_model_fingerprint=data.get("source_model_fingerprint"),
            )
        except (KeyError, TypeError) as exc:
            raise EvidenceError(f"invalid transition evidence: {exc}") from exc

    @classmethod
    def from_channel_message(
        cls,
        exchange: ChannelExchangeLedger,
        message_id: str,
        frame: TransportFrameReceipt,
        encounters: EncounterLedger,
        *,
        ground_id: str,
        context_digest: str,
        evidence_id: str | None = None,
    ) -> "TransitionEvidence":
        """Normalize an inbound message only after the matching Encounter is retained."""
        if not isinstance(exchange, ChannelExchangeLedger):
            raise EvidenceError("exchange must be a ChannelExchangeLedger")
        if not isinstance(encounters, EncounterLedger):
            raise EvidenceError("encounters must be an EncounterLedger")
        _text(message_id, "message_id")
        message = next((x for x in exchange.messages if x.message_id == message_id), None)
        if message is None:
            raise EvidenceError(f"message {message_id!r} is absent from channel ledger")
        if not isinstance(frame, TransportFrameReceipt):
            raise EvidenceError("frame must be a TransportFrameReceipt")
        expected_payload_digest = _digest(message.to_dict())
        if (
            frame.message_id != message.message_id
            or frame.channel_id != message.channel_id
            or frame.source != message.provenance.source
            or frame.payload_digest != expected_payload_digest
        ):
            raise EvidenceError("transport frame receipt does not bind this exact message")
        contract = exchange.contract_for(message.channel_id)
        if message.direction == "request":
            raise EvidenceError("outbound request intents are not observations")
        if message.direction == "observation" and not contract.can_observe:
            raise EvidenceError("channel has no declared observation capability")
        if message.direction == "reply" and not contract.can_address:
            raise EvidenceError("channel has no declared request/reply capability")

        encounter_id = f"channel-message:{message.message_id}"
        try:
            encounter = encounters.get(encounter_id)
        except ValueError as exc:
            raise EvidenceError("inbound message has not been retained as an Encounter") from exc
        stored = encounter.to_dict()
        payload = _plain(message.payload)
        if stored["payload"] != payload or encounter.provenance != message.provenance:
            raise EvidenceError("Encounter payload/provenance differs from channel message")
        expected_context = {
            "channel_id": message.channel_id, "protocol_id": message.protocol_id,
            "direction": message.direction, "correlation_id": message.correlation_id,
            "message_id": message.message_id,
        }
        if stored["context"] != expected_context:
            raise EvidenceError("Encounter context does not bind channel-message identity")

        status = payload.get("status")
        state = payload.get("source_state", payload.get("source"))
        action = payload.get("action")
        if status not in ("known", "unknown", "ambiguous"):
            raise EvidenceError("payload must declare known, unknown, or ambiguous status")
        if not isinstance(state, str) or not state:
            raise EvidenceError("payload lacks source_state/source")
        if not isinstance(action, str) or not action:
            raise EvidenceError("payload lacks action")

        if status == "known":
            if "target" not in payload or not isinstance(payload.get("output"), list):
                raise EvidenceError("known payload requires target and output array")
            outcomes = (ObservedOutcome(payload["target"], tuple(payload["output"])),)
        elif status == "unknown":
            if any(key in payload for key in ("target", "output", "outcomes")):
                raise EvidenceError("unknown payload cannot contain a proposed result")
            outcomes = ()
        else:
            raw = payload.get("outcomes")
            if not isinstance(raw, list):
                raise EvidenceError("ambiguous payload requires an outcomes array")
            try:
                outcomes = tuple(ObservedOutcome(x["target"], tuple(x["output"])) for x in raw)
            except (KeyError, TypeError) as exc:
                raise EvidenceError(f"ambiguous outcome has invalid shape: {exc}") from exc

        return cls(
            evidence_id=evidence_id or f"{message.message_id}:{frame.sequence}",
            encounter_id=encounter_id, message_id=message.message_id,
            channel_id=message.channel_id, protocol_id=message.protocol_id,
            transport_id=frame.transport_id, frame_id=frame.frame_id,
            transport_sequence=frame.sequence, source=message.provenance.source,
            ground_id=ground_id, context_digest=context_digest,
            source_state=state, action=action, status=status, outcomes=outcomes,
            payload_digest=_digest(message.to_dict()), correlation_id=message.correlation_id,
            source_model_fingerprint=payload.get("ground_fingerprint"),
        )


@dataclass(frozen=True, slots=True)
class TransitionEvidenceDecision:
    source_state: str
    action: str
    status: str
    quorum: int
    strict: bool
    observed_sources: tuple[str, ...]
    agreeing_sources: tuple[str, ...]
    dissenting_sources: tuple[str, ...]
    indeterminate_sources: tuple[str, ...]
    conflicting_sources: tuple[str, ...]
    missing_sources: tuple[str, ...]
    outcome: ObservedOutcome | None
    agreeing_evidence_ids: tuple[str, ...]
    observed_evidence_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_state": self.source_state, "action": self.action, "status": self.status,
            "quorum": self.quorum, "strict": self.strict,
            "observed_sources": list(self.observed_sources),
            "agreeing_sources": list(self.agreeing_sources),
            "dissenting_sources": list(self.dissenting_sources),
            "indeterminate_sources": list(self.indeterminate_sources),
            "conflicting_sources": list(self.conflicting_sources),
            "missing_sources": list(self.missing_sources),
            "outcome": None if self.outcome is None else self.outcome.to_dict(),
            "agreeing_evidence_ids": list(self.agreeing_evidence_ids),
            "observed_evidence_ids": list(self.observed_evidence_ids),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class TransitionEvidenceFinalization:
    source_state: str
    action: str
    status: str
    decision_digest: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.source_state, "finalization source_state")
        _text(self.action, "finalization action")
        if self.status not in ("AUTHORIZED", "CONFLICT", "REFUSED"):
            raise EvidenceError("invalid finalization status")
        _sha(self.decision_digest, "decision_digest")
        ids = tuple(self.evidence_ids)
        if not ids or any(not isinstance(x, str) or not x for x in ids):
            raise EvidenceError("finalization requires a non-empty evidence ID sequence")
        if len(ids) != len(set(ids)):
            raise EvidenceError("finalization evidence IDs must be unique")
        object.__setattr__(self, "evidence_ids", ids)

    @property
    def event(self) -> tuple[str, str]:
        return self.source_state, self.action

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_state": self.source_state, "action": self.action,
            "status": self.status, "decision_digest": self.decision_digest,
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TransitionEvidenceFinalization":
        try:
            return cls(data["source_state"], data["action"], data["status"],
                       data["decision_digest"], tuple(data["evidence_ids"]))
        except (KeyError, TypeError) as exc:
            raise EvidenceError(f"invalid finalization: {exc}") from exc


@dataclass(frozen=True, slots=True)
class TransitionEvidenceLedger:
    """Append-only observed claims and policy finalizations for one Ground context."""

    policy: TransitionEvidencePolicy
    evidence: tuple[TransitionEvidence, ...] = ()
    finalizations: tuple[TransitionEvidenceFinalization, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.policy, TransitionEvidencePolicy):
            raise EvidenceError("ledger requires a TransitionEvidencePolicy")
        records, finalizations = tuple(self.evidence), tuple(self.finalizations)
        if any(not isinstance(x, TransitionEvidence) for x in records):
            raise EvidenceError("evidence must contain TransitionEvidence records")
        if any(not isinstance(x, TransitionEvidenceFinalization) for x in finalizations):
            raise EvidenceError("finalizations must contain finalization records")
        evidence_ids = [x.evidence_id for x in records]
        message_ids = [x.message_id for x in records]
        frame_ids = [(x.transport_id, x.source, x.channel_id, x.transport_sequence) for x in records]
        receipt_ids = [x.frame_id for x in records]
        event_ids = [x.event for x in finalizations]
        for values, label in ((evidence_ids, "evidence IDs"), (message_ids, "message IDs"),
                              (frame_ids, "transport/source/channel frame IDs"),
                              (receipt_ids, "transport frame receipt IDs"),
                              (event_ids, "finalized events")):
            if len(values) != len(set(values)):
                raise EvidenceError(f"{label} must be unique")
        for item in records:
            if item.ground_id != self.policy.ground_id or item.context_digest != self.policy.context_digest:
                raise EvidenceError("evidence Ground/context differs from policy")
            if item.source not in self.policy.allowed_sources:
                raise EvidenceError(f"source {item.source!r} is not allowed by policy")
        for finalization in finalizations:
            event_records = tuple(x for x in records if x.event == finalization.event)
            expected_ids = tuple(x.evidence_id for x in event_records)
            if not event_records or finalization.evidence_ids != expected_ids:
                raise EvidenceError("finalization does not bind the exact ordered event evidence")
            raw = self._raw_decision(finalization.source_state, finalization.action, records, self.policy)
            if raw.digest != finalization.decision_digest:
                raise EvidenceError("finalization digest differs from retained evidence")
            expected_status = ("AUTHORIZED" if raw.status == "QUORUM" else
                               "CONFLICT" if raw.status == "CONFLICT" else "REFUSED")
            if finalization.status != expected_status:
                raise EvidenceError("finalization status does not follow policy decision")
        object.__setattr__(self, "evidence", records)
        object.__setattr__(self, "finalizations", finalizations)

    @staticmethod
    def _raw_decision(
        source_state: str,
        action: str,
        records: tuple[TransitionEvidence, ...],
        policy: TransitionEvidencePolicy,
    ) -> TransitionEvidenceDecision:
        event_records = tuple(x for x in records if x.event == (source_state, action))
        if not event_records:
            raise EvidenceError("no evidence has been observed for this state/action event")

        by_source: dict[str, dict[tuple[Any, ...], list[TransitionEvidence]]] = {}
        for item in event_records:
            by_source.setdefault(item.source, {}).setdefault(item.signature, []).append(item)
        conflicting = tuple(sorted(s for s, signatures in by_source.items() if len(signatures) > 1))

        groups: dict[tuple[str, tuple[int, ...]], list[str]] = {}
        indeterminate = []
        for source, signatures in by_source.items():
            if len(signatures) != 1:
                continue
            status, outcomes = next(iter(signatures))
            if status == "known":
                groups.setdefault(outcomes[0], []).append(source)
            else:
                indeterminate.append(source)

        observed = tuple(sorted(by_source))
        missing = tuple(sorted(set(policy.allowed_sources) - set(observed)))
        indeterminate_sources = tuple(sorted(indeterminate))
        ranked = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0][0], item[0][1]))
        winner = None
        agreeing: tuple[str, ...] = ()
        tied = False
        if ranked:
            high = len(ranked[0][1])
            tied = sum(1 for _, sources in ranked if len(sources) == high) > 1
            if not tied:
                winner = ranked[0][0]
                agreeing = tuple(sorted(ranked[0][1]))
        dissenting = tuple(sorted(
            source for sources in groups.values() for source in sources
            if source not in agreeing
        ))

        if conflicting or tied or (policy.strict and dissenting):
            status = "CONFLICT"
        elif winner is not None and len(agreeing) >= policy.quorum:
            status = "PENDING" if policy.strict and (missing or indeterminate_sources) else "QUORUM"
        else:
            status = "PENDING"

        outcome = None if winner is None else ObservedOutcome(winner[0], winner[1])
        agreeing_ids = []
        if outcome is not None:
            for source in agreeing:
                representative = next(
                    x for x in event_records
                    if x.source == source and x.status == "known" and x.outcomes == (outcome,)
                )
                agreeing_ids.append(representative.evidence_id)
        return TransitionEvidenceDecision(
            source_state, action, status, policy.quorum, policy.strict,
            observed, agreeing, dissenting, indeterminate_sources, conflicting,
            missing, outcome, tuple(agreeing_ids),
            tuple(x.evidence_id for x in event_records),
        )

    def ingest(self, evidence: TransitionEvidence) -> "TransitionEvidenceLedger":
        if not isinstance(evidence, TransitionEvidence):
            raise EvidenceError("ingest expects TransitionEvidence")
        if (evidence.ground_id, evidence.context_digest) != (
            self.policy.ground_id, self.policy.context_digest
        ):
            raise EvidenceError("evidence Ground/context does not match policy")
        if evidence.source not in self.policy.allowed_sources:
            raise EvidenceError(f"source {evidence.source!r} is not authorized")
        if any(x.event == evidence.event for x in self.finalizations):
            raise EvidenceError("event is finalized; use a new Ground/context revision")
        if any(x.evidence_id == evidence.evidence_id for x in self.evidence):
            raise EvidenceError("evidence ID already recorded")
        if any(x.message_id == evidence.message_id for x in self.evidence):
            raise EvidenceError("message ID already recorded")
        if any((x.transport_id, x.source, x.channel_id, x.transport_sequence) ==
               (evidence.transport_id, evidence.source, evidence.channel_id, evidence.transport_sequence)
               for x in self.evidence):
            raise EvidenceError("transport/source/channel frame already recorded")
        if any(x.frame_id == evidence.frame_id for x in self.evidence):
            raise EvidenceError("transport frame receipt ID already recorded")
        return TransitionEvidenceLedger(
            self.policy, self.evidence + (evidence,), self.finalizations
        )

    def ingest_channel_message(
        self, exchange: ChannelExchangeLedger, message_id: str,
        frame: TransportFrameReceipt, encounters: EncounterLedger, *,
        evidence_id: str | None = None,
    ) -> "TransitionEvidenceLedger":
        item = TransitionEvidence.from_channel_message(
            exchange, message_id, frame, encounters,
            ground_id=self.policy.ground_id, context_digest=self.policy.context_digest,
            evidence_id=evidence_id,
        )
        return self.ingest(item)

    def status(self, source_state: str, action: str) -> TransitionEvidenceDecision:
        return self._raw_decision(source_state, action, self.evidence, self.policy)

    def finalize(self, source_state: str, action: str) -> "TransitionEvidenceLedger":
        event = (_text(source_state, "source_state"), _text(action, "action"))
        if any(x.event == event for x in self.finalizations):
            return self
        decision = self.status(*event)
        status = ("AUTHORIZED" if decision.status == "QUORUM" else
                  "CONFLICT" if decision.status == "CONFLICT" else "REFUSED")
        finalization = TransitionEvidenceFinalization(
            event[0], event[1], status, decision.digest, decision.observed_evidence_ids
        )
        return TransitionEvidenceLedger(
            self.policy, self.evidence, self.finalizations + (finalization,)
        )

    def decision(self, source_state: str, action: str) -> TransitionEvidenceDecision:
        raw = self.status(source_state, action)
        final = next((x for x in self.finalizations if x.event == (source_state, action)), None)
        return raw if final is None else replace(raw, status=final.status)

    def transition_observation(self, source_state: str, action: str) -> TransitionObservation:
        decision = self.decision(source_state, action)
        if decision.status != "AUTHORIZED" or decision.outcome is None:
            raise EvidenceError("transition is not authorized by finalized evidence")
        return TransitionObservation(
            source=source_state, action=action,
            outcomes=(TransitionOutcome(decision.outcome.target, decision.outcome.output),),
            support_count=len(decision.agreeing_sources),
            evidence=decision.agreeing_evidence_ids,
        )

    def build_ground(
        self, *, states: Sequence[str], actions: Sequence[str], initial_state: str,
        channels: Sequence[str], metadata: Mapping[str, Any] | None = None,
    ) -> GroundTransitionSystem:
        """Build a possibly partial Ground from AUTHORIZED finalizations only."""
        observations = tuple(
            self.transition_observation(x.source_state, x.action)
            for x in sorted(self.finalizations, key=lambda row: row.event)
            if x.status == "AUTHORIZED"
        )
        merged = dict(metadata or {})
        reserved = {
            "vgi_evidence_ground_id": self.policy.ground_id,
            "vgi_evidence_context_digest": self.policy.context_digest,
            "vgi_evidence_policy_digest": self.policy.fingerprint,
            "vgi_evidence_ledger_digest": self.fingerprint,
        }
        for key, value in reserved.items():
            if key in merged and merged[key] != value:
                raise EvidenceError(f"metadata cannot override {key!r}")
            merged[key] = value
        try:
            return GroundTransitionSystem(
                states=tuple(states), actions=tuple(actions), initial_state=initial_state,
                channels=tuple(channels), observations=observations, metadata=merged,
            )
        except TransitionSystemError as exc:
            raise EvidenceError(f"authorized evidence cannot form requested Ground: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-TransitionEvidenceLedger-1",
            "policy": self.policy.to_dict(),
            "evidence": [x.to_dict() for x in self.evidence],
            "finalizations": [x.to_dict() for x in self.finalizations],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TransitionEvidenceLedger":
        if not isinstance(data, Mapping) or data.get("format") != "VGI-TransitionEvidenceLedger-1":
            raise EvidenceError("expected VGI-TransitionEvidenceLedger-1")
        try:
            return cls(
                TransitionEvidencePolicy.from_dict(data["policy"]),
                tuple(TransitionEvidence.from_dict(x) for x in data.get("evidence", ())),
                tuple(TransitionEvidenceFinalization.from_dict(x)
                      for x in data.get("finalizations", ())),
            )
        except (KeyError, TypeError) as exc:
            raise EvidenceError(f"invalid evidence ledger: {exc}") from exc

    @classmethod
    def from_json(cls, source: str) -> "TransitionEvidenceLedger":
        try:
            return cls.from_dict(json.loads(source))
        except json.JSONDecodeError as exc:
            raise EvidenceError(f"invalid evidence-ledger JSON: {exc}") from exc


@dataclass(frozen=True, slots=True)
class GroundReconstructionCertificate:
    """Finite witness certificate for Ground-to-compiled-VGI replay agreement."""

    ground_fingerprint: str
    context_digest: str
    witness_digest: str
    action_sequences: tuple[tuple[str, ...], ...]
    witness_count: int
    max_horizon: int
    compiler_id: str = "vgi.transition-compiler"
    compiler_version: int = 1
    schema: str = "vgi.ground-reconstruction-certificate.v1"
    scope: str = "finite_action_sequence_replay"

    def __post_init__(self) -> None:
        _sha(self.ground_fingerprint, "ground_fingerprint")
        _sha(self.context_digest, "context_digest")
        _sha(self.witness_digest, "witness_digest")
        _positive(self.witness_count, "witness_count")
        if isinstance(self.action_sequences, (str, bytes)):
            raise EvidenceError("action_sequences must be a sequence of action sequences")
        raw_sequences = tuple(self.action_sequences)
        if any(isinstance(x, (str, bytes)) for x in raw_sequences):
            raise EvidenceError("each witness must be an action sequence, not one string")
        sequences = tuple(tuple(x) for x in raw_sequences)
        if not sequences or len(sequences) != self.witness_count:
            raise EvidenceError("witness_count must equal retained non-empty sequence count")
        if len(sequences) != len(set(sequences)):
            raise EvidenceError("witness sequences must be unique")
        if any(any(not isinstance(a, str) or not a for a in seq) for seq in sequences):
            raise EvidenceError("witness sequence contains invalid action")
        if isinstance(self.max_horizon, bool) or not isinstance(self.max_horizon, int) or self.max_horizon < 0:
            raise EvidenceError("max_horizon must be a non-negative integer")
        if max((len(x) for x in sequences), default=0) != self.max_horizon:
            raise EvidenceError("max_horizon does not match witness sequences")
        if self.max_horizon > 128 or self.witness_count > 4096:
            raise EvidenceError("witness corpus exceeds configured bounds")
        _text(self.compiler_id, "compiler_id")
        _positive(self.compiler_version, "compiler_version")
        if self.schema != "vgi.ground-reconstruction-certificate.v1":
            raise EvidenceError("unsupported certificate schema")
        if self.scope != "finite_action_sequence_replay":
            raise EvidenceError("unsupported reconstruction scope")
        object.__setattr__(self, "action_sequences", sequences)

    @property
    def reconstructable_for_witnesses(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "ground_fingerprint": self.ground_fingerprint,
            "context_digest": self.context_digest, "witness_digest": self.witness_digest,
            "action_sequences": [list(x) for x in self.action_sequences],
            "witness_count": self.witness_count, "max_horizon": self.max_horizon,
            "compiler_id": self.compiler_id, "compiler_version": self.compiler_version,
            "scope": self.scope,
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GroundReconstructionCertificate":
        try:
            return cls(
                ground_fingerprint=data["ground_fingerprint"],
                context_digest=data["context_digest"], witness_digest=data["witness_digest"],
                action_sequences=tuple(tuple(x) for x in data["action_sequences"]),
                witness_count=data["witness_count"], max_horizon=data["max_horizon"],
                compiler_id=data["compiler_id"], compiler_version=data["compiler_version"],
                schema=data["schema"], scope=data["scope"],
            )
        except (KeyError, TypeError) as exc:
            raise EvidenceError(f"invalid reconstruction certificate: {exc}") from exc


class GroundReconstructionVerifier:
    """Certify only the caller-declared finite replay corpus."""

    compiler_id = "vgi.transition-compiler"
    compiler_version = 1
    max_witnesses = 4096
    max_horizon = 128

    @classmethod
    def _normalize(cls, sequences: Sequence[Sequence[str]]) -> tuple[tuple[str, ...], ...]:
        if isinstance(sequences, (str, bytes)):
            raise EvidenceError("action_sequences must be a sequence of sequences")
        try:
            if any(isinstance(x, (str, bytes)) for x in sequences):
                raise EvidenceError("each witness must be an action sequence, not one string")
            normalized = tuple(tuple(x) for x in sequences)
        except TypeError as exc:
            raise EvidenceError("action_sequences must contain finite sequences") from exc
        if not normalized or len(normalized) > cls.max_witnesses:
            raise EvidenceError("witness corpus must be non-empty and within configured bounds")
        if len(normalized) != len(set(normalized)):
            raise EvidenceError("witness sequences must be unique")
        if any(any(not isinstance(a, str) or not a for a in seq) for seq in normalized):
            raise EvidenceError("witness sequence contains invalid action")
        if max((len(x) for x in normalized), default=0) > cls.max_horizon:
            raise EvidenceError("witness sequence exceeds maximum horizon")
        return normalized

    def certify(
        self, system: GroundTransitionSystem, action_sequences: Sequence[Sequence[str]],
        *, context_digest: str,
    ) -> GroundReconstructionCertificate:
        if not isinstance(system, GroundTransitionSystem):
            raise EvidenceError("system must be a GroundTransitionSystem")
        _sha(context_digest, "context_digest")
        if not system.complete:
            raise EvidenceError("only complete, single-valued Grounds can be compiled")
        sequences = self._normalize(action_sequences)
        try:
            report = differential_verify(system, sequences)
        except (TransitionSystemError, TypeError, ValueError) as exc:
            raise EvidenceError(f"compiled replay could not be verified: {exc}") from exc
        if report.get("status") != "PASS" or report.get("errors"):
            raise EvidenceError("compiled reconstruction disagrees with direct Ground semantics")

        traces = []
        for actions in sequences:
            run = system.run(actions)
            traces.append({
                "actions": list(actions), "state_trace": list(run.state_trace),
                "outputs": [list(x) for x in run.outputs], "final_state": run.final_state,
            })
        witness_digest = _digest({
            "ground_fingerprint": system.fingerprint, "context_digest": context_digest,
            "compiler_id": self.compiler_id, "compiler_version": self.compiler_version,
            "traces": traces,
        })
        return GroundReconstructionCertificate(
            ground_fingerprint=system.fingerprint, context_digest=context_digest,
            witness_digest=witness_digest, action_sequences=sequences,
            witness_count=len(sequences), max_horizon=max(len(x) for x in sequences),
            compiler_id=self.compiler_id, compiler_version=self.compiler_version,
        )

    def verify(
        self, system: GroundTransitionSystem, certificate: GroundReconstructionCertificate,
        *, context_digest: str,
    ) -> bool:
        if not isinstance(system, GroundTransitionSystem):
            raise EvidenceError("system must be a GroundTransitionSystem")
        if not isinstance(certificate, GroundReconstructionCertificate):
            raise EvidenceError("certificate must be a GroundReconstructionCertificate")
        if system.fingerprint != certificate.ground_fingerprint:
            raise EvidenceError("certificate belongs to a different Ground fingerprint")
        if context_digest != certificate.context_digest:
            raise EvidenceError("certificate belongs to a different context")
        if (certificate.compiler_id, certificate.compiler_version) != (
            self.compiler_id, self.compiler_version
        ):
            raise EvidenceError("certificate compiler identity/version is unsupported")
        actual = self.certify(system, certificate.action_sequences, context_digest=context_digest)
        if actual.to_dict() != certificate.to_dict():
            raise EvidenceError("replayed witness digest differs from certificate")
        return True


__all__ = [
    "EvidenceError", "ObservedOutcome", "TransitionEvidencePolicy", "TransitionEvidence",
    "TransitionEvidenceDecision", "TransitionEvidenceFinalization", "TransitionEvidenceLedger",
    "TransportFrameReceipt", "GroundReconstructionCertificate", "GroundReconstructionVerifier",
]
