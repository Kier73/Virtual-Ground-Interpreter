"""GEOMETRY-FIRST-002: discover and certify finite-field polynomial lifts.

The only admissible acceleration is one whose lifted affine transition agrees
with *every* edge of a finite snapshot. A short fitting probe is not a proof.
The snapshot is not independently trusted external evidence: its fingerprint
only binds the exact finite transition table supplied by the observer.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Sequence

from .affine import ModularAffineMap
from .geometry_first import FiniteGeometry, GeometryError


Monomial = tuple[int, int]
MAX_SIDE = 257  # Keep the full-domain verification finite and reproducible.
MAX_DEGREE = 3  # Research-limited polynomial basis (at most ten terms).


class PolynomialLiftError(GeometryError):
    """The observed transition does not admit this certified polynomial lift."""


def _integer(value: int, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PolynomialLiftError(f"{name} must be an integer >= {minimum}")
    return value


def _prime(value: int) -> int:
    _integer(value, "finite-field modulus", 3)
    if value > MAX_SIDE:
        raise PolynomialLiftError("finite-field modulus exceeds declared audit budget")
    for divisor in range(2, int(value**0.5) + 1):
        if value % divisor == 0:
            raise PolynomialLiftError("polynomial fitting requires a prime modulus")
    return value


def _fingerprint(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def _monomials(degree: int) -> tuple[Monomial, ...]:
    if degree > MAX_DEGREE:
        raise PolynomialLiftError("maximum polynomial degree exceeds declared audit budget")
    return tuple((x, total - x) for total in range(degree + 1)
                 for x in range(total, -1, -1))


def _eval(monomial: Monomial, x: int, y: int, modulus: int) -> int:
    a, b = monomial
    return (pow(x, a, modulus) * pow(y, b, modulus)) % modulus


def _rank(rows: Sequence[Sequence[int]], modulus: int) -> int:
    if not rows:
        return 0
    work = [list(r) for r in rows]
    rank = 0
    for col in range(len(work[0])):
        pivot = next((i for i in range(rank, len(work)) if work[i][col] % modulus), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        inv = pow(work[rank][col] % modulus, -1, modulus)
        work[rank] = [(a * inv) % modulus for a in work[rank]]
        for i in range(rank + 1, len(work)):
            k = work[i][col] % modulus
            if k:
                work[i] = [(a - k * b) % modulus
                           for a, b in zip(work[i], work[rank])]
        rank += 1
        if rank == len(work):
            break
    return rank


def _solve(square: Sequence[Sequence[int]], outputs: Sequence[int],
           modulus: int) -> tuple[int, ...]:
    size = len(square)
    if len(outputs) != size or any(len(row) != size for row in square):
        raise PolynomialLiftError("invalid full-rank probe system")
    work = [[*row, out % modulus] for row, out in zip(square, outputs)]
    for column in range(size):
        pivot = next((i for i in range(column, size)
                      if work[i][column] % modulus), None)
        if pivot is None:
            raise PolynomialLiftError("fitting probes are not independent")
        work[column], work[pivot] = work[pivot], work[column]
        inv = pow(work[column][column] % modulus, -1, modulus)
        work[column] = [v * inv % modulus for v in work[column]]
        for row in range(size):
            if row == column:
                continue
            factor = work[row][column]
            if factor:
                work[row] = [(v - factor * u) % modulus
                             for v, u in zip(work[row], work[column])]
    return tuple(row[-1] for row in work)


@dataclass(frozen=True)
class TransitionSnapshot:
    """Complete observations of one named action on a finite coordinate chart.

    The caller supplies all edges. Capturing from FiniteGeometry is one
    synthetic way to obtain the table, not external evidence admission.
    """
    side: int
    action: str
    targets: tuple[int, ...]

    def __post_init__(self) -> None:
        side = _prime(self.side)
        if not isinstance(self.action, str) or not self.action:
            raise PolynomialLiftError("action must be non-empty")
        if not isinstance(self.targets, tuple) or len(self.targets) != side * side:
            raise PolynomialLiftError("snapshot must contain one edge per source point")
        if any(isinstance(v, bool) or not isinstance(v, int) or
               v < 0 or v >= side * side for v in self.targets):
            raise PolynomialLiftError("snapshot contains invalid destination")

    @classmethod
    def capture(cls, geometry: FiniteGeometry, action: str) -> "TransitionSnapshot":
        return cls(geometry.side, action,
                   tuple(geometry.step(p, action) for p in geometry.points()))

    @property
    def fingerprint(self) -> str:
        return _fingerprint({"format": "VGI-TransitionSnapshot-1", "side": self.side,
                             "action": self.action, "targets": self.targets})

    def coordinates(self, state: int) -> tuple[int, int]:
        _integer(state, "state")
        if state >= self.side ** 2:
            raise PolynomialLiftError("state outside Ground")
        return divmod(state, self.side)


@dataclass(frozen=True)
class PolynomialLiftCertificate:
    """A discovered polynomial feature map whose dynamics are exactly affine.

    A finite-field coordinate lift is certified only after all transitions
    and all feature relations are verified. Runtime queries reuse VGI's
    existing ModularAffineMap and its logarithmic binary powering.
    """
    snapshot: TransitionSnapshot
    max_degree: int
    features: tuple[Monomial, ...]
    transform: ModularAffineMap
    fit_probes: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, TransitionSnapshot):
            raise PolynomialLiftError("certificate requires a transition snapshot")
        degree = _integer(self.max_degree, "maximum degree", 1)
        if degree >= self.snapshot.side:
            raise PolynomialLiftError("degree must be below finite-field modulus")
        allowed = _monomials(degree)
        if (len(set(self.features)) != len(self.features)
            or not {(1, 0), (0, 1)}.issubset(self.features)
            or any(m not in allowed or m == (0, 0) for m in self.features)):
            raise PolynomialLiftError("certificate has an invalid feature selection")
        if (not isinstance(self.transform, ModularAffineMap)
            or self.transform.modulus != self.snapshot.side
            or self.transform.dimension != len(self.features)):
            raise PolynomialLiftError("lifted transform has incompatible dimensions")
        if len(self.fit_probes) != len(allowed) or len(set(self.fit_probes)) != len(allowed):
            raise PolynomialLiftError("incomplete fitting-probe record")
        for probe in self.fit_probes:
            self.snapshot.coordinates(probe)
        rows = [tuple(_eval(m, *self.snapshot.coordinates(p), self.snapshot.side)
                      for m in allowed) for p in self.fit_probes]
        if _rank(rows, self.snapshot.side) != len(allowed):
            raise PolynomialLiftError("certificate fitting probes are not independent")
        # Verification does not trust fitted equations or claimed sample status.
        for state, target in enumerate(self.snapshot.targets):
            actual = self._lift(self.snapshot.coordinates(target))
            predicted = self.transform.apply(self._lift(self.snapshot.coordinates(state)))
            if actual != predicted:
                raise PolynomialLiftError(f"lift fails at observed edge {state} -> {target}")

    def _lift(self, coords: tuple[int, int]) -> tuple[int, ...]:
        return tuple(_eval(m, *coords, self.snapshot.side) for m in self.features)

    @property
    def fingerprint(self) -> str:
        return _fingerprint({
            "format": "VGI-PolynomialLiftCertificate-1",
            "snapshot_fingerprint": self.snapshot.fingerprint,
            "max_degree": self.max_degree,
            "features": self.features,
            "transform": self.transform.to_dict(),
            "fit_probes": self.fit_probes,
            "verified_edges": len(self.snapshot.targets),
        })

    def state_at(self, start: int, tick: int) -> "PolynomialLiftResult":
        """Navigate from arbitrary runtime operands to any nonnegative tick."""
        coords = self.snapshot.coordinates(start)
        _integer(tick, "logical tick")
        powered = self.transform.power(self._lift(coords), tick)
        x = powered[self.features.index((1, 0))]
        y = powered[self.features.index((0, 1))]
        if powered != self._lift((x, y)):
            raise PolynomialLiftError("powered result violates lifted coordinate invariant")
        return PolynomialLiftResult(
            self.snapshot.action, start, tick, x * self.snapshot.side + y,
            (x, y), powered, self.fingerprint, len(self.snapshot.targets),
            tick.bit_length(), 0,
        )


@dataclass(frozen=True)
class PolynomialLiftResult:
    action: str
    start: int
    tick: int
    state: int
    coordinates: tuple[int, int]
    lifted_coordinates: tuple[int, ...]
    certificate_fingerprint: str
    verified_edges: int
    exponent_bits: int
    materialized_intermediate_states: int

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "VGI-PolynomialLiftResult-1", "action": self.action,
            "start": self.start, "logical_tick": self.tick,
            "state": self.state, "coordinates": list(self.coordinates),
            "lifted_coordinates": list(self.lifted_coordinates),
            "certificate_fingerprint": self.certificate_fingerprint,
            "verified_edges": self.verified_edges,
            "exponent_bits": self.exponent_bits,
            "materialized_intermediate_states": self.materialized_intermediate_states,
            "method": "certified_polynomial_coordinate_lift_and_affine_power",
        }


def discover_polynomial_lift(snapshot: TransitionSnapshot,
                             max_degree: int = 2) -> PolynomialLiftCertificate:
    """Find the least feature closure from x,y using polynomials up to degree d.

    The chart, maximum degree and observed transition table are declared;
    the feature support and affine lift are inferred, not prescribed. A
    candidate polynomial is admitted only if exact on *every* observed edge.
    """
    if not isinstance(snapshot, TransitionSnapshot):
        raise PolynomialLiftError("discovery requires complete TransitionSnapshot")
    degree = _integer(max_degree, "maximum degree", 1)
    if degree >= snapshot.side:
        raise PolynomialLiftError("degree must be below finite-field modulus")
    p = snapshot.side
    basis = _monomials(degree)
    # Find a rank-complete set of deterministic probes on the finite domain.
    probes: list[int] = []
    probe_rows: list[tuple[int, ...]] = []
    for state in range(p * p):
        x, y = snapshot.coordinates(state)
        row = tuple(_eval(m, x, y, p) for m in basis)
        if _rank([*probe_rows, row], p) > len(probe_rows):
            probes.append(state)
            probe_rows.append(row)
            if len(probes) == len(basis):
                break
    if len(probes) != len(basis):
        raise PolynomialLiftError("unable to locate independent finite-field probes")

    features: set[Monomial] = {(1, 0), (0, 1)}
    expressions: dict[Monomial, dict[Monomial, int]] = {}
    while True:
        previous = set(features)
        for feature in sorted(features - expressions.keys()):
            expected = [_eval(feature, *snapshot.coordinates(snapshot.targets[state]), p)
                        for state in probes]
            coefficients = _solve(probe_rows, expected, p)
            # Critically: check all observed points, not only fitting probes.
            if any(sum(coefficient * _eval(mon, *snapshot.coordinates(state), p)
                       for mon, coefficient in zip(basis, coefficients)) % p
                   != _eval(feature, *snapshot.coordinates(snapshot.targets[state]), p)
                   for state in range(p * p)):
                raise PolynomialLiftError(
                    f"observed successor of {feature} is not degree-{degree} polynomial"
                )
            expressions[feature] = {mon: c for mon, c in zip(basis, coefficients) if c}
            features.update(mon for mon, c in expressions[feature].items()
                            if c and mon != (0, 0))
        if features == previous:
            break
    # Keep source coordinates first; then stable deterministic feature ordering.
    chosen = ((1, 0), (0, 1)) + tuple(sorted(features - {(1, 0), (0, 1)}))
    matrix = tuple(tuple(expressions[f].get(other, 0) for other in chosen)
                   for f in chosen)
    offset = tuple(expressions[f].get((0, 0), 0) for f in chosen)
    transform = ModularAffineMap(p, matrix, offset)
    return PolynomialLiftCertificate(snapshot, degree, chosen, transform, tuple(probes))


__all__ = ["PolynomialLiftError", "TransitionSnapshot", "PolynomialLiftCertificate",
           "PolynomialLiftResult", "discover_polynomial_lift"]