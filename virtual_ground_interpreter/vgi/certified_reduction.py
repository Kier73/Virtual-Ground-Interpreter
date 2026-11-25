"""VLD-002: observation-relative finite-state Ground minimization.

A small, exact Mealy-machine laboratory.  The discovery algorithm refines a
partition; the independent checker validates a forward simulation and proves
minimality by pair distinguishability.  No sampled-trace assertion is used for
admission, and content hashes identify artifacts rather than authenticate them.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import json
from typing import Any


class ReductionError(ValueError):
    """Invalid machine or inadmissible reduction."""


def _digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _names(values: Any, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or (not values and not allow_empty):
        raise ReductionError(f"{label} must be a nonempty sequence")
    if any(type(v) is not str or not v for v in values):
        raise ReductionError(f"{label} must contain nonempty strings")
    result = tuple(values)
    if result != tuple(sorted(set(result))):
        raise ReductionError(f"{label} must be unique and lexicographically sorted")
    return result


@dataclass(frozen=True, slots=True)
class Edge:
    state: str
    input: str
    next: str
    observations: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"state": self.state, "input": self.input, "next": self.next,
                "observations": dict(self.observations)}


@dataclass(frozen=True, slots=True)
class FiniteGround:
    states: tuple[str, ...]
    alphabet: tuple[str, ...]
    initial: str
    transitions: tuple[Edge, ...]

    def __post_init__(self) -> None:
        _names(self.states, "states")
        _names(self.alphabet, "alphabet")
        if len(self.states) > 128 or len(self.alphabet) > 32:
            raise ReductionError("finite pilot limit: 128 states and 32 inputs")
        if self.initial not in self.states:
            raise ReductionError("initial state is absent")
        if len(self.transitions) != len(self.states) * len(self.alphabet):
            raise ReductionError("transition function must be total")
        keys = []
        channels: tuple[str, ...] | None = None
        for edge in self.transitions:
            if not isinstance(edge, Edge) or edge.state not in self.states or edge.next not in self.states:
                raise ReductionError("transition references an unknown state")
            if edge.input not in self.alphabet:
                raise ReductionError("transition references an unknown input")
            fields = tuple(k for k, _ in edge.observations)
            if fields != tuple(sorted(set(fields))) or any(type(k) is not str or not k or type(v) is not str for k, v in edge.observations):
                raise ReductionError("observations must be sorted unique string channels and values")
            if channels is None:
                channels = fields
            if fields != channels:
                raise ReductionError("all transitions must declare the same channels")
            keys.append((edge.state, edge.input))
        expected = [(s, a) for s in self.states for a in self.alphabet]
        if keys != expected:
            raise ReductionError("transitions must be total, unique and canonically ordered")

    @property
    def channels(self) -> tuple[str, ...]:
        return tuple(k for k, _ in self.transitions[0].observations)

    def edges(self) -> dict[tuple[str, str], Edge]:
        return {(e.state, e.input): e for e in self.transitions}

    def reachable(self) -> tuple[str, ...]:
        edges = self.edges()
        found = {self.initial}
        todo = deque([self.initial])
        while todo:
            s = todo.popleft()
            for a in self.alphabet:
                dest = edges[(s, a)].next
                if dest not in found:
                    found.add(dest)
                    todo.append(dest)
        return tuple(sorted(found))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "VGI-FiniteMealy-1", "states": list(self.states),
                "alphabet": list(self.alphabet), "initial": self.initial,
                "transitions": [e.to_dict() for e in self.transitions]}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, record: Any) -> "FiniteGround":
        if type(record) is not dict or set(record) != {"schema", "states", "alphabet", "initial", "transitions"}:
            raise ReductionError("machine fields are not canonical")
        if record["schema"] != "VGI-FiniteMealy-1" or type(record["initial"]) is not str:
            raise ReductionError("unknown machine schema")
        if type(record["states"]) is not list or type(record["alphabet"]) is not list:
            raise ReductionError("states and alphabet must be lists")
        if type(record["transitions"]) is not list:
            raise ReductionError("transitions must be a list")
        edges = []
        for item in record["transitions"]:
            if type(item) is not dict or set(item) != {"state", "input", "next", "observations"}:
                raise ReductionError("invalid transition fields")
            if any(type(item[k]) is not str for k in ("state", "input", "next")) or type(item["observations"]) is not dict:
                raise ReductionError("invalid transition values")
            try:
                pairs = tuple(sorted(item["observations"].items()))
            except TypeError as exc:
                raise ReductionError("invalid observation fields") from exc
            edges.append(Edge(item["state"], item["input"], item["next"], pairs))
        return cls(tuple(record["states"]), tuple(record["alphabet"]), record["initial"], tuple(edges))


def _project(edge: Edge, channels: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    values = dict(edge.observations)
    return tuple((k, values[k]) for k in channels)


def _classes(states: tuple[str, ...], group_of: dict[str, int]) -> list[tuple[str, ...]]:
    blocks: dict[int, list[str]] = {}
    for state in states:
        blocks.setdefault(group_of[state], []).append(state)
    return sorted((tuple(v) for v in blocks.values()), key=lambda b: b[0])


def _partition(source: FiniteGround, channels: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Moore-style refinement to its stable observation-relative congruence."""
    edges, states = source.edges(), source.reachable()
    group_of = {s: 0 for s in states}
    while True:
        signatures = {}
        for s in states:
            signatures[s] = tuple((_project(edges[(s, a)], channels),
                                  group_of[edges[(s, a)].next]) for a in source.alphabet)
        distinct = {sig: i for i, sig in enumerate(sorted(set(signatures.values())))}
        updated = {s: distinct[signatures[s]] for s in states}
        if _classes(states, updated) == _classes(states, group_of):
            return _classes(states, updated)
        group_of = updated


