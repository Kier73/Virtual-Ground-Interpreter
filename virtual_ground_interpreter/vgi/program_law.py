"""GEOMETRY-FIRST-004: structural law extraction from a bounded executable DSL.

Only the accepted Python AST subset has semantics here. No user-supplied source is
executed or evaluated. Exact polynomial identities certify navigation *within*
this DSL's mathematical model, not arbitrary Python or an external process.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from hashlib import sha256

from .affine import ModularAffineMap
from .polynomial_lift import PolynomialLiftError, _eval, _fingerprint, _integer, _prime
from .sparse_polynomial import (
    DeclaredPolynomialGround, SparseTransitionObservations,
    _construct_lift, _normalize, _poly_add, _poly_mul, _poly_pow,
)

Monomial = tuple[int, int]
Polynomial = dict[Monomial, int]

MAX_SOURCE_BYTES = 8192
MAX_AST_NODES = 256
MAX_STATEMENTS = 48
MAX_POWER = 6
MAX_EXPRESSION_DEGREE = 9
MAX_COEFFICIENT = 10**12


def _literal(node: ast.AST, *, nonnegative: bool = False) -> int:
    if not isinstance(node, ast.Constant) or type(node.value) is not int:
        raise PolynomialLiftError("only literal integer constants are allowed here")
    value = node.value
    if abs(value) > MAX_COEFFICIENT or (nonnegative and value < 0):
        raise PolynomialLiftError("integer literal is outside the bounded program grammar")
    return value


def _neg(poly: Polynomial, p: int) -> Polynomial:
    return {m: (-c) % p for m, c in poly.items() if (-c) % p}


def _expr(node: ast.AST, env: dict[str, Polynomial], p: int,
          expression_degree: int) -> Polynomial:
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        if node.id not in env:
            raise PolynomialLiftError(f"unbound or prohibited name: {node.id}")
        return dict(env[node.id])
    if isinstance(node, ast.Constant):
        return {(0, 0): v} if (v := _literal(node) % p) else {}
    if isinstance(node, ast.UnaryOp):
        child = _expr(node.operand, env, p, expression_degree)
        if isinstance(node.op, ast.UAdd):
            return child
        if isinstance(node.op, ast.USub):
            return _neg(child, p)
        raise PolynomialLiftError("only unary plus or minus is allowed")
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            exponent = _literal(node.right, nonnegative=True)
            if exponent > MAX_POWER:
                raise PolynomialLiftError("power exponent exceeds bounded grammar")
            return _poly_pow(_expr(node.left, env, p, expression_degree),
                             exponent, p, expression_degree)
        if isinstance(node.op, ast.Mod):
            # Python a % p and finite-field reduction agree for strict integer p.
            if _literal(node.right) != p:
                raise PolynomialLiftError("modulus must equal the declared finite-field prime")
            return _expr(node.left, env, p, expression_degree)
        left = _expr(node.left, env, p, expression_degree)
        right = _expr(node.right, env, p, expression_degree)
        if isinstance(node.op, ast.Add):
            return _poly_add(left, right, p)
        if isinstance(node.op, ast.Sub):
            return _poly_add(left, _neg(right, p), p)
        if isinstance(node.op, ast.Mult):
            return _poly_mul(left, right, p, expression_degree)
        raise PolynomialLiftError("unsupported binary operator")
    raise PolynomialLiftError(f"unsupported expression construct: {type(node).__name__}")


def _target(node: ast.AST) -> str:
    if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Store):
        raise PolynomialLiftError("assignment targets must be plain local names")
    if node.id.startswith("_") or len(node.id) > 48:
        raise PolynomialLiftError("private or oversized local names are forbidden")
    return node.id


def _parse(source: str, p: int) -> tuple[tuple[tuple[Monomial, int], ...],
                                         tuple[tuple[Monomial, int], ...], int, str]:
    if not isinstance(source, str) or not source or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise PolynomialLiftError("program source is empty or exceeds byte budget")
    try:
        module = ast.parse(source, mode="exec")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise PolynomialLiftError("program source cannot be parsed as bounded Python") from exc
    if sum(1 for _ in ast.walk(module)) > MAX_AST_NODES:
        raise PolynomialLiftError("program AST exceeds bounded node budget")
    if len(module.body) != 1 or not isinstance(module.body[0], ast.FunctionDef):
        raise PolynomialLiftError("source must contain exactly one function definition")
    fn = module.body[0]
    args = fn.args
    if (fn.name != "advance" or fn.decorator_list or getattr(fn, "type_params", ()) or fn.returns is not None
        or args.posonlyargs or args.kwonlyargs or args.defaults or args.kw_defaults
        or args.vararg or args.kwarg or len(args.args) != 2
        or [a.arg for a in args.args] != ["x", "y"]
        or any(a.annotation is not None for a in args.args)):
        raise PolynomialLiftError("expected undecorated def advance(x, y) with no annotations/defaults")
    if not fn.body or len(fn.body) > MAX_STATEMENTS or not isinstance(fn.body[-1], ast.Return):
        raise PolynomialLiftError("bounded program must end with a return")
    env: dict[str, Polynomial] = {"x": {(1, 0): 1}, "y": {(0, 1): 1}}
    for statement in fn.body[:-1]:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            raise PolynomialLiftError("only straight-line local assignments are supported")
        target = statement.targets[0]
        if isinstance(target, (ast.Tuple, ast.List)):
            if not isinstance(statement.value, (ast.Tuple, ast.List)) or len(target.elts) != len(statement.value.elts):
                raise PolynomialLiftError("parallel assignment requires equal-length literal tuple/list")
            names = tuple(_target(t) for t in target.elts)
            if len(names) != len(set(names)):
                raise PolynomialLiftError("duplicate parallel assignment target")
            # Compute all RHS values under the OLD environment, then publish.
            values = tuple(_expr(v, env, p, MAX_EXPRESSION_DEGREE)
                           for v in statement.value.elts)
            env.update(zip(names, values))
        else:
            name = _target(target)
            value = _expr(statement.value, env, p, MAX_EXPRESSION_DEGREE)
            env[name] = value
        if len(env) > 48:
            raise PolynomialLiftError("local variable budget exceeded")
    result = fn.body[-1].value
    if not isinstance(result, (ast.Tuple, ast.List)) or len(result.elts) != 2:
        raise PolynomialLiftError("advance must return an exact (x_next, y_next) tuple")
    polys = tuple(_expr(v, env, p, MAX_EXPRESSION_DEGREE) for v in result.elts)
    degree = max([1, *(sum(m) for poly in polys for m in poly)], default=1)
    # Reuse VGI's bounded 2-var finite-field polynomial model (max degree 3).
    if degree > 3:
        raise PolynomialLiftError("derived output law exceeds supported polynomial degree")
    return (_normalize(tuple(polys[0].items()), p, degree),
            _normalize(tuple(polys[1].items()), p, degree),
            degree,
            sha256(ast.dump(module, include_attributes=False).encode()).hexdigest())


@dataclass(frozen=True, slots=True)
class ExtractedProgramLaw:
    """A mathematical model derived from a source AST, not supplied coefficients."""
    source: str
    modulus: int
    action: str = "advance"
    source_digest: str = field(init=False)
    structure_digest: str = field(init=False)
    ground: DeclaredPolynomialGround = field(init=False)
    statement_count: int = field(init=False)

    def __post_init__(self) -> None:
        p = _prime(self.modulus)
        if not isinstance(self.action, str) or not self.action or len(self.action) > 128:
            raise PolynomialLiftError("invalid action identity")
        x_next, y_next, degree, parsed_digest = _parse(self.source, p)
        source_digest = sha256(self.source.encode("utf-8")).hexdigest()
        ground = DeclaredPolynomialGround(
            p, self.action, degree, x_next, y_next, model_id="ast:" + parsed_digest[:32],
        )
        object.__setattr__(self, "source_digest", source_digest)
        object.__setattr__(self, "structure_digest", parsed_digest)
        object.__setattr__(self, "ground", ground)
        object.__setattr__(self, "statement_count", len(ast.parse(self.source).body[0].body))

    def state_after_one(self, state: int) -> int:
        """Execute only the admitted, structurally interpreted formal law."""
        return self.ground.step(state)

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "VGI-ExtractedProgramLaw-1",
            "status": "derived_from_bounded_ast_subset",
            "source_digest": self.source_digest,
            "structure_digest": self.structure_digest,
            "model_fingerprint": self.ground.fingerprint,
            "modulus": self.modulus,
            "action": self.action,
            "degree": self.ground.degree,
            "x_next": [[list(m), c] for m, c in self.ground.x_next],
            "y_next": [[list(m), c] for m, c in self.ground.y_next],
            "statement_count": self.statement_count,
            "scope": "formal_bounded_program_semantics_only",
        }


@dataclass(frozen=True, slots=True)
class ProgramNavigationCertificate:
    """Exact coefficient closure certificate over the admissible program DSL."""
    law: ExtractedProgramLaw
    max_feature_degree: int
    features: tuple[Monomial, ...]
    transform: ModularAffineMap
    observations: SparseTransitionObservations | None = None
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.law, ExtractedProgramLaw):
            raise PolynomialLiftError("program certificate requires extracted law")
        # Independently reconstruct the law from its source; do not trust a supplied model.
        rederived = ExtractedProgramLaw(self.law.source, self.law.modulus, self.law.action)
        if (rederived.source_digest != self.law.source_digest
            or rederived.ground.fingerprint != self.law.ground.fingerprint):
            raise PolynomialLiftError("compiled law does not match the exact source")
        expected_features, expected_transform = _construct_lift(
            rederived.ground, self.max_feature_degree, 32,
        )
        if (self.features != expected_features or not isinstance(self.transform, ModularAffineMap)
            or self.transform.to_dict() != expected_transform.to_dict()):
            raise PolynomialLiftError("supplied affine lift fails exact symbolic coefficient verification")
        if self.observations is not None:
            obs = self.observations
            if (not isinstance(obs, SparseTransitionObservations)
                or obs.modulus != self.law.modulus or obs.action != self.law.action):
                raise PolynomialLiftError("observations target a different program model")
            for s, t in obs.edges:
                if rederived.state_after_one(s) != t:
                    raise PolynomialLiftError("observed execution contradicts program semantics")
        object.__setattr__(self, "fingerprint", _fingerprint({
            "format": "VGI-ProgramNavigationCertificate-1",
            "source_digest": self.law.source_digest,
            "structural_digest": self.law.structure_digest,
            "model": self.law.ground.fingerprint,
            "features": self.features,
            "transform": self.transform.to_dict(),
            "observations": self.observations.fingerprint if self.observations else None,
            "trust_scope": "formal_bounded_program_semantics_only",
        }))

    def state_at(self, start: int, tick: int) -> "ProgramNavigationResult":
        _integer(start, "state")
        _integer(tick, "logical tick")
        p = self.law.modulus
        if start >= p * p:
            raise PolynomialLiftError("initial state outside declared chart")
        x, y = divmod(start, p)
        lifted = tuple(_eval(m, x, y, p) for m in self.features)
        end = self.transform.power(lifted, tick)
        ox, oy = end[:2]
        if end != tuple(_eval(m, ox, oy, p) for m in self.features):
            raise PolynomialLiftError("power result escaped the verified feature embedding")
        return ProgramNavigationResult(
            state=ox * p + oy, coordinates=(ox, oy), logical_tick=tick,
            certificate_fingerprint=self.fingerprint,
            source_digest=self.law.source_digest,
            model_fingerprint=self.law.ground.fingerprint,
            observation_fingerprint=self.observations.fingerprint if self.observations else None,
            exponent_bits=tick.bit_length(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "VGI-ProgramNavigationCertificate-1",
            "certificate_fingerprint": self.fingerprint,
            "source_digest": self.law.source_digest,
            "model_fingerprint": self.law.ground.fingerprint,
            "observation_fingerprint": self.observations.fingerprint if self.observations else None,
            "observed_edges": len(self.observations.edges) if self.observations else 0,
            "features": [list(m) for m in self.features],
            "transition": self.transform.to_dict(),
            "proof_method": "bounded_ast_denotational_semantics_and_exact_polynomial_identity",
            "trust_scope": "formal_bounded_program_semantics_only",
            "external_implementation_verified": False,
        }


@dataclass(frozen=True, slots=True)
class ProgramNavigationResult:
    state: int
    coordinates: tuple[int, int]
    logical_tick: int
    certificate_fingerprint: str
    source_digest: str
    model_fingerprint: str
    observation_fingerprint: str | None
    exponent_bits: int
    materialized_intermediate_states: int = 0
    trust_scope: str = "formal_bounded_program_semantics_only"

    def to_dict(self) -> dict[str, object]:
        return {
            "format": "VGI-ProgramNavigationResult-1",
            "state": self.state,
            "coordinates": list(self.coordinates),
            "logical_tick": self.logical_tick,
            "certificate_fingerprint": self.certificate_fingerprint,
            "source_digest": self.source_digest,
            "model_fingerprint": self.model_fingerprint,
            "observation_fingerprint": self.observation_fingerprint,
            "exponent_bits": self.exponent_bits,
            "materialized_intermediate_states": self.materialized_intermediate_states,
            "trust_scope": self.trust_scope,
        }


def certify_program(source: str, modulus: int, *, action: str = "advance",
                    max_feature_degree: int = 3,
                    observations: SparseTransitionObservations | None = None) -> ProgramNavigationCertificate:
    """Compile and structurally verify a supported straight-line Python-like program.

    No execution or evaluation of the input source is performed. Returning a result does not establish
    anything about a process outside the DSL. Exact symbolic identities prove
    the lifted relation within the declared formal program semantics.
    """
    law = ExtractedProgramLaw(source, modulus, action)
    features, transform = _construct_lift(law.ground, max_feature_degree, 32)
    return ProgramNavigationCertificate(law, max_feature_degree, features, transform,
                                        observations)


__all__ = [
    "ExtractedProgramLaw", "ProgramNavigationCertificate",
    "ProgramNavigationResult", "certify_program",
]