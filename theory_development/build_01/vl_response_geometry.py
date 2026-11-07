#!/usr/bin/env python3
"""A small, reproducible prototype for observer-dependent response geometry.

This experiment deliberately separates:
  1. algebraic identity (canonical codonic expression + SHA-256 identifier),
  2. observer response (values under a fixed family of probes), and
  3. response geometry (a point on S^3 derived from four response coefficients).

The S^3 point is NOT the Virtual Layer's existing quaternion address q(f).
It is a second, observer-dependent representation, q_resp. Its antipode is
kept distinct: q_resp and -q_resp mean opposite response directions.

Only the standard library is required.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Callable, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class OpSpec:
    arity: int
    fn: Callable[..., float]
    commutative: bool = False
    identity: float | None = None


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple["Expr", ...] = ()
    value: float | str | None = None

    @staticmethod
    def var(name: str = "x") -> "Expr":
        return Expr("$var", value=name)

    @staticmethod
    def const(value: float) -> "Expr":
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("Constants must be finite real numbers")
        return Expr("$const", value=value)

    @staticmethod
    def call(op: str, *args: "Expr") -> "Expr":
        return Expr(op, tuple(args))


def default_registry() -> dict[str, OpSpec]:
    """Local, editable codon map for this experiment.

    It follows the user's explicitly stated current example: ad=addition,
    mx=multiplication. This is a local test registry, not a claim that the
    uploaded v3.0 registry has identical symbol assignments.
    """
    return {
        "ad": OpSpec(2, lambda a, b: a + b, commutative=True, identity=0.0),
        "mx": OpSpec(2, lambda a, b: a * b, commutative=True, identity=1.0),
        "su": OpSpec(2, lambda a, b: a - b),
        "dv": OpSpec(2, lambda a, b: a / b),
        "sq": OpSpec(1, lambda a: a * a),
        "ng": OpSpec(1, lambda a: -a),
        "sn": OpSpec(1, math.sin),
        "cs": OpSpec(1, math.cos),
    }


def _const_equal(expr: Expr, value: float) -> bool:
    return expr.op == "$const" and float(expr.value) == float(value)


def canonical_tree(expr: Expr, registry: Mapping[str, OpSpec]) -> tuple:
    """Return a canonical, JSON-serializable tree using conservative rewrites.

    Applied rules:
      - sort arguments of explicitly commutative operations;
      - remove the declared identity from ad and mx;
      - remove 0 from the right of subtraction and 1 from the right of division.

    No distributivity, associativity flattening, floating-point reassociation,
    or approximate equivalence is assumed.
    """
    if expr.op == "$var":
        if not isinstance(expr.value, str) or not expr.value:
            raise ValueError("Variable names must be non-empty strings")
        return ("var", expr.value)
    if expr.op == "$const":
        value = float(expr.value)
        if not math.isfinite(value):
            raise ValueError("Constants must be finite")
        return ("const", value.hex())

    if expr.op not in registry:
        raise KeyError(f"Unknown codon: {expr.op}")
    spec = registry[expr.op]
    if len(expr.args) != spec.arity:
        raise ValueError(f"{expr.op} expects {spec.arity} arguments, got {len(expr.args)}")

    children = [canonical_tree(a, registry) for a in expr.args]
    child_exprs = list(expr.args)

    # Identity reductions are deliberately exact and narrowly scoped.
    if expr.op in ("ad", "mx") and spec.identity is not None:
        kept = [
            (tree, child)
            for tree, child in zip(children, child_exprs)
            if not _const_equal(child, spec.identity)
        ]
        if len(kept) == 1:
            return kept[0][0]
        if len(kept) == 0:
            return ("const", float(spec.identity).hex())
        children = [item[0] for item in kept]

    if expr.op == "su" and _const_equal(child_exprs[1], 0.0):
        return children[0]
    if expr.op == "dv" and _const_equal(child_exprs[1], 1.0):
        return children[0]

    if spec.commutative:
        children.sort(key=lambda item: json.dumps(item, separators=(",", ":"), sort_keys=True))

    return ("call", expr.op, tuple(children))


def canonical_json(expr: Expr, registry: Mapping[str, OpSpec]) -> str:
    return json.dumps(canonical_tree(expr, registry), separators=(",", ":"), sort_keys=True)


def seed_identity(expr: Expr, registry: Mapping[str, OpSpec]) -> dict[str, str]:
    """A reproducible identity address; it is not used as a distance metric."""
    canonical = canonical_json(expr, registry)
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    return {"canonical": canonical, "sha256": digest, "sigma64": digest[:16]}


def evaluate(expr: Expr, x: float, registry: Mapping[str, OpSpec]) -> float:
    if expr.op == "$var":
        if expr.value != "x":
            raise ValueError(f"Only variable x is bound in this prototype, got {expr.value!r}")
        return float(x)
    if expr.op == "$const":
        return float(expr.value)
    if expr.op not in registry:
        raise KeyError(f"Unknown codon: {expr.op}")
    spec = registry[expr.op]
    if len(expr.args) != spec.arity:
        raise ValueError(f"{expr.op} expects {spec.arity} arguments, got {len(expr.args)}")
    args = [evaluate(a, x, registry) for a in expr.args]
    try:
        value = float(spec.fn(*args))
    except (ArithmeticError, OverflowError, ValueError) as exc:
        raise ValueError(f"Evaluation failed for codon {expr.op}: {exc}") from exc
    if not math.isfinite(value):
        raise ValueError(f"Non-finite output from codon {expr.op}")
    return value


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def norm(a: Sequence[float]) -> float:
    return math.sqrt(dot(a, a))


def normalize(a: Sequence[float], eps: float = 1e-14) -> tuple[float, ...] | None:
    n = norm(a)
    if n <= eps:
        return None
    return tuple(x / n for x in a)


def _orthonormal_probe_basis(xs: Sequence[float]) -> tuple[tuple[float, ...], ...]:
    """Construct DC, linear, curvature, and oscillatory probe directions."""
    raw = [
        [1.0 for _ in xs],
        [x for x in xs],
        [x * x for x in xs],
        [math.sin(2.0 * math.pi * x) for x in xs],
    ]
    basis: list[tuple[float, ...]] = []
    for vector in raw:
        residual = list(vector)
        for q in basis:
            projection = dot(residual, q)
            residual = [v - projection * qi for v, qi in zip(residual, q)]
        qv = normalize(residual)
        if qv is None:
            raise RuntimeError("Probe basis became linearly dependent")
        basis.append(qv)
    return tuple(basis)


@dataclass(frozen=True)
class Observer:
    name: str
    matrix: tuple[tuple[float, float, float, float], ...]

    @staticmethod
    def diagonal(name: str, scales: Sequence[float]) -> "Observer":
        if len(scales) != 4 or any(not math.isfinite(float(s)) for s in scales):
            raise ValueError("Observer needs four finite feature scales")
        return Observer(name, tuple(
            tuple(float(scales[i]) if i == j else 0.0 for j in range(4))
            for i in range(4)
        ))

    @staticmethod
    def identity(name: str = "balanced") -> "Observer":
        return Observer.diagonal(name, (1.0, 1.0, 1.0, 1.0))

    def observe(self, features: Sequence[float]) -> tuple[float, ...]:
        if len(self.matrix) != 4 or any(len(row) != 4 for row in self.matrix):
            raise ValueError("Observer matrix must be 4x4")
        return tuple(dot(row, features) for row in self.matrix)


@dataclass(frozen=True)
class Response:
    features: tuple[float, float, float, float]
    residual_rms: float
    amplitude: float
    q_resp: tuple[float, float, float, float] | None


def response_signature(
    expr: Expr,
    observer: Observer,
    registry: Mapping[str, OpSpec] | None = None,
    n_probes: int = 129,
) -> Response:
    """Evaluate an expression under a fixed input probe family.

    The four response coefficients are projections onto an orthonormal probe
    basis: DC/mean, linear, curvature, and oscillatory. The residual RMS is
    retained so that the S^3 projection does not silently discard everything
    outside those four modes.
    """
    if n_probes < 9 or n_probes % 2 == 0:
        raise ValueError("n_probes must be odd and at least 9")
    registry = registry or default_registry()
    xs = tuple(-1.0 + 2.0 * i / (n_probes - 1) for i in range(n_probes))
    ys = tuple(evaluate(expr, x, registry) for x in xs)
    basis = _orthonormal_probe_basis(xs)
    coefficients = tuple(dot(ys, b) for b in basis)

    reconstruction = [0.0] * n_probes
    for coefficient, b in zip(coefficients, basis):
        reconstruction = [v + coefficient * bi for v, bi in zip(reconstruction, b)]
    residual_rms = math.sqrt(sum((y - yhat) ** 2 for y, yhat in zip(ys, reconstruction)) / n_probes)

    observed = observer.observe(coefficients)
    amplitude = norm(observed)
    q = normalize(observed)
    return Response(tuple(observed), residual_rms, amplitude, q)  # type: ignore[arg-type]


def s3_distance(q1: Sequence[float], q2: Sequence[float]) -> float:
    """Unit S^3 geodesic distance; deliberately does NOT identify q ~ -q."""
    if len(q1) != 4 or len(q2) != 4:
        raise ValueError("S^3 points must have four coordinates")
    n1, n2 = norm(q1), norm(q2)
    if abs(n1 - 1.0) > 1e-8 or abs(n2 - 1.0) > 1e-8:
        raise ValueError("Inputs must be unit vectors")
    cosine = max(-1.0, min(1.0, dot(q1, q2)))
    return math.acos(cosine)


def response_distance(a: Response, b: Response) -> float:
    """A simple augmented distance retaining both angle and amplitude."""
    if a.q_resp is None or b.q_resp is None:
        raise ValueError("Cannot compare a zero response direction")
    angular = s3_distance(a.q_resp, b.q_resp)
    radial = abs(math.log1p(a.amplitude) - math.log1p(b.amplitude))
    residual = abs(a.residual_rms - b.residual_rms)
    return math.sqrt(angular * angular + radial * radial + residual * residual)


def pairwise_rdm(responses: Sequence[Response]) -> tuple[tuple[float, ...], ...]:
    matrix = []
    for a in responses:
        row = []
        for b in responses:
            row.append(response_distance(a, b))
        matrix.append(tuple(row))
    return tuple(matrix)


def _rankdata(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda p: p[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        average_rank = ((i + 1) + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = average_rank
        i = j
    return ranks


def _pearson(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    da, db = [x - ma for x in a], [y - mb for y in b]
    denom = norm(da) * norm(db)
    if denom <= 1e-14:
        return None
    return dot(da, db) / denom


def rdm_rank_correlation(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> float | None:
    """Spearman correlation between upper-triangle entries of two RDMs."""
    if len(a) != len(b) or any(len(row) != len(a) for row in a) or any(len(row) != len(b) for row in b):
        raise ValueError("RDMs must be square and the same size")
    av, bv = [], []
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            av.append(float(a[i][j]))
            bv.append(float(b[i][j]))
    return _pearson(_rankdata(av), _rankdata(bv))


def demo_report() -> dict:
    reg = default_registry()
    x = Expr.var()
    c = Expr.const
    call = Expr.call
    pi2 = Expr.const(2.0 * math.pi)
    sinusoid = call("sn", call("mx", pi2, x))
    square = call("sq", x)
    mixed_plus = call("ad", square, call("mx", c(0.4), sinusoid))
    mixed_minus = call("su", square, call("mx", c(0.4), sinusoid))

    expressions = {
        "identity_x": x,
        "add_zero": call("ad", x, c(0.0)),
        "multiply_one": call("mx", x, c(1.0)),
        "negated_x": call("su", c(0.0), x),
        "square": square,
        "sin_2pi_x": sinusoid,
        "mixed_plus": mixed_plus,
        "mixed_minus": mixed_minus,
    }

    observers = {
        "balanced": Observer.identity("balanced"),
        "oscillation_sensitive": Observer.diagonal("oscillation_sensitive", (1.0, 1.0, 1.0, 4.0)),
        "polynomial_sensitive": Observer.diagonal("polynomial_sensitive", (1.0, 1.0, 3.0, 0.25)),
    }

    per_observer = {}
    for oname, observer in observers.items():
        responses = {name: response_signature(expr, observer, reg) for name, expr in expressions.items()}
        names = list(expressions)
        rdm = pairwise_rdm([responses[name] for name in names])
        per_observer[oname] = {
            "feature_names": ["dc", "linear", "curvature", "oscillatory"],
            "responses": {
                name: {
                    "features": list(r.features),
                    "amplitude": r.amplitude,
                    "residual_rms": r.residual_rms,
                    "q_resp": list(r.q_resp) if r.q_resp is not None else None,
                }
                for name, r in responses.items()
            },
            "rdm": [list(row) for row in rdm],
        }

    # Identifier/geometry separation: aliases reduce to the same canonical tree.
    identity_ids = [seed_identity(expressions[n], reg)["sigma64"] for n in ("identity_x", "add_zero", "multiply_one")]

    balanced = per_observer["balanced"]["rdm"]
    osc = per_observer["oscillation_sensitive"]["rdm"]
    poly = per_observer["polynomial_sensitive"]["rdm"]

    # Explicit antipode control using identity and its negation.
    ra = response_signature(expressions["identity_x"], observers["balanced"], reg)
    rb = response_signature(expressions["negated_x"], observers["balanced"], reg)
    antipodal_distance = s3_distance(ra.q_resp, rb.q_resp) if ra.q_resp and rb.q_resp else None

    return {
        "experiment": "VL Observer-Dependent Response Geometry / prototype 0.1",
        "important_scope": [
            "q_resp is not the existing Virtual Layer quaternion address q(f).",
            "SHA-256 sigma64 is recorded as identity only; it is not used for distance.",
            "The S^3 geometry is an observer-dependent projection of four response coefficients.",
            "The antipode q_resp -> -q_resp remains distinct; this is S^3 response direction, not SO(3) rotation equivalence."
        ],
        "local_codon_map": {"ad": "addition", "mx": "multiplication", "su": "subtraction", "dv": "division", "sq": "square", "ng": "negation", "sn": "sine", "cs": "cosine"},
        "identity_alias_sigma64": identity_ids,
        "identity_aliases_match": len(set(identity_ids)) == 1,
        "identity_vs_negation_antipodal_distance_radians": antipodal_distance,
        "observer_rdm_rank_correlations": {
            "balanced_vs_oscillation_sensitive": rdm_rank_correlation(balanced, osc),
            "balanced_vs_polynomial_sensitive": rdm_rank_correlation(balanced, poly),
            "oscillation_vs_polynomial_sensitive": rdm_rank_correlation(osc, poly),
        },
        "observers": per_observer,
        "interpretation_limit": "Synthetic scalar functions and four hand-defined response modes only; no biological or emotional claim is tested.",
    }


if __name__ == "__main__":
    print(json.dumps(demo_report(), indent=2, sort_keys=True))