@dataclass(frozen=True, slots=True)
class ReductionCertificate:
    source_sha256: str
    target_sha256: str
    channels: tuple[str, ...]
    mapping: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "VGI-StateReductionWitness-1", "source_sha256": self.source_sha256,
                "target_sha256": self.target_sha256, "channels": list(self.channels),
                "mapping": [[src, dst] for src, dst in self.mapping]}

    @classmethod
    def from_dict(cls, record: Any) -> "ReductionCertificate":
        if type(record) is not dict or set(record) != {"schema", "source_sha256", "target_sha256", "channels", "mapping"}:
            raise ReductionError("invalid witness fields")
        if record["schema"] != "VGI-StateReductionWitness-1":
            raise ReductionError("unknown witness schema")
        for key in ("source_sha256", "target_sha256"):
            v = record[key]
            if type(v) is not str or len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
                raise ReductionError("invalid artifact fingerprint")
        channels = _names(record["channels"], "channels", allow_empty=True)
        pairs = record["mapping"]
        if type(pairs) is not list or any(type(p) is not list or len(p) != 2 or any(type(x) is not str for x in p) for p in pairs):
            raise ReductionError("invalid state map")
        mapping = tuple((a, b) for a, b in pairs)
        if tuple(a for a, _ in mapping) != tuple(sorted(set(a for a, _ in mapping))):
            raise ReductionError("noncanonical state map")
        return cls(record["source_sha256"], record["target_sha256"], channels, mapping)


