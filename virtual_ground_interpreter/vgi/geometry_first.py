"""Geometry-first finite computational affordance experiment.

All laws are checked against the complete finite substrate before shortcuts
are admitted. Hash identities never define distances or transitions.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import random
from typing import Sequence

from .affine import ModularAffineMap


class GeometryError(ValueError):
    """A geometric law or computational query is not admissible."""


def _nat(value: int, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise GeometryError(f"{name} must be an integer >= {minimum}")
    return value


def _digest(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


Point = tuple[int, int]
ACTIONS = ("alpha", "beta", "gamma", "delta", "epsilon")


@dataclass(frozen=True)
class FiniteGeometry:
    """An unlabeled 2-D toroidal geometry and three observed action channels.

    alpha/beta translate, gamma projects, delta shears, epsilon is nonlinear.
    Action names are deliberately opaque to the separate registry.
    """
    side: int = 100

    def __post_init__(self) -> None:
        _nat(self.side, "side", 2)

    def points(self) -> range:
        return range(self.side * self.side)

    def coordinates(self, point: int) -> Point:
        _nat(point, "point")
        if point >= self.side ** 2:
            raise GeometryError("point outside substrate")
        return divmod(point, self.side)

    def address(self, coordinates: Point) -> int:
        x, y = coordinates
        if not (0 <= x < self.side and 0 <= y < self.side):
            raise GeometryError("coordinates outside substrate")
        return x * self.side + y

    def step(self, point: int, action: str) -> int:
        x, y = self.coordinates(point)
        if action == "alpha":
            return self.address(((x + 1) % self.side, y))
        if action == "beta":
            return self.address((x, (y + 1) % self.side))
        if action == "gamma":
            return self.address((0, y))
        if action == "delta":
            return self.address(((x + y) % self.side, (y + 1) % self.side))
        if action == "epsilon":
            return self.address(((x + y * y) % self.side, (y + 1) % self.side))
        raise GeometryError("unknown substrate action")

    def distance(self, first: int, second: int) -> int:
        ax, ay = self.coordinates(first)
        bx, by = self.coordinates(second)
        dx, dy = abs(ax - bx), abs(ay - by)
        return min(dx, self.side - dx) + min(dy, self.side - dy)

    @property
    def fingerprint(self) -> str:
        # Coordinate-chart transitions are a canonical, seed-independent witness.
        return _digest({"format": "VGI-FiniteGeometry-1", "side": self.side,
                        "edges": [[self.step(p, a) for a in ACTIONS] for p in self.points()]})

    def opaque_addresses(self, seed: str) -> tuple[str, ...]:
        if not isinstance(seed, str) or not seed:
            raise GeometryError("seed must be a non-empty string")
        identifiers = tuple(sha256(f"{seed}:{p}".encode()).hexdigest()
                            for p in self.points())
        if len(set(identifiers)) != len(identifiers):
            raise GeometryError("opaque identifier collision")
        return identifiers


@dataclass(frozen=True)
class ObservedLaw:
    action: str
    bijective: bool
    idempotent: bool
    uniform_displacement: Point | None
    orbit_period: int | None
    affine_matrix: tuple[tuple[int, int], tuple[int, int]] | None
    affine_offset: Point | None
    complete_edges_checked: int


def discover_laws(geometry: FiniteGeometry) -> dict[str, ObservedLaw]:
    """Exhaustively infer valid shortcuts; do not extrapolate from samples."""
    laws: dict[str, ObservedLaw] = {}
    for action in ACTIONS:
        outputs = [geometry.step(p, action) for p in geometry.points()]
        shifts = set()
        for p, target in enumerate(outputs):
            x, y = geometry.coordinates(p)
            tx, ty = geometry.coordinates(target)
            shifts.add(((tx - x) % geometry.side, (ty - y) % geometry.side))
        delta = next(iter(shifts)) if len(shifts) == 1 else None
        period = None
        if delta is not None:
            period = math.lcm(
                geometry.side // math.gcd(geometry.side, delta[0]),
                geometry.side // math.gcd(geometry.side, delta[1]),
            )
        # Fit an affine transformation using only origin and basis probes,
        # then validate that hypothesis on *every* finite geometric point.
        o = geometry.coordinates(outputs[geometry.address((0, 0))])
        e1 = geometry.coordinates(outputs[geometry.address((1, 0))])
        e2 = geometry.coordinates(outputs[geometry.address((0, 1))])
        matrix = (((e1[0] - o[0]) % geometry.side, (e2[0] - o[0]) % geometry.side),
                  ((e1[1] - o[1]) % geometry.side, (e2[1] - o[1]) % geometry.side))
        affine = ModularAffineMap(geometry.side, matrix, o)
        if not all(affine.apply(geometry.coordinates(p)) == geometry.coordinates(target)
                   for p, target in enumerate(outputs)):
            matrix = None
            o = None
        laws[action] = ObservedLaw(
            action=action,
            bijective=len(set(outputs)) == len(outputs),
            idempotent=all(outputs[target] == target for target in outputs),
            uniform_displacement=delta,
            orbit_period=period,
            affine_matrix=matrix,
            affine_offset=o,
            complete_edges_checked=len(outputs),
        )
    return laws


def discover_commutations(geometry: FiniteGeometry) -> dict[tuple[str, str], bool]:
    return {(a, b): all(
        geometry.step(geometry.step(p, a), b)
        == geometry.step(geometry.step(p, b), a)
        for p in geometry.points()
    ) for a in ACTIONS for b in ACTIONS}


@dataclass(frozen=True)
class CertifiedGeometryNavigator:
    """One complete finite-law audit, followed by amortized logical-time queries.

    Unlike a sampled extrapolation, the observed affine map is accepted only
    after all points in the declared finite domain have been checked.
    """
    geometry: FiniteGeometry
    laws: tuple[ObservedLaw, ...] = ()
    certificate_fingerprint: str = ""

    def __post_init__(self) -> None:
        observed = tuple(discover_laws(self.geometry)[action] for action in ACTIONS)
        object.__setattr__(self, "laws", observed)
        object.__setattr__(self, "certificate_fingerprint", _digest({
            "geometry": self.geometry.fingerprint,
            "laws": [{"action": l.action, "bijective": l.bijective,
                      "idempotent": l.idempotent, "shift": l.uniform_displacement,
                      "affine": l.affine_matrix, "offset": l.affine_offset,
                      "checked": l.complete_edges_checked} for l in observed],
        }))

    def state_at(self, action: str, start: int, tick: int) -> int:
        try:
            law = next(l for l in self.laws if l.action == action)
        except StopIteration as exc:
            raise GeometryError("unregistered geometric action") from exc
        return _navigate_verified(self.geometry, law, start, tick)


def _navigate_verified(geometry: FiniteGeometry, law: ObservedLaw,
                       start: int, tick: int) -> int:
    geometry.coordinates(start)
    _nat(tick, "logical tick")
    if tick == 0:
        return start
    if law.uniform_displacement is not None:
        x, y = geometry.coordinates(start)
        dx, dy = law.uniform_displacement
        return geometry.address(((x + tick * dx) % geometry.side,
                                 (y + tick * dy) % geometry.side))
    if law.idempotent:
        return geometry.step(start, law.action)
    if law.affine_matrix is not None and law.affine_offset is not None:
        affine = ModularAffineMap(geometry.side, law.affine_matrix, law.affine_offset)
        return geometry.address(affine.power(geometry.coordinates(start), tick))
    raise GeometryError("no verified navigation shortcut for this action")


def navigate(geometry: FiniteGeometry, law: ObservedLaw, start: int, tick: int) -> int:
    """Reach a logical state without enumerating tick physical transitions."""
    if law.action not in ACTIONS or law.complete_edges_checked != geometry.side ** 2:
        raise GeometryError("law not checked for complete geometry")
    if discover_laws(geometry)[law.action] != law:
        raise GeometryError("law differs from current observed geometry")
    return _navigate_verified(geometry, law, start, tick)


@dataclass(frozen=True)
class CodonRequirement:
    name: str
    bijective: bool
    idempotent: bool | None = None
    displacement: Point | None = None


def bind_registry(laws: dict[str, ObservedLaw],
                  registry: Sequence[CodonRequirement]) -> dict[str, str]:
    """Match an independent symbolic grammar to observed algebraic contracts."""
    bindings: dict[str, str] = {}
    for codon in registry:
        if codon.name in bindings:
            raise GeometryError("duplicate codon")
        eligible = [law.action for law in laws.values()
                    if law.bijective == codon.bijective
                    and (codon.idempotent is None or law.idempotent == codon.idempotent)
                    and (codon.displacement is None
                         or law.uniform_displacement == codon.displacement)]
        if len(eligible) != 1:
            raise GeometryError(f"{codon.name}: expected one match, got {len(eligible)}")
        bindings[codon.name] = eligible[0]
    return bindings


def place_dependency_graph(geometry: FiniteGeometry, dependencies: Sequence[Sequence[int]],
                           seed: int, guided: bool) -> tuple[tuple[int, ...], int]:
    """Place codons, minimizing parent-edge distance when guided=True.

    Geometry is homogeneous: the anchor is arbitrary; only relative placement
    can be selected from geometric evidence.
    """
    rng = random.Random(seed)
    occupied: set[int] = set()
    positions: list[int] = []
    n = geometry.side * geometry.side
    if len(dependencies) > n:
        raise GeometryError("more codons than points")
    for i, parents in enumerate(dependencies):
        if any(isinstance(p, bool) or not isinstance(p, int) or p < 0 or p >= i
               for p in parents):
            raise GeometryError("dependencies must point to earlier codons")
        if not guided or not parents:
            available = [p for p in geometry.points() if p not in occupied]
            candidate = rng.choice(available)
        else:
            # A bounded ring around all parents; all candidate costs are explicit.
            candidates: set[int] = set()
            for parent in parents:
                x, y = geometry.coordinates(positions[parent])
                for radius in range(1, geometry.side // 2 + 1):
                    for dx, dy in ((radius, 0), (-radius, 0), (0, radius), (0, -radius)):
                        p = geometry.address(((x + dx) % geometry.side,
                                              (y + dy) % geometry.side))
                        if p not in occupied:
                            candidates.add(p)
                    if len(candidates) >= 16:
                        break
            if not candidates:
                raise GeometryError("placement search exhausted")
            min_cost = min(sum(geometry.distance(p, positions[k]) for k in parents)
                           for p in candidates)
            best = sorted(p for p in candidates if
                          sum(geometry.distance(p, positions[k]) for k in parents) == min_cost)
            candidate = rng.choice(best)
        positions.append(candidate)
        occupied.add(candidate)
    cost = sum(geometry.distance(positions[i], positions[parent])
               for i, parents in enumerate(dependencies) for parent in parents)
    return tuple(positions), cost


Matrix = tuple[tuple[int, ...], ...]


def _matrix(value: Sequence[Sequence[int]], modulus: int) -> Matrix:
    try:
        rows = tuple(tuple(row) for row in value)
    except TypeError as exc:
        raise GeometryError("matrix must be a sequence of rows") from exc
    if not rows or any(len(row) != len(rows) for row in rows):
        raise GeometryError("only nonempty square matrices are supported")
    for row in rows:
        for entry in row:
            if isinstance(entry, bool) or not isinstance(entry, int):
                raise GeometryError("matrix entries must be integers")
    return tuple(tuple(value % modulus for value in row) for row in rows)


def _matvec(matrix: Matrix, vector: Sequence[int], modulus: int) -> tuple[int, ...]:
    if len(vector) != len(matrix) or any(isinstance(v, bool) or not isinstance(v, int)
                                        for v in vector):
        raise GeometryError("vector shape/type mismatch")
    return tuple(sum(a * b for a, b in zip(row, vector)) % modulus for row in matrix)


@dataclass(frozen=True)
class DeferredMatrixProduct:
    """Addressable AB with dynamically supplied operands; no dense AB built yet."""
    left: Matrix
    right: Matrix
    modulus: int
    context_fingerprint: str

    @classmethod
    def from_operands(cls, left: Sequence[Sequence[int]],
                      right: Sequence[Sequence[int]], modulus: int) -> "DeferredMatrixProduct":
        _nat(modulus, "modulus", 2)
        a, b = _matrix(left, modulus), _matrix(right, modulus)
        if len(a) != len(b):
            raise GeometryError("matrix sizes do not match")
        return cls(a, b, modulus, _digest({"left": a, "right": b, "modulus": modulus}))

    def __post_init__(self) -> None:
        _nat(self.modulus, "modulus", 2)
        a, b = _matrix(self.left, self.modulus), _matrix(self.right, self.modulus)
        if a != self.left or b != self.right or len(a) != len(b):
            raise GeometryError("deferred product requires immutable canonical operands")
        if self.context_fingerprint != _digest({"left": a, "right": b,
                                                "modulus": self.modulus}):
            raise GeometryError("dynamic operand context fingerprint mismatch")

    @property
    def dimension(self) -> int:
        return len(self.left)

    def entry(self, row: int, column: int) -> int:
        _nat(row, "row")
        _nat(column, "column")
        if row >= self.dimension or column >= self.dimension:
            raise GeometryError("entry outside matrix")
        return sum(self.left[row][k] * self.right[k][column]
                   for k in range(self.dimension)) % self.modulus

    def apply_vector(self, vector: Sequence[int]) -> tuple[int, ...]:
        return _matvec(self.left, _matvec(self.right, vector, self.modulus), self.modulus)

    def materialize(self) -> Matrix:
        return tuple(tuple(self.entry(i, j) for j in range(self.dimension))
                     for i in range(self.dimension))


def naive_product(a: Matrix, b: Matrix, modulus: int) -> Matrix:
    """Independent conventional reference: compute every entry of AB."""
    n = len(a)
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(n)) % modulus
                       for j in range(n)) for i in range(n))