"""Certified modular-affine fast-forward over one verified VGI orbit."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .orbit import OrbitIndex, OrbitTimeCoordinate


class AffineFastForwardError(ValueError):
    """Invalid modular-affine model or orbit certificate."""


def _integer(value: Any, label: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AffineFastForwardError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise AffineFastForwardError(f"{label} must be at least {minimum}")
    return value


def _digest(value: Any) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AffineFastForwardError(f"value is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def _vector(
    values: Sequence[int], dimension: int, modulus: int, label: str,
) -> tuple[int, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise AffineFastForwardError(f"{label} must be a finite integer sequence")
    result = tuple(values)
    if len(result) != dimension:
        raise AffineFastForwardError(f"{label} must contain exactly {dimension} coordinates")
    for value in result:
        _integer(value, f"{label} coordinate")
    return tuple(value % modulus for value in result)


def _multiply(
    left: tuple[tuple[int, ...], ...],
    right: tuple[tuple[int, ...], ...],
    modulus: int,
) -> tuple[tuple[int, ...], ...]:
    size = len(left)
    return tuple(
        tuple(
            sum(left[row][inner] * right[inner][column] for inner in range(size))
            % modulus
            for column in range(size)
        )
        for row in range(size)
    )


def _power(
    matrix: tuple[tuple[int, ...], ...], exponent: int, modulus: int,
) -> tuple[tuple[int, ...], ...]:
    """Square a matrix over Z/modulus Z in logarithmic exponent steps."""
    size = len(matrix)
    result = tuple(
        tuple(1 if row == column else 0 for column in range(size))
        for row in range(size)
    )
    factor = matrix
    remaining = exponent
    while remaining:
        if remaining & 1:
            result = _multiply(factor, result, modulus)
        remaining >>= 1
        if remaining:
            factor = _multiply(factor, factor, modulus)
    return result


@dataclass(frozen=True, slots=True)
class ModularAffineMap:
    """The total map x -> Mx + b over (Z/modulus Z)^dimension.

    The modulus need not be prime and the matrix need not be invertible.
    Python integer arithmetic is exact; coefficients and results are reduced
    modulo the declared modulus.
    """

    modulus: int
    matrix: tuple[tuple[int, ...], ...]
    offset: tuple[int, ...]

    def __post_init__(self) -> None:
        modulus = _integer(self.modulus, "modulus", 2)
        if isinstance(self.matrix, (str, bytes, bytearray)):
            raise AffineFastForwardError("matrix must be a non-empty square integer matrix")
        try:
            rows = tuple(tuple(row) for row in self.matrix)
        except TypeError as exc:
            raise AffineFastForwardError("matrix must be a finite square integer matrix") from exc
        dimension = len(rows)
        if dimension < 1 or any(len(row) != dimension for row in rows):
            raise AffineFastForwardError("matrix must be non-empty and square")
        for row in rows:
            for coefficient in row:
                _integer(coefficient, "matrix coefficient")
        if isinstance(self.offset, (str, bytes, bytearray)):
            raise AffineFastForwardError("offset must be a finite integer vector")
        try:
            offset = tuple(self.offset)
        except TypeError as exc:
            raise AffineFastForwardError("offset must be a finite integer vector") from exc
        if len(offset) != dimension:
            raise AffineFastForwardError("offset dimension must match the matrix")
        for value in offset:
            _integer(value, "offset coordinate")
        object.__setattr__(
            self, "matrix",
            tuple(tuple(value % modulus for value in row) for row in rows),
        )
        object.__setattr__(self, "offset", tuple(value % modulus for value in offset))

    @property
    def dimension(self) -> int:
        return len(self.matrix)

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-ModularAffineMap-1",
            "domain": {"ring": "Z/modulus Z", "modulus": self.modulus,
                       "dimension": self.dimension},
            "matrix": [list(row) for row in self.matrix],
            "offset": list(self.offset),
            "equation": "x_next = M*x + b (mod modulus)",
        }

    def apply(self, values: Sequence[int]) -> tuple[int, ...]:
        """Apply one exact affine step."""
        source = _vector(values, self.dimension, self.modulus, "source vector")
        return tuple(
            (
                sum(self.matrix[row][column] * source[column]
                    for column in range(self.dimension))
                + self.offset[row]
            ) % self.modulus
            for row in range(self.dimension)
        )

    def power(self, values: Sequence[int], transitions: int) -> tuple[int, ...]:
        """Return F^transitions(values) by homogeneous matrix exponentiation."""
        count = _integer(transitions, "transitions", 0)
        source = _vector(values, self.dimension, self.modulus, "source vector")
        size = self.dimension + 1
        homogeneous = tuple(
            tuple(self.matrix[row]) + (self.offset[row],)
            for row in range(self.dimension)
        ) + ((0,) * self.dimension + (1,),)
        powered = _power(homogeneous, count, self.modulus)
        extended = source + (1,)
        return tuple(
            sum(powered[row][column] * extended[column] for column in range(size))
            % self.modulus
            for row in range(self.dimension)
        )


@dataclass(frozen=True, slots=True)
class AffineFastForwardResult:
    """An exact state returned by certificate-bound affine powering."""

    status: str
    requested_time: OrbitTimeCoordinate
    resolved_time: OrbitTimeCoordinate | None
    state: str | None
    vector: tuple[int, ...] | None
    logical_transitions: int
    exponent_bits: int
    materialized_intermediate_states: int
    method: str | None
    certificate_fingerprint: str
    orbit_fingerprint: str
    ground_fingerprint: str
    policy_fingerprint: str
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-AffineFastForwardResult-1",
            "status": self.status,
            "requested_time": self.requested_time.to_dict(),
            "resolved_time": (
                self.resolved_time.to_dict() if self.resolved_time is not None else None
            ),
            "state": self.state,
            "vector": list(self.vector) if self.vector is not None else None,
            "logical_transitions": self.logical_transitions,
            "exponent_bits": self.exponent_bits,
            "materialized_intermediate_states": self.materialized_intermediate_states,
            "method": self.method,
            "certificate_fingerprint": self.certificate_fingerprint,
            "orbit_fingerprint": self.orbit_fingerprint,
            "ground_fingerprint": self.ground_fingerprint,
            "policy_fingerprint": self.policy_fingerprint,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AffineOrbitCertificate:
    """An affine generator checked against one closed, replay-verified orbit.

    The state encoding is caller supplied, total, and injective over every
    distinct state in the OrbitIndex. Every retained transition is checked.
    """

    orbit: OrbitIndex
    transform: ModularAffineMap
    state_vectors: tuple[tuple[str, tuple[int, ...]], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.orbit, OrbitIndex):
            raise AffineFastForwardError("certificate requires an OrbitIndex")
        if not self.orbit.closed:
            raise AffineFastForwardError("affine fast-forward requires a closed OrbitIndex")
        if not isinstance(self.transform, ModularAffineMap):
            raise AffineFastForwardError("certificate requires a ModularAffineMap")

        mapping: dict[str, tuple[int, ...]] = {}
        try:
            items = tuple(self.state_vectors)
        except TypeError as exc:
            raise AffineFastForwardError("state_vectors must contain state/vector pairs") from exc
        for item in items:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise AffineFastForwardError("each encoding must be a (state, vector) pair")
            state, values = item
            if not isinstance(state, str) or not state:
                raise AffineFastForwardError("encoded state names must be non-empty strings")
            if state in mapping:
                raise AffineFastForwardError(f"state {state!r} has duplicate vector encodings")
            mapping[state] = _vector(
                values, self.transform.dimension, self.transform.modulus,
                f"vector for state {state!r}",
            )

        path_states = tuple(self.orbit.states[:-1])
        expected = set(path_states)
        if len(expected) != len(path_states):
            raise AffineFastForwardError("OrbitIndex path must list each distinct state once before closure")
        if set(mapping) != expected:
            missing = sorted(expected - set(mapping))
            extra = sorted(set(mapping) - expected)
            raise AffineFastForwardError(
                f"encoding must cover exactly the certified orbit; missing={missing}, extra={extra}"
            )
        if len(set(mapping.values())) != len(mapping):
            raise AffineFastForwardError("state encoding must be injective over the certified orbit")

        for step in self.orbit.steps:
            predicted = self.transform.apply(mapping[step.source_state])
            if predicted != mapping[step.target_state]:
                raise AffineFastForwardError(
                    "affine map does not reproduce Ground edge "
                    f"{step.source_state!r} --{step.action!r}--> {step.target_state!r}"
                )

        object.__setattr__(
            self, "state_vectors",
            tuple(sorted(mapping.items(), key=lambda item: item[0])),
        )

    @classmethod
    def certify(
        cls,
        orbit: OrbitIndex,
        transform: ModularAffineMap,
        state_vectors: Mapping[str, Sequence[int]],
    ) -> "AffineOrbitCertificate":
        """Validate a candidate transform and complete state encoding."""
        if not isinstance(state_vectors, Mapping):
            raise AffineFastForwardError("state_vectors must map state IDs to vectors")
        return cls(
            orbit, transform,
            tuple((state, tuple(values)) for state, values in state_vectors.items()),
        )

    @property
    def orbit_fingerprint(self) -> str:
        return self.orbit.fingerprint

    @property
    def ground_fingerprint(self) -> str:
        return self.orbit.system.fingerprint

    @property
    def policy_fingerprint(self) -> str:
        return self.orbit.policy.fingerprint

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def _mapping(self) -> dict[str, tuple[int, ...]]:
        return dict(self.state_vectors)

    def to_dict(self) -> dict[str, Any]:
        mapping = self._mapping()
        checks = []
        for step in self.orbit.steps:
            predicted = self.transform.apply(mapping[step.source_state])
            checks.append({
                "source_state": step.source_state,
                "action": step.action,
                "target_state": step.target_state,
                "predicted_vector": list(predicted),
                "target_vector": list(mapping[step.target_state]),
                "matched": predicted == mapping[step.target_state],
            })
        return {
            "format": "VGI-AffineOrbitCertificate-1",
            "claim": "the affine map generates this exact closed fixed-policy OrbitIndex",
            "orbit_fingerprint": self.orbit_fingerprint,
            "ground_fingerprint": self.ground_fingerprint,
            "policy_fingerprint": self.policy_fingerprint,
            "clock_id": self.orbit.start_time.clock_id,
            "start_time": self.orbit.start_time.to_dict(),
            "start_state": self.orbit.start_state,
            "cycle_start_index": self.orbit.cycle_start_index,
            "cycle_period": self.orbit.cycle_period,
            "transform": self.transform.to_dict(),
            "transform_fingerprint": self.transform.fingerprint,
            "state_vectors": [
                {"state": state, "vector": list(values)}
                for state, values in self.state_vectors
            ],
            "verified_edges": checks,
            "scope": "all retained transitions in this closed orbit, not other states or policies",
        }

    def state_at(self, requested_time: OrbitTimeCoordinate) -> AffineFastForwardResult:
        """Navigate to an exact logical coordinate using the certified affine power."""
        if not isinstance(requested_time, OrbitTimeCoordinate):
            raise AffineFastForwardError("state_at requires an OrbitTimeCoordinate")
        common = {
            "certificate_fingerprint": self.fingerprint,
            "orbit_fingerprint": self.orbit_fingerprint,
            "ground_fingerprint": self.ground_fingerprint,
            "policy_fingerprint": self.policy_fingerprint,
        }
        if requested_time.clock_id != self.orbit.start_time.clock_id:
            return AffineFastForwardResult(
                "clock_mismatch", requested_time, None, None, None, 0, 0, 0, None,
                reason="requested coordinate belongs to another logical clock", **common,
            )
        if requested_time.tick < self.orbit.start_time.tick:
            return AffineFastForwardResult(
                "before_origin", requested_time, None, None, None, 0, 0, 0, None,
                reason="requested coordinate precedes the certified orbit origin", **common,
            )

        transitions = requested_time.tick - self.orbit.start_time.tick
        start_vector = self._mapping()[self.orbit.start_state]
        vector = self.transform.power(start_vector, transitions)
        inverse = {values: state for state, values in self.state_vectors}
        state = inverse.get(vector)
        if state is None:
            raise AffineFastForwardError(
                "certificate invariant violated: affine power escaped the closed orbit encoding"
            )
        if transitions < len(self.orbit.states) and state != self.orbit.states[transitions]:
            raise AffineFastForwardError(
                "certificate invariant violated: affine power disagrees with retained path prefix"
            )
        return AffineFastForwardResult(
            "located", requested_time, requested_time, state, vector,
            transitions, transitions.bit_length(), 0,
            "homogeneous_matrix_exponentiation", reason=None, **common,
        )


__all__ = [
    "AffineFastForwardError", "ModularAffineMap",
    "AffineFastForwardResult", "AffineOrbitCertificate",
]