def discover_reduction(source: FiniteGround, channels: tuple[str, ...]) -> tuple[FiniteGround, ReductionCertificate]:
    """Discover a reachable-state quotient, without influencing its independent checker."""
    channels = _names(channels, "channels", allow_empty=True)
    if not set(channels) <= set(source.channels):
        raise ReductionError("an observer requests unknown channels")
    blocks = _partition(source, channels)
    mapping = {s: f"q{i:03d}" for i, block in enumerate(blocks) for s in block}
    edges = source.edges()
    reduced = []
    for block in blocks:
        representative = block[0]
        for a in source.alphabet:
            e = edges[(representative, a)]
            reduced.append(Edge(mapping[representative], a, mapping[e.next], _project(e, channels)))
    target = FiniteGround(tuple(sorted(set(mapping.values()))), source.alphabet,
                          mapping[source.initial], tuple(reduced))
    certificate = ReductionCertificate(source.fingerprint, target.fingerprint, channels,
                                       tuple(sorted(mapping.items())))
    return target, certificate


def _pair_distinguishability(target: FiniteGround) -> int:
    """Independent least fixed point: pair (x,y) is distinct if output or a successor pair differs."""
    edges = target.edges()
    states = target.states
    pairs = [(x, y) for i, x in enumerate(states) for y in states[i + 1:]]
    known: set[tuple[str, str]] = set()
    def ordered(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a < b else (b, a)
    while True:
        fresh = set()
        for x, y in pairs:
            if (x, y) in known:
                continue
            if any(edges[(x, a)].observations != edges[(y, a)].observations or
                   (edges[(x, a)].next != edges[(y, a)].next and
                    ordered(edges[(x, a)].next, edges[(y, a)].next) in known)
                   for a in target.alphabet):
                fresh.add((x, y))
        if not fresh:
            break
        known |= fresh
    if len(known) != len(pairs):
        raise ReductionError("target retains observationally equivalent distinct states")
    return len(known)


def verify_reduction(source: FiniteGround, target: FiniteGround,
                     certificate: ReductionCertificate) -> dict[str, Any]:
    """Check the witness without calling discover_reduction or its partition algorithm.

    The local commuting square yields equivalence for *all finite input words*
    by induction.  The independent pair fixed point additionally checks that
    no smaller reachable deterministic Mealy quotient preserves these channels.
    """
    if not isinstance(certificate, ReductionCertificate):
        raise ReductionError("expected a typed certificate")
    if (certificate.source_sha256 != source.fingerprint or
        certificate.target_sha256 != target.fingerprint):
        raise ReductionError("artifact digest mismatch")
    if _names(certificate.channels, "channels", allow_empty=True) != certificate.channels:
        raise ReductionError("noncanonical channel scope")
    if not set(certificate.channels) <= set(source.channels):
        raise ReductionError("observer channels missing from source")
    if certificate.channels != target.channels or source.alphabet != target.alphabet:
        raise ReductionError("observer projection or input alphabet changed")
    witness = dict(certificate.mapping)
    reachable = source.reachable()
    if tuple(s for s, _ in certificate.mapping) != reachable:
        raise ReductionError("witness must cover exactly the reachable source states")
    if set(witness.values()) != set(target.states):
        raise ReductionError("every reduced state must be represented")
    if witness[source.initial] != target.initial:
        raise ReductionError("initial states do not correspond")
    if set(target.reachable()) != set(target.states):
        raise ReductionError("candidate contains unreachable states")
    old, new = source.edges(), target.edges()
    for s in reachable:
        for a in source.alphabet:
            ref = old[(s, a)]
            out = new[(witness[s], a)]
            if _project(ref, certificate.channels) != out.observations:
                raise ReductionError(f"observable output mismatch at ({s}, {a})")
            if witness[ref.next] != out.next:
                raise ReductionError(f"successor mismatch at ({s}, {a})")
    pairs = _pair_distinguishability(target)
    return {"status": "VERIFIED", "scope": "all finite input sequences from initial state",
            "original_states": len(source.states), "reachable_states": len(reachable),
            "reduced_states": len(target.states), "checked_edges": len(reachable) * len(source.alphabet),
            "distinguished_pairs": pairs, "channels": list(certificate.channels),
            "source_sha256": source.fingerprint, "target_sha256": target.fingerprint,
            "minimal_reachable_quotient": True}
