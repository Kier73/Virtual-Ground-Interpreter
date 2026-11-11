"""Explicit observation/request/reply contracts for compatible interaction channels.

A shared protocol identifier describes the channel framing language. It does not
imply that a channel is writable: observation, request, and reply schemas are
declared independently. The reference predictive-Ground adapter demonstrates a
model-internal request/reply path without claiming physical communication.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from .encounters import Encounter, EncounterLedger, EncounterProvenance
from .transitions import GroundTransitionSystem, TransitionSystemError


class ChannelError(ValueError):
    """Invalid channel contract, message, exchange, or adapter interaction."""


def _freeze_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ChannelError("channel payload object keys must be strings")
        return MappingProxyType({key: _freeze_payload(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_payload(item) for item in value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ChannelError(
        "channel payloads must be finite JSON-compatible values; "
        f"received {type(value).__name__}"
    )


def _thaw_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_payload(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ChannelError(f"{label} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ChannelContract:
    """Declared directions and schema identifiers for one channel.

    protocol_id is the shared framing/encoding language. It is not itself a
    semantic schema. observation_schema enables incoming observations;
    request_schema and response_schema together enable addressed exchanges.
    """

    channel_id: str
    protocol_id: str
    observation_schema: str | None = None
    request_schema: str | None = None
    response_schema: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.channel_id, "channel_id")
        _require_text(self.protocol_id, "protocol_id")
        for value, label in (
            (self.observation_schema, "observation_schema"),
            (self.request_schema, "request_schema"),
            (self.response_schema, "response_schema"),
        ):
            if value is not None:
                _require_text(value, label)
        if (self.request_schema is None) != (self.response_schema is None):
            raise ChannelError(
                "addressable request/reply channels must declare both request_schema "
                "and response_schema"
            )

    @property
    def can_observe(self) -> bool:
        return self.observation_schema is not None

    @property
    def can_address(self) -> bool:
        return self.request_schema is not None and self.response_schema is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "protocol_id": self.protocol_id,
            "observation_schema": self.observation_schema,
            "request_schema": self.request_schema,
            "response_schema": self.response_schema,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ChannelContract":
        try:
            return cls(**dict(data))
        except (TypeError, KeyError) as exc:
            raise ChannelError(f"invalid channel contract: {exc}") from exc

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            _canonical_json(self.to_dict()).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ChannelMessage:
    """One observation, proposed request, or received reply."""

    message_id: str
    channel_id: str
    protocol_id: str
    direction: str
    payload: Mapping[str, Any]
    provenance: EncounterProvenance
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.message_id, "message_id"),
            (self.channel_id, "channel_id"),
            (self.protocol_id, "protocol_id"),
        ):
            _require_text(value, label)
        if self.direction not in ("observation", "request", "reply"):
            raise ChannelError("direction must be observation, request, or reply")
        if not isinstance(self.payload, Mapping):
            raise ChannelError("channel payload must be a JSON object")
        if not isinstance(self.provenance, EncounterProvenance):
            raise ChannelError("provenance must be an EncounterProvenance")
        if self.direction == "reply":
            _require_text(self.correlation_id, "reply correlation_id")
        elif self.correlation_id is not None:
            raise ChannelError(
                "only replies carry correlation_id; requests use their message_id"
            )
        frozen = _freeze_payload(self.payload)
        if not isinstance(frozen, Mapping):
            raise ChannelError("channel payload must be a JSON object")
        object.__setattr__(self, "payload", frozen)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "channel_id": self.channel_id,
            "protocol_id": self.protocol_id,
            "direction": self.direction,
            "payload": _thaw_payload(self.payload),
            "provenance": self.provenance.to_dict(),
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ChannelMessage":
        try:
            return cls(
                message_id=data["message_id"],
                channel_id=data["channel_id"],
                protocol_id=data["protocol_id"],
                direction=data["direction"],
                payload=data["payload"],
                provenance=EncounterProvenance(**data["provenance"]),
                correlation_id=data.get("correlation_id"),
            )
        except (KeyError, TypeError) as exc:
            raise ChannelError(f"invalid channel message: {exc}") from exc


@runtime_checkable
class ChannelAdapter(Protocol):
    """A source that accepts a request and returns a correlated reply."""

    @property
    def contract(self) -> ChannelContract:
        ...

    def exchange(self, request: ChannelMessage) -> ChannelMessage:
        ...


@dataclass(frozen=True, slots=True)
class ChannelExchangeLedger:
    """Append-only contracts and messages with validated request/reply links."""

    contracts: tuple[ChannelContract, ...] = ()
    messages: tuple[ChannelMessage, ...] = ()

    def __post_init__(self) -> None:
        contracts = tuple(self.contracts)
        messages = tuple(self.messages)
        if any(not isinstance(item, ChannelContract) for item in contracts):
            raise ChannelError("contracts must contain ChannelContract instances")
        if any(not isinstance(item, ChannelMessage) for item in messages):
            raise ChannelError("messages must contain ChannelMessage instances")
        by_channel: dict[str, ChannelContract] = {}
        for contract in contracts:
            if contract.channel_id in by_channel:
                raise ChannelError(f"duplicate channel contract {contract.channel_id!r}")
            by_channel[contract.channel_id] = contract

        message_ids: set[str] = set()
        requests: dict[str, ChannelMessage] = {}
        for message in messages:
            if message.message_id in message_ids:
                raise ChannelError(f"duplicate message identifier {message.message_id!r}")
            message_ids.add(message.message_id)
            contract = by_channel.get(message.channel_id)
            if contract is None:
                raise ChannelError(
                    f"message references unregistered channel {message.channel_id!r}"
                )
            self._validate_message(contract, message, requests)

        object.__setattr__(self, "contracts", contracts)
        object.__setattr__(self, "messages", messages)

    @staticmethod
    def _validate_message(
        contract: ChannelContract,
        message: ChannelMessage,
        prior_requests: dict[str, ChannelMessage],
    ) -> None:
        if message.protocol_id != contract.protocol_id:
            raise ChannelError("message protocol_id does not match its channel contract")
        if message.direction == "observation":
            if not contract.can_observe:
                raise ChannelError("channel contract does not accept observations")
            return
        if message.direction == "request":
            if not contract.can_address:
                raise ChannelError("channel contract is not addressable")
            prior_requests[message.message_id] = message
            return
        if message.direction == "reply":
            if not contract.can_address:
                raise ChannelError("channel contract cannot produce addressed replies")
            request = prior_requests.get(message.correlation_id or "")
            if request is None:
                raise ChannelError("reply must correlate to an earlier recorded request")
            if (
                request.channel_id != message.channel_id
                or request.protocol_id != message.protocol_id
            ):
                raise ChannelError("reply channel/protocol differs from its request")

    def contract_for(self, channel_id: str) -> ChannelContract:
        for contract in self.contracts:
            if contract.channel_id == channel_id:
                return contract
        raise ChannelError(f"unregistered channel {channel_id!r}")

    def register(self, contract: ChannelContract) -> "ChannelExchangeLedger":
        if not isinstance(contract, ChannelContract):
            raise ChannelError("register expects a ChannelContract")
        existing = next(
            (item for item in self.contracts if item.channel_id == contract.channel_id),
            None,
        )
        if existing is not None:
            if existing != contract:
                raise ChannelError(
                    f"channel {contract.channel_id!r} is already registered differently"
                )
            return self
        return ChannelExchangeLedger(self.contracts + (contract,), self.messages)

    def append(self, message: ChannelMessage) -> "ChannelExchangeLedger":
        if not isinstance(message, ChannelMessage):
            raise ChannelError("append expects a ChannelMessage")
        if any(item.message_id == message.message_id for item in self.messages):
            raise ChannelError(f"message {message.message_id!r} already exists")
        return ChannelExchangeLedger(self.contracts, self.messages + (message,))

    def record_observation(
        self, contract: ChannelContract, message: ChannelMessage
    ) -> "ChannelExchangeLedger":
        if message.direction != "observation":
            raise ChannelError("record_observation requires an observation message")
        return self.register(contract).append(message)

    def propose_request(
        self, contract: ChannelContract, message: ChannelMessage
    ) -> "ChannelExchangeLedger":
        """Record a local request intent; this method does not transmit it."""
        if message.direction != "request":
            raise ChannelError("propose_request requires a request message")
        return self.register(contract).append(message)

    def record_reply(self, message: ChannelMessage) -> "ChannelExchangeLedger":
        if message.direction != "reply":
            raise ChannelError("record_reply requires a reply message")
        return self.append(message)

    def exchange(
        self, adapter: ChannelAdapter, request: ChannelMessage
    ) -> "ChannelExchangeLedger":
        """Invoke an adapter and record the request and its returned reply.

        For explicit retention of a request intent when a transport fails, call
        propose_request first and invoke the adapter separately.
        """
        if not isinstance(request, ChannelMessage) or request.direction != "request":
            raise ChannelError("exchange requires a request ChannelMessage")
        if not isinstance(adapter, ChannelAdapter):
            raise ChannelError("adapter must expose a ChannelContract and exchange()")
        contract = adapter.contract
        prepared = self.propose_request(contract, request)
        reply = adapter.exchange(request)
        return prepared.record_reply(reply)

    def to_encounter(self, message_id: str) -> Encounter:
        message = next(
            (item for item in self.messages if item.message_id == message_id),
            None,
        )
        if message is None:
            raise ChannelError(f"unknown message {message_id!r}")
        if message.direction == "request":
            raise ChannelError(
                "outbound request intents are not observations and cannot become encounters"
            )
        return Encounter(
            encounter_id=f"channel-message:{message.message_id}",
            payload=_thaw_payload(message.payload),
            provenance=message.provenance,
            context={
                "channel_id": message.channel_id,
                "protocol_id": message.protocol_id,
                "direction": message.direction,
                "correlation_id": message.correlation_id,
                "message_id": message.message_id,
            },
        )

    def to_encounter_ledger(self) -> EncounterLedger:
        ledger = EncounterLedger()
        for message in self.messages:
            if message.direction in ("observation", "reply"):
                ledger = ledger.append(self.to_encounter(message.message_id))
        return ledger

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-ChannelExchangeLedger-1",
            "contracts": [item.to_dict() for item in self.contracts],
            "messages": [item.to_dict() for item in self.messages],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False
        )

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            _canonical_json(self.to_dict()).encode("utf-8")
        ).hexdigest()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ChannelExchangeLedger":
        if (
            not isinstance(data, Mapping)
            or data.get("format") != "VGI-ChannelExchangeLedger-1"
        ):
            raise ChannelError("expected VGI-ChannelExchangeLedger-1")
        return cls(
            contracts=tuple(
                ChannelContract.from_dict(item) for item in data.get("contracts", ())
            ),
            messages=tuple(
                ChannelMessage.from_dict(item) for item in data.get("messages", ())
            ),
        )

    @classmethod
    def from_json(cls, source: str) -> "ChannelExchangeLedger":
        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise ChannelError(f"invalid channel ledger JSON: {exc}") from exc
        return cls.from_dict(data)


class PredictiveGroundAdapter:
    """Address a finite predictive Ground using its declared state/action language.

    This is a model-internal query adapter. It exposes known, unknown, and
    ambiguous records faithfully; it is not a physical sensor or host channel.
    """

    def __init__(self, system: GroundTransitionSystem):
        if not isinstance(system, GroundTransitionSystem):
            raise ChannelError("system must be a GroundTransitionSystem")
        self.system = system
        self._contract = ChannelContract(
            channel_id="vgi.predictive-ground",
            protocol_id="vgi.transition-query/1",
            request_schema="vgi.transition-query.request/1",
            response_schema="vgi.transition-query.reply/1",
        )

    @property
    def contract(self) -> ChannelContract:
        return self._contract

    def exchange(self, request: ChannelMessage) -> ChannelMessage:
        if not isinstance(request, ChannelMessage) or request.direction != "request":
            raise ChannelError("PredictiveGroundAdapter accepts request messages only")
        if (
            request.channel_id != self.contract.channel_id
            or request.protocol_id != self.contract.protocol_id
        ):
            raise ChannelError("request does not address the predictive Ground channel")
        if set(request.payload) != {"source", "action"}:
            raise ChannelError("transition query payload requires exactly source and action")
        source, action = request.payload["source"], request.payload["action"]
        if not isinstance(source, str) or not isinstance(action, str):
            raise ChannelError("transition query source and action must be strings")
        try:
            status = self.system.status(source, action)
        except TransitionSystemError as exc:
            raise ChannelError(f"query is outside the declared Ground: {exc}") from exc

        if status == "known":
            step = self.system.step(source, action)
            payload = {
                "status": "known",
                "source": source,
                "action": action,
                "target": step.target,
                "output": list(step.output),
                "support_count": step.support_count,
                "evidence": list(step.evidence),
                "ground_fingerprint": self.system.fingerprint,
            }
        elif status == "unknown":
            payload = {
                "status": "unknown",
                "source": source,
                "action": action,
                "ground_fingerprint": self.system.fingerprint,
            }
        else:
            observation = next(
                item for item in self.system.observations
                if item.source == source and item.action == action
            )
            payload = {
                "status": "ambiguous",
                "source": source,
                "action": action,
                "outcomes": [
                    {"target": item.target, "output": list(item.output)}
                    for item in observation.outcomes
                ],
                "support_count": observation.support_count,
                "evidence": list(observation.evidence),
                "ground_fingerprint": self.system.fingerprint,
            }

        return ChannelMessage(
            message_id=f"{request.message_id}:reply",
            channel_id=self.contract.channel_id,
            protocol_id=self.contract.protocol_id,
            direction="reply",
            payload=payload,
            provenance=EncounterProvenance(
                source=self.contract.channel_id,
                source_ref=f"vgi-ground://{self.system.fingerprint}/{source}/{action}",
                collector="PredictiveGroundAdapter",
            ),
            correlation_id=request.message_id,
        )
