"""GEOMETRY-FIRST-003: sparse algebraic discovery with an explicit trust boundary.

Unqualified samples produce hypotheses, NEVER executable shortcuts. A separately
provided symbolic polynomial Ground definition can be checked by exact
coefficient identities to certify navigation *within that declared model*;
this does not establish that an unobserved physical system obeys the model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .affine import ModularAffineMap
from .polynomial_lift import (
    MAX_DEGREE, PolynomialLiftError, _eval, _fingerprint, _integer,
    _monomials, _prime, _rank, _solve,
)

Monomial = tuple[int, int]
Poly = tuple[tuple[Monomial, int], ...]


def _state(value: int, modulus: int) -> tuple[int, int]:
    _integer(value, "state")
    if value >= modulus * modulus:
        raise PolynomialLiftError("state exceeds declared coordinate chart")
    return divmod(value, modulus)


def _normalize(entries: Sequence[tuple[Monomial, int]], modulus: int,
               degree: int) -> Poly:
    if isinstance(entries, (str, bytes)):
        raise PolynomialLiftError("symbolic polynomial requires terms")
    coefficients: dict[Monomial, int] = {}
    try:
        terms = tuple(entries)
    except TypeError as exc:
        raise PolynomialLiftError("symbolic polynomial requires finite terms") from exc
    if len(terms) > 64:
        raise PolynomialLiftError("symbolic polynomial exceeds term budget")
    for term in terms:
        if not isinstance(term, (tuple, list)) or len(term) != 2:
            raise PolynomialLiftError("symbolic polynomial term must be (monomial, coefficient)")
        mon, value = term
        if not isinstance(mon, (tuple, list)) or len(mon) != 2:
            raise PolynomialLiftError("monomial must have two exponents")
        a, b = mon
        _integer(a, "x exponent")
        _integer(b, "y exponent")
        if a + b > degree or a >= modulus or b >= modulus:
            raise PolynomialLiftError("term is outside declared polynomial degree and field")
        if not isinstance(value, int) or isinstance(value, bool):
            raise PolynomialLiftError("coefficient must be an exact integer")
        exponent = (a, b)
        coefficients[exponent] = (coefficients.get(exponent, 0) + value) % modulus
    return tuple(sorted((mon, val) for mon, val in coefficients.items() if val))


def _poly_add(left: dict[Monomial, int], right: dict[Monomial, int], p: int) -> dict[Monomial, int]:
    result = dict(left)
    for mon, value in right.items():
        total = (result.get(mon, 0) + value) % p
        if total:
            result[mon] = total
        else:
            result.pop(mon, None)
    return result


def _poly_mul(left: dict[Monomial, int], right: dict[Monomial, int],
              p: int, cap: int) -> dict[Monomial, int]:
    result: dict[Monomial, int] = {}
    for (a, b), va in left.items():
        for (c, d), vb in right.items():
            mon = (a + c, b + d)
            if sum(mon) > cap or mon[0] >= p or mon[1] >= p:
                raise PolynomialLiftError("symbolic feature closure exceeds allowed polynomial representation")
            coefficient = (result.get(mon, 0) + va * vb) % p
            if coefficient:
                result[mon] = coefficient
            else:
                result.pop(mon, None)
    return result


def _poly_pow(base: dict[Monomial, int], exponent: int, p: int,
              cap: int) -> dict[Monomial, int]:
    result = {(0, 0): 1}
    for _ in range(exponent):
        result = _poly_mul(result, base, p, cap)
    return result


def _composition(monomial: Monomial, x_next: Poly, y_next: Poly,
                 p: int, cap: int) -> dict[Monomial, int]:
    left = _poly_pow(dict(x_next), monomial[0], p, cap)
    right = _poly_pow(dict(y_next), monomial[1], p, cap)
    return _poly_mul(left, right, p, cap)


@dataclass(frozen=True)
class SparseTransitionObservations:
    """Partial table; revision/source labels are caller claims, not authentication."""
    modulus: int
    action: str
    edges: tuple[tuple[int, int], ...]
    source: str = "synthetic"
    revision: str = "v1"
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        _prime(self.modulus)
        if not all(isinstance(value, str) and value and len(value) <= 128
                   for value in (self.action, self.source, self.revision)):
            raise PolynomialLiftError("action/source/revision must be bounded identifiers")
        try:
            edges = tuple(tuple(pair) for pair in self.edges)
        except (TypeError, ValueError) as exc:
            raise PolynomialLiftError("edges must be (source,target) pairs") from exc
        if not edges or len(edges) > self.modulus * self.modulus or any(len(e) != 2 for e in edges):
            raise PolynomialLiftError("invalid partial observation count or shape")
        for start, end in edges:
            _state(start, self.modulus)
            _state(end, self.modulus)
        sources = [start for start, _ in edges]
        if len(set(sources)) != len(sources):
            raise PolynomialLiftError("duplicate observation source (even if targets agree)")
        ordered = tuple(sorted(edges))
        object.__setattr__(self, "edges", ordered)
        object.__setattr__(self, "fingerprint", _fingerprint({
            "format": "VGI-SparseTransitionObservations-1",
            "modulus": self.modulus, "action": self.action, "source": self.source,
            "revision": self.revision, "edges": ordered,
        }))


@dataclass(frozen=True)
class SparsePolynomialHypothesis:
    """Interpolation result without authority to navigate unknown transitions."""
    observations: SparseTransitionObservations
    degree: int
    fit_states: tuple[int, ...]
    heldout_states: tuple[int, ...]
    x_next: Poly
    y_next: Poly
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        degree = _integer(self.degree, "degree", 1)
        if degree >= self.observations.modulus:
            raise PolynomialLiftError("degree exceeds finite-field representation")
        basis = _monomials(degree)
        known = dict(self.observations.edges)
        if (len(self.fit_states) != len(basis) or len(set(self.fit_states)) != len(basis)
            or any(s not in known for s in self.fit_states)
            or set(self.fit_states) & set(self.heldout_states)
            or set(self.heldout_states) != set(known) - set(self.fit_states)):
            raise PolynomialLiftError("invalid independent fitting/held-out sample split")
        fit_rows = [tuple(_eval(m, *_state(s, self.observations.modulus),
                                self.observations.modulus) for m in basis)
                    for s in self.fit_states]
        if _rank(fit_rows, self.observations.modulus) != len(basis):
            raise PolynomialLiftError("fit samples fail the required full rank")
        for poly in (self.x_next, self.y_next):
            if _normalize(poly, self.observations.modulus, self.degree) != poly:
                raise PolynomialLiftError("noncanonical hypothesis polynomial")
        for source, target in self.observations.edges:
            x, y = _state(source, self.observations.modulus)
            actual = _state(target, self.observations.modulus)
            expected = tuple(sum(coef * _eval(m, x, y, self.observations.modulus)
                                 for m, coef in poly) % self.observations.modulus
                             for poly in (self.x_next, self.y_next))
            if expected != actual:
                raise PolynomialLiftError(f"observed counterexample at state {source}")
        object.__setattr__(self, "fingerprint", _fingerprint({
            "format": "VGI-SparsePolynomialHypothesis-1",
            "observations": self.observations.fingerprint, "degree": self.degree,
            "fit_states": self.fit_states, "heldout_states": self.heldout_states,
            "x_next": self.x_next, "y_next": self.y_next,
        }))

    @property
    def status(self) -> str:
        return "observational_hypothesis_unverified_outside_samples"

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "VGI-SparsePolynomialHypothesis-1",
            "status": self.status,
            "hypothesis_fingerprint": self.fingerprint,
            "observation_fingerprint": self.observations.fingerprint,
            "observed_edges": len(self.observations.edges),
            "independent_fit_states": list(self.fit_states),
            "heldout_states": list(self.heldout_states),
            "degree": self.degree,
            "x_next": [[list(mon), value] for mon, value in self.x_next],
            "y_next": [[list(mon), value] for mon, value in self.y_next],
            "navigation_admitted": False,
        }

    def state_at(self, start: int, tick: int) -> None:
        raise PolynomialLiftError("sparse observations alone do not authorize logical-time navigation")


def propose_rank_probes(modulus: int, degree: int,
                        observed_sources: Sequence[int] = ()) -> tuple[int, ...]:
    """Minimal rank-completing queries for a total-degree polynomial basis.

    This is a deterministic exact-linear-algebra policy, not expected information
    gain under an uncalibrated distribution. Scans only a bounded d-by-d grid.
    """
    p = _prime(modulus)
    d = _integer(degree, "maximum polynomial degree", 1)
    if d > MAX_DEGREE or d >= p:
        raise PolynomialLiftError("probe degree outside supported finite-field basis")
    basis = _monomials(d)
    seen: set[int] = set()
    rows: list[tuple[int, ...]] = []
    for s in observed_sources:
        x, y = _state(s, p)
        if s in seen:
            raise PolynomialLiftError("duplicate observed query state")
        seen.add(s)
        row = tuple(_eval(m, x, y, p) for m in basis)
        if _rank([*rows, row], p) > len(rows):
            rows.append(row)
    output: list[int] = []
    for x in range(d + 1):
        for y in range(d + 1):
            s = x * p + y
            if s in seen:
                continue
            row = tuple(_eval(m, x, y, p) for m in basis)
            if _rank([*rows, row], p) > len(rows):
                output.append(s)
                rows.append(row)
            if len(rows) == len(basis):
                return tuple(output)
    if len(rows) != len(basis):
        raise PolynomialLiftError("declared probe search did not span basis")
    return tuple(output)


def fit_sparse_hypothesis(observations: SparseTransitionObservations,
                          degree: int = 2) -> SparsePolynomialHypothesis:
    """Fit using independent samples, reject any contradicting observed edge."""
    if not isinstance(observations, SparseTransitionObservations):
        raise PolynomialLiftError("fit requires typed partial observations")
    p = observations.modulus
    basis = _monomials(_integer(degree, "degree", 1))
    if degree >= p:
        raise PolynomialLiftError("degree must be less than field modulus")
    fits: list[int] = []
    rows: list[tuple[int, ...]] = []
    known = dict(observations.edges)
    for s in sorted(known):
        x, y = _state(s, p)
        row = tuple(_eval(m, x, y, p) for m in basis)
        if _rank([*rows, row], p) > len(rows):
            fits.append(s)
            rows.append(row)
        if len(fits) == len(basis):
            break
    if len(fits) < len(basis):
        raise PolynomialLiftError("insufficient independent observations to fit degree")
    targets = [_state(known[s], p) for s in fits]
    x_coeffs = _solve(rows, [x for x, _ in targets], p)
    y_coeffs = _solve(rows, [y for _, y in targets], p)
    return SparsePolynomialHypothesis(
        observations, degree, tuple(fits),
        tuple(s for s in sorted(known) if s not in set(fits)),
        _normalize(tuple(zip(basis, x_coeffs)), p, degree),
        _normalize(tuple(zip(basis, y_coeffs)), p, degree),
    )


@dataclass(frozen=True)
class DeclaredPolynomialGround:
    """Mathematical law DEFINED by explicit polynomials; not a sensor receipt.

    A declaration is its own mathematical authority for its *formal model*.
    It makes no assertion that an unobserved external system follows it.
    """
    modulus: int
    action: str
    degree: int
    x_next: Poly
    y_next: Poly
    model_id: str = "synthetic-law"
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        p = _prime(self.modulus)
        degree = _integer(self.degree, "degree", 1)
        if degree >= p or degree > MAX_DEGREE:
            raise PolynomialLiftError("symbolic law degree outside finite-field contract")
        if not isinstance(self.action, str) or not self.action:
            raise PolynomialLiftError("symbolic law action must be nonempty")
        if not isinstance(self.model_id, str) or not self.model_id or len(self.model_id) > 128:
            raise PolynomialLiftError("invalid model identity")
        for poly in (self.x_next, self.y_next):
            if poly != _normalize(poly, p, degree):
                raise PolynomialLiftError("ground law must be a canonical polynomial")
        object.__setattr__(self, "fingerprint", _fingerprint({
            "format": "VGI-DeclaredPolynomialGround-1", "modulus": p,
            "action": self.action, "degree": degree, "x_next": self.x_next,
            "y_next": self.y_next, "model_id": self.model_id,
        }))

    def step(self, state: int) -> int:
        x, y = _state(state, self.modulus)
        new_x, new_y = (sum(c * _eval(m, x, y, self.modulus) for m, c in poly)
                        % self.modulus for poly in (self.x_next, self.y_next))
        return new_x * self.modulus + new_y


def _construct_lift(ground: DeclaredPolynomialGround, max_feature_degree: int,
                    max_features: int) -> tuple[tuple[Monomial, ...], ModularAffineMap]:
    p = ground.modulus
    cap = _integer(max_feature_degree, "feature degree", 1)
    if cap >= p or cap > 9:
        raise PolynomialLiftError("feature degree exceeds sound symbolic polynomial budget")
    max_features = _integer(max_features, "maximum features", 2)
    if max_features > 32:
        raise PolynomialLiftError("maximum features exceeds declared audit budget")
    features: set[Monomial] = {(1, 0), (0, 1)}
    equations: dict[Monomial, dict[Monomial, int]] = {}
    for _ in range(max_features + 1):
        new_features: set[Monomial] = set()
        for mon in sorted(features):
            if mon not in equations:
                symbolic = _composition(mon, ground.x_next, ground.y_next, p, cap)
                equations[mon] = symbolic
                new_features.update(m for m in symbolic if m != (0, 0))
        discovered = new_features - features
        if not discovered:
            break
        features.update(discovered)
        if len(features) > max_features:
            raise PolynomialLiftError("feature closure exceeds declared dimension")
    else:
        raise PolynomialLiftError("feature closure did not terminate")
    chosen = ((1, 0), (0, 1)) + tuple(sorted(features - {(1, 0), (0, 1)}))
    matrix = tuple(tuple(equations[mon].get(other, 0) for other in chosen)
                   for mon in chosen)
    offset = tuple(equations[mon].get((0, 0), 0) for mon in chosen)
    return chosen, ModularAffineMap(p, matrix, offset)


@dataclass(frozen=True)
class ModelCertifiedSparseNavigation:
    """Exact symbolic identity proof, scoped to a declared mathematical model."""
    ground: DeclaredPolynomialGround
    hypothesis: SparsePolynomialHypothesis
    max_feature_degree: int
    features: tuple[Monomial, ...]
    transform: ModularAffineMap
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.ground, DeclaredPolynomialGround) or not isinstance(self.hypothesis, SparsePolynomialHypothesis):
            raise PolynomialLiftError("certificate requires a declared model and hypothesis")
        if self.hypothesis.observations.modulus != self.ground.modulus or self.hypothesis.observations.action != self.ground.action:
            raise PolynomialLiftError("observed and declared Ground identity mismatch")
        if self.hypothesis.degree != self.ground.degree:
            raise PolynomialLiftError("model degree and fitted probe basis disagree")
        if (self.hypothesis.x_next, self.hypothesis.y_next) != (self.ground.x_next, self.ground.y_next):
            raise PolynomialLiftError("observed polynomial contradicts declared symbolic Ground")
        for source, target in self.hypothesis.observations.edges:
            if self.ground.step(source) != target:
                raise PolynomialLiftError("an observed transition contradicts the declared model")
        expected_features, expected_transform = _construct_lift(self.ground, self.max_feature_degree, 32)
        if self.features != expected_features or not isinstance(self.transform, ModularAffineMap) or self.transform.to_dict() != expected_transform.to_dict():
            raise PolynomialLiftError("supplied lift fails exact symbolic coefficient verification")
        object.__setattr__(self, "fingerprint", _fingerprint({
            "format": "VGI-SymbolicModelLiftCertificate-1",
            "model": self.ground.fingerprint,
            "observations": self.hypothesis.observations.fingerprint,
            "hypothesis": self.hypothesis.fingerprint,
            "features": self.features,
            "transform": self.transform.to_dict(),
            "trust_scope": "formal_declared_ground_only",
        }))

    @property
    def status(self) -> str:
        return "certified_for_declared_model_not_external_ground"

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "VGI-SymbolicModelLiftCertificate-1",
            "status": self.status,
            "certificate_fingerprint": self.fingerprint,
            "model_fingerprint": self.ground.fingerprint,
            "observations_fingerprint": self.hypothesis.observations.fingerprint,
            "observation_source": self.hypothesis.observations.source,
            "observation_revision": self.hypothesis.observations.revision,
            "observed_edges": len(self.hypothesis.observations.edges),
            "fit_states": list(self.hypothesis.fit_states),
            "heldout_states": list(self.hypothesis.heldout_states),
            "features": [list(mon) for mon in self.features],
            "transform": self.transform.to_dict(),
            "proof_method": "exact_symbolic_polynomial_coefficient_identity",
            "navigation_admitted_for_declared_model": True,
            "navigation_admitted_for_external_system": False,
        }

    def state_at(self, start: int, tick: int) -> "SparseNavigationResult":
        x, y = _state(start, self.ground.modulus)
        _integer(tick, "logical tick")
        p = self.ground.modulus
        lifted = tuple(_eval(m, x, y, p) for m in self.features)
        powered = self.transform.power(lifted, tick)
        ox, oy = powered[:2]
        # Check that the returned point lies on the declared embedding.
        if powered != tuple(_eval(m, ox, oy, p) for m in self.features):
            raise PolynomialLiftError("navigation escaped the certified lifted representation")
        return SparseNavigationResult(
            state=ox * p + oy, coordinates=(ox, oy), logical_tick=tick,
            exponent_bits=tick.bit_length(), observed_edges=len(self.hypothesis.observations.edges),
            declared_ground_fingerprint=self.ground.fingerprint,
            observation_fingerprint=self.hypothesis.observations.fingerprint,
            certificate_fingerprint=self.fingerprint,
        )


@dataclass(frozen=True)
class SparseNavigationResult:
    state: int
    coordinates: tuple[int, int]
    logical_tick: int
    exponent_bits: int
    observed_edges: int
    declared_ground_fingerprint: str
    observation_fingerprint: str
    certificate_fingerprint: str
    materialized_intermediate_states: int = 0
    trust_scope: str = "formal_declared_ground_only"

    def to_dict(self) -> dict[str, object]:
        return {"format": "VGI-SparseNavigationResult-1",
                "state": self.state, "coordinates": list(self.coordinates),
                "logical_tick": self.logical_tick, "exponent_bits": self.exponent_bits,
                "observed_edges": self.observed_edges,
                "materialized_intermediate_states": self.materialized_intermediate_states,
                "declared_ground_fingerprint": self.declared_ground_fingerprint,
                "observation_fingerprint": self.observation_fingerprint,
                "certificate_fingerprint": self.certificate_fingerprint,
                "trust_scope": self.trust_scope}


def certify_declared_model(hypothesis: SparsePolynomialHypothesis,
                           ground: DeclaredPolynomialGround,
                           max_feature_degree: int = 3) -> ModelCertifiedSparseNavigation:
    """Exact symbolic certificate of a model, NOT a certification of reality."""
    if not isinstance(hypothesis, SparsePolynomialHypothesis) or not isinstance(ground, DeclaredPolynomialGround):
        raise PolynomialLiftError("expected typed hypothesis and declared Ground")
    features, transform = _construct_lift(ground, max_feature_degree, 32)
    return ModelCertifiedSparseNavigation(ground, hypothesis, max_feature_degree,
                                          features, transform)


__all__ = [
    "SparseTransitionObservations", "SparsePolynomialHypothesis",
    "DeclaredPolynomialGround", "ModelCertifiedSparseNavigation",
    "SparseNavigationResult", "propose_rank_probes", "fit_sparse_hypothesis",
    "certify_declared_model",
]