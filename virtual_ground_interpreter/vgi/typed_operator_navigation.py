"""GEOMETRY-FIRST-005: typed, context-bound, demand-driven operator navigation.

A finite-ring linear-map chain is a first-class computational result. It may
answer a selected coordinate or a vector without constructing an intermediate
matrix product. Distant logical-time navigation is separate and explicitly
prepares a dense map before using VGI's existing affine powering primitive.

Pure mathematical reference implementation; no host authority is implied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Sequence, TypeAlias

from .affine import ModularAffineMap


class TypedOperatorError(ValueError):
    """An invalid type, graph, demand, or claimed navigation result."""


def _int(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise TypedOperatorError(f"{name} must be an integer >= {minimum}")
    return value


def _digest(value: Any) -> str:
    try:
        blob = json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TypedOperatorError("cannot fingerprint noncanonical value") from exc
    return sha256(blob).hexdigest()


def _name(value: Any, label: str) -> str:
    if (not isinstance(value, str) or not value or value.strip() != value
        or len(value) > 128 or any(ord(c) < 32 for c in value)):
        raise TypedOperatorError(f"invalid {label}")
    return value


@dataclass(frozen=True, slots=True)
class FiniteSpace:
    """Named coordinate frame over Z/mZ: identical dimensions are not identical types."""
    frame: str
    dimension: int
    modulus: int

    def __post_init__(self) -> None:
        _name(self.frame, "frame")
        _int(self.dimension, "dimension", 1)
        _int(self.modulus, "modulus", 2)

    def to_dict(self) -> dict[str, Any]:
        return {"frame": self.frame, "dimension": self.dimension,
                "ring": "Z/modulus Z", "modulus": self.modulus}


@dataclass(frozen=True, slots=True)
class TypedVector:
    space: FiniteSpace
    values: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.space, FiniteSpace):
            raise TypedOperatorError("vector requires a finite coordinate space")
        if isinstance(self.values, (str, bytes)):
            raise TypedOperatorError("vector coordinates must be integers")
        try:
            coords = tuple(self.values)
        except TypeError as exc:
            raise TypedOperatorError("vector coordinates must be finite") from exc
        if len(coords) != self.space.dimension:
            raise TypedOperatorError("vector dimension disagrees with its coordinate space")
        for v in coords:
            if type(v) is not int:
                raise TypedOperatorError("vector coordinates must be exact integers")
        object.__setattr__(self, "values", tuple(v % self.space.modulus for v in coords))

    def to_dict(self) -> dict[str, Any]:
        return {"space": self.space.to_dict(), "values": list(self.values)}


def _rect(rows: Sequence[Sequence[int]], output: FiniteSpace,
          input_: FiniteSpace) -> tuple[tuple[int, ...], ...]:
    if isinstance(rows, (str, bytes)):
        raise TypedOperatorError("matrix must be rows of exact integers")
    try:
        canonical = tuple(tuple(row) for row in rows)
    except TypeError as exc:
        raise TypedOperatorError("matrix must have rectangular finite rows") from exc
    if len(canonical) != output.dimension or any(len(row) != input_.dimension for row in canonical):
        raise TypedOperatorError("matrix shape does not match typed input/output frames")
    for row in canonical:
        for coefficient in row:
            if type(coefficient) is not int:
                raise TypedOperatorError("matrix coefficients must be exact integers")
    return tuple(tuple(v % output.modulus for v in row) for row in canonical)


@dataclass(frozen=True, slots=True)
class DenseMap:
    """One immutable dynamic operand, supplying an exact linear map."""
    identity: str
    domain: FiniteSpace
    codomain: FiniteSpace
    rows: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        _name(self.identity, "operand identity")
        if not isinstance(self.domain, FiniteSpace) or not isinstance(self.codomain, FiniteSpace):
            raise TypedOperatorError("operator requires typed domain and codomain")
        if self.domain.modulus != self.codomain.modulus:
            raise TypedOperatorError("operator cannot silently change rings")
        object.__setattr__(self, "rows", _rect(self.rows, self.codomain, self.domain))

    def apply(self, value: TypedVector) -> TypedVector:
        if not isinstance(value, TypedVector) or value.space != self.domain:
            raise TypedOperatorError("operator input type mismatch")
        m = self.domain.modulus
        return TypedVector(self.codomain, tuple(
            sum(a * b for a, b in zip(row, value.values)) % m for row in self.rows
        ))

    @property
    def scalar_products(self) -> int:
        return self.domain.dimension * self.codomain.dimension

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"type": "dense", "identity": self.identity,
                "domain": self.domain.to_dict(), "codomain": self.codomain.to_dict(),
                "rows": [list(row) for row in self.rows]}


def homogeneous_affine_map(identity: str, frame: str,
                           transform: ModularAffineMap) -> DenseMap:
    """Reframe a verified VGI affine transform as a typed homogeneous map.

    The final coordinate is 1 only for valid affine-state embeddings. The
    resulting *linear* operator can be composed with other typed maps, but
    arbitrary operators do NOT automatically preserve the embedding's semantic
    invariants; callers must check those before interpreting base-state values.
    """
    if not isinstance(transform, ModularAffineMap):
        raise TypedOperatorError("requires an existing VGI ModularAffineMap")
    space = FiniteSpace(_name(frame, "frame"), transform.dimension + 1, transform.modulus)
    rows = tuple(tuple(row) + (transform.offset[i],)
                 for i, row in enumerate(transform.matrix))
    rows += ((0,) * transform.dimension + (1,),)
    return DenseMap(identity, space, space, rows)


def project_homogeneous_vector(vector: TypedVector) -> tuple[int, ...]:
    """Decode only states with the declared trailing affine constant equal to 1."""
    if not isinstance(vector, TypedVector) or vector.space.dimension < 2:
        raise TypedOperatorError("homogeneous vector requires a typed augmented space")
    if vector.values[-1] != 1:
        raise TypedOperatorError("homogeneous constant coordinate was not preserved")
    return vector.values[:-1]


@dataclass(frozen=True, slots=True)
class DiagonalMap:
    """A typed diagonal operator; O(n) to apply, never materializes a dense matrix."""
    identity: str
    domain: FiniteSpace
    codomain: FiniteSpace
    diagonal: tuple[int, ...]

    def __post_init__(self) -> None:
        _name(self.identity, "operand identity")
        if not isinstance(self.domain, FiniteSpace) or not isinstance(self.codomain, FiniteSpace):
            raise TypedOperatorError("diagonal map requires finite spaces")
        if self.domain.modulus != self.codomain.modulus or self.domain.dimension != self.codomain.dimension:
            raise TypedOperatorError("diagonal map requires equal dimensions and ring")
        try:
            diag = tuple(self.diagonal)
        except TypeError as exc:
            raise TypedOperatorError("diagonal coefficients must be finite") from exc
        if len(diag) != self.domain.dimension or any(type(v) is not int for v in diag):
            raise TypedOperatorError("invalid diagonal coefficients")
        object.__setattr__(self, "diagonal", tuple(v % self.domain.modulus for v in diag))

    def apply(self, value: TypedVector) -> TypedVector:
        if not isinstance(value, TypedVector) or value.space != self.domain:
            raise TypedOperatorError("diagonal input frame mismatch")
        return TypedVector(self.codomain, tuple(
            v * d % self.domain.modulus for v, d in zip(value.values, self.diagonal)
        ))

    @property
    def scalar_products(self) -> int:
        return self.domain.dimension

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"type": "diagonal", "identity": self.identity,
                "domain": self.domain.to_dict(), "codomain": self.codomain.to_dict(),
                "diagonal": list(self.diagonal)}


Leaf: TypeAlias = DenseMap | DiagonalMap


@dataclass(frozen=True, slots=True)
class OperatorChain:
    """Typed composition F0 ◦ F1 ◦ ...; rightmost factor acts first."""
    factors: tuple[Leaf, ...]
    _fingerprint: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            factors = tuple(self.factors)
        except TypeError as exc:
            raise TypedOperatorError("operator graph must be a finite sequence") from exc
        if not factors or len(factors) > 64:
            raise TypedOperatorError("operator graph must contain between 1 and 64 factors")
        if any(not isinstance(f, (DenseMap, DiagonalMap)) for f in factors):
            raise TypedOperatorError("unknown operator kind")
        for left, right in zip(factors, factors[1:]):
            if left.domain != right.codomain:
                raise TypedOperatorError("composition frames/rings do not match exactly")
        object.__setattr__(self, "factors", factors)
        object.__setattr__(self, "_fingerprint", _digest({
            "schema": "VGI-TypedOperatorChain-1",
            "factor_digests": [f.fingerprint for f in factors],
        }))

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    @property
    def domain(self) -> FiniteSpace:
        return self.factors[-1].domain

    @property
    def codomain(self) -> FiniteSpace:
        return self.factors[0].codomain

    @property
    def scalar_products_per_vector(self) -> int:
        return sum(f.scalar_products for f in self.factors)

    def apply(self, value: TypedVector) -> TypedVector:
        if not isinstance(value, TypedVector) or value.space != self.domain:
            raise TypedOperatorError("graph input frame mismatch")
        for factor in reversed(self.factors):
            value = factor.apply(value)
        return value

    def entry(self, row: int, column: int) -> int:
        _int(row, "output row")
        _int(column, "input column")
        if row >= self.codomain.dimension or column >= self.domain.dimension:
            raise TypedOperatorError("requested entry outside typed product")
        basis = tuple(1 if i == column else 0 for i in range(self.domain.dimension))
        return self.apply(TypedVector(self.domain, basis)).values[row]

    def materialize(self) -> tuple[tuple[int, ...], ...]:
        """Only an explicit demand materializes the full composed matrix."""
        columns = []
        for col in range(self.domain.dimension):
            basis = tuple(int(i == col) for i in range(self.domain.dimension))
            columns.append(self.apply(TypedVector(self.domain, basis)).values)
        return tuple(tuple(columns[j][i] for j in range(self.domain.dimension))
                     for i in range(self.codomain.dimension))

    def rebind(self, slot: int, operand: Leaf) -> "OperatorChain":
        _int(slot, "slot")
        if slot >= len(self.factors) or not isinstance(operand, (DenseMap, DiagonalMap)):
            raise TypedOperatorError("replacement operand/slot invalid")
        if (operand.domain != self.factors[slot].domain
            or operand.codomain != self.factors[slot].codomain):
            raise TypedOperatorError("replacement changes graph interface")
        replaced = list(self.factors)
        replaced[slot] = operand
        return OperatorChain(tuple(replaced))

    def to_dict(self) -> dict[str, Any]:
        return {"format": "VGI-TypedOperatorChain-1", "fingerprint": self.fingerprint,
                "factors": [f.to_dict() for f in self.factors],
                "application_order": "right_to_left"}


@dataclass(frozen=True, slots=True)
class OperatorDemand:
    """An exact, immutable request bound to a typed graph and operand snapshot."""
    kind: str
    vector: TypedVector | None = None
    row: int | None = None
    column: int | None = None

    def __post_init__(self) -> None:
        if self.kind == "vector":
            if not isinstance(self.vector, TypedVector) or self.row is not None or self.column is not None:
                raise TypedOperatorError("vector demand requires only one typed vector")
        elif self.kind == "entry":
            if self.vector is not None:
                raise TypedOperatorError("entry demand must not contain a vector")
            _int(self.row, "output row")
            _int(self.column, "input column")
        elif self.kind == "dense":
            if self.vector is not None or self.row is not None or self.column is not None:
                raise TypedOperatorError("dense demand has no input payload")
        else:
            raise TypedOperatorError("unknown operator demand kind")

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "vector": self.vector.to_dict() if self.vector else None,
                "row": self.row, "column": self.column}


@dataclass(frozen=True, slots=True)
class OperatorDemandReceipt:
    """Replayable self-check; NOT a signature or E-CPU authorization grant."""
    graph_fingerprint: str
    demand_fingerprint: str
    result_fingerprint: str
    result_value: int | tuple[int, ...] | tuple[tuple[int, ...], ...]
    output_space: FiniteSpace | None
    leaf_applications: int
    estimated_scalar_products: int
    composite_dense_materialized: bool
    method: str

    def to_dict(self) -> dict[str, Any]:
        return {"format": "VGI-TypedOperatorDemandReceipt-1",
                "graph_fingerprint": self.graph_fingerprint,
                "demand_fingerprint": self.demand_fingerprint,
                "result_fingerprint": self.result_fingerprint,
                "result": self.result_value, "output_space": self.output_space.to_dict() if self.output_space else None,
                "leaf_applications": self.leaf_applications,
                "estimated_scalar_products": self.estimated_scalar_products,
                "composite_dense_materialized": self.composite_dense_materialized,
                "method": self.method,
                "scope": "declared_exact_linear_ring_semantics_only"}


def fulfill(chain: OperatorChain, demand: OperatorDemand) -> OperatorDemandReceipt:
    """Evaluate only the target observable; a graph itself is a valid result."""
    if not isinstance(chain, OperatorChain) or not isinstance(demand, OperatorDemand):
        raise TypedOperatorError("expected typed graph and typed demand")
    if demand.kind == "vector":
        assert demand.vector is not None
        result = chain.apply(demand.vector)
        value, space = result.values, result.space
        evaluations, dense, method = 1, False, "composed_vector_application"
    elif demand.kind == "entry":
        assert demand.row is not None and demand.column is not None
        value, space = chain.entry(demand.row, demand.column), None
        evaluations, dense, method = 1, False, "single_column_basis_navigation"
    else:
        value, space = chain.materialize(), None
        evaluations, dense, method = chain.domain.dimension, True, "explicit_dense_materialization"
    return OperatorDemandReceipt(
        chain.fingerprint, demand.fingerprint,
        _digest({"value": value, "output_space": space.to_dict() if space else None}),
        value, space, len(chain.factors) * evaluations,
        chain.scalar_products_per_vector * evaluations, dense, method,
    )


def verify_receipt(chain: OperatorChain, demand: OperatorDemand,
                   receipt: OperatorDemandReceipt) -> bool:
    """Recompute against *current* graph/operand state: old receipts do not rebind."""
    if not isinstance(receipt, OperatorDemandReceipt):
        return False
    return fulfill(chain, demand) == receipt


def _dense_reference_product(chain: OperatorChain) -> tuple[tuple[int, ...], ...]:
    """Independently construct a composite via matrix-by-matrix products.

    This is a *preparation* cost, unlike the demand-driven entry/vector route.
    The resulting matrix is checked against every basis-vector traversal by
    PreparedTemporalOperator before admission.
    """
    if not isinstance(chain, OperatorChain):
        raise TypedOperatorError("expected typed operator chain")
    def factor_rows(factor: Leaf) -> tuple[tuple[int, ...], ...]:
        if isinstance(factor, DenseMap):
            return factor.rows
        return tuple(tuple(factor.diagonal[i] if i == j else 0
                           for j in range(factor.domain.dimension))
                     for i in range(factor.codomain.dimension))
    left = factor_rows(chain.factors[0])
    m = chain.domain.modulus
    for factor in chain.factors[1:]:
        right = factor_rows(factor)
        left = tuple(tuple(
            sum(left[i][k] * right[k][j] for k in range(len(right))) % m
            for j in range(len(right[0]))
        ) for i in range(len(left)))
    return left


@dataclass(frozen=True, slots=True)
class PreparedTemporalOperator:
    """A closed endomorphism with an explicitly materialized, checked dense map.

    The materialization cost belongs to preparation, never concealed in a
    zero-materialization query count. The graph need not be invertible.
    """
    graph: OperatorChain
    dense: tuple[tuple[int, ...], ...]
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.graph, OperatorChain) or self.graph.domain != self.graph.codomain:
            raise TypedOperatorError("temporal power requires a closed typed endomorphism")
        expected = self.graph.materialize()
        try:
            supplied = tuple(tuple(row) for row in self.dense)
        except TypeError as exc:
            raise TypedOperatorError("temporal materialization must be a square matrix") from exc
        if supplied != expected:
            raise TypedOperatorError("prepared temporal matrix differs from full graph action")
        object.__setattr__(self, "dense", expected)
        object.__setattr__(self, "fingerprint", _digest({
            "schema": "VGI-PreparedTemporalOperator-1",
            "graph": self.graph.fingerprint, "dense": expected,
        }))

    @classmethod
    def from_chain(cls, chain: OperatorChain) -> "PreparedTemporalOperator":
        return cls(chain, _dense_reference_product(chain))

    def state_at(self, initial: TypedVector, logical_tick: int) -> "TemporalNavigationReceipt":
        _int(logical_tick, "logical tick")
        if not isinstance(initial, TypedVector) or initial.space != self.graph.domain:
            raise TypedOperatorError("temporal query input frame mismatch")
        matrix = ModularAffineMap(self.graph.domain.modulus, self.dense,
                                  (0,) * self.graph.domain.dimension)
        end = TypedVector(self.graph.codomain, matrix.power(initial.values, logical_tick))
        return TemporalNavigationReceipt(
            self.fingerprint, initial, logical_tick, end,
            logical_tick.bit_length(), 0,
            self.graph.domain.dimension * len(self.graph.factors),
        )


@dataclass(frozen=True, slots=True)
class TemporalNavigationReceipt:
    temporal_certificate_fingerprint: str
    initial: TypedVector
    logical_tick: int
    result: TypedVector
    exponent_bits: int
    intermediate_logical_states_materialized: int
    preparation_leaf_applications: int  # basis verification; dense product preparation is separate

    def to_dict(self) -> dict[str, Any]:
        return {"format": "VGI-TemporalOperatorNavigationReceipt-1",
                "temporal_certificate_fingerprint": self.temporal_certificate_fingerprint,
                "initial": self.initial.to_dict(), "logical_tick": self.logical_tick,
                "result": self.result.to_dict(), "exponent_bits": self.exponent_bits,
                "intermediate_logical_states_materialized": self.intermediate_logical_states_materialized,
                "preparation_leaf_applications": self.preparation_leaf_applications,
                "method": "dense_operator_preparation_then_modular_affine_power",
                "scope": "declared_exact_linear_ring_semantics_only"}


def verify_temporal_receipt(prepared: PreparedTemporalOperator,
                            receipt: TemporalNavigationReceipt) -> bool:
    if not isinstance(receipt, TemporalNavigationReceipt):
        return False
    try:
        return prepared.state_at(receipt.initial, receipt.logical_tick) == receipt
    except TypedOperatorError:
        return False


__all__ = [
    "TypedOperatorError", "FiniteSpace", "TypedVector", "DenseMap", "DiagonalMap",
    "homogeneous_affine_map", "project_homogeneous_vector",
    "OperatorChain", "OperatorDemand", "OperatorDemandReceipt", "fulfill",
    "verify_receipt", "PreparedTemporalOperator", "TemporalNavigationReceipt",
    "verify_temporal_receipt",
]


@dataclass(frozen=True, slots=True)
class PreparedDiagonalTemporalOperator:
    """An exact type-discovered diagonal semigroup with no dense preparation.

    Only closed endomorphism chains composed entirely of admitted DiagonalMap
    factors qualify. Certification checks each basis action of the original
    graph against the pointwise product of the diagonal coefficients.
    """
    graph: OperatorChain
    diagonal: tuple[int, ...]
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if (not isinstance(self.graph, OperatorChain)
            or self.graph.domain != self.graph.codomain
            or any(not isinstance(f, DiagonalMap) for f in self.graph.factors)):
            raise TypedOperatorError("structured temporal navigation requires a closed diagonal chain")
        m, n = self.graph.domain.modulus, self.graph.domain.dimension
        expected = tuple(
            _component_diagonal(self.graph.factors, i, m) for i in range(n)
        )
        if (not isinstance(self.diagonal, (tuple, list))
            or len(self.diagonal) != n
            or any(type(x) is not int for x in self.diagonal)
            or tuple(self.diagonal) != expected):
            raise TypedOperatorError("structured temporal coefficients disagree with graph")
        for j in range(n):
            basis = TypedVector(self.graph.domain, tuple(int(i == j) for i in range(n)))
            image = self.graph.apply(basis)
            if image.values != tuple(expected[i] if i == j else 0 for i in range(n)):
                raise TypedOperatorError("structured certificate fails independent basis check")
        object.__setattr__(self, "diagonal", expected)
        object.__setattr__(self, "fingerprint", _digest({
            "schema": "VGI-StructuredDiagonalTemporalOperator-1",
            "graph": self.graph.fingerprint, "diagonal": expected,
            "basis_checks": n,
        }))

    @classmethod
    def from_chain(cls, chain: OperatorChain) -> "PreparedDiagonalTemporalOperator":
        if not isinstance(chain, OperatorChain) or chain.domain != chain.codomain:
            raise TypedOperatorError("structured temporal query requires a closed chain")
        if any(not isinstance(f, DiagonalMap) for f in chain.factors):
            raise TypedOperatorError("cannot prove diagonal structure from arbitrary dense leaves")
        return cls(chain, tuple(_component_diagonal(chain.factors, i, chain.domain.modulus)
                                for i in range(chain.domain.dimension)))

    def state_at(self, initial: TypedVector, logical_tick: int) -> "StructuredTemporalReceipt":
        _int(logical_tick, "logical tick")
        if not isinstance(initial, TypedVector) or initial.space != self.graph.domain:
            raise TypedOperatorError("structured temporal input frame mismatch")
        m = self.graph.domain.modulus
        return StructuredTemporalReceipt(
            self.fingerprint, initial, logical_tick,
            TypedVector(self.graph.codomain, tuple(
                pow(d, logical_tick, m) * x % m
                for d, x in zip(self.diagonal, initial.values)
            )), logical_tick.bit_length(),
            basis_checks=self.graph.domain.dimension,
            composite_dense_materialized=False,
            intermediate_logical_states_materialized=0,
        )


def _component_diagonal(factors: tuple[Leaf, ...], index: int, modulus: int) -> int:
    value = 1
    for factor in factors:
        if not isinstance(factor, DiagonalMap):
            raise TypedOperatorError("non-diagonal factor cannot enter diagonal certificate")
        value = value * factor.diagonal[index] % modulus
    return value


@dataclass(frozen=True, slots=True)
class StructuredTemporalReceipt:
    certificate_fingerprint: str
    initial: TypedVector
    logical_tick: int
    result: TypedVector
    exponent_bits: int
    basis_checks: int
    composite_dense_materialized: bool
    intermediate_logical_states_materialized: int

    def to_dict(self) -> dict[str, Any]:
        return {"format": "VGI-StructuredTemporalReceipt-1",
                "certificate_fingerprint": self.certificate_fingerprint,
                "initial": self.initial.to_dict(), "logical_tick": self.logical_tick,
                "result": self.result.to_dict(), "exponent_bits": self.exponent_bits,
                "basis_checks": self.basis_checks,
                "composite_dense_materialized": self.composite_dense_materialized,
                "intermediate_logical_states_materialized": self.intermediate_logical_states_materialized,
                "method": "certified_diagonal_component_powers",
                "scope": "declared_exact_linear_ring_semantics_only"}


def verify_structured_temporal_receipt(prepared: PreparedDiagonalTemporalOperator,
                                       receipt: StructuredTemporalReceipt) -> bool:
    if not isinstance(prepared, PreparedDiagonalTemporalOperator) or not isinstance(receipt, StructuredTemporalReceipt):
        return False
    try:
        return prepared.state_at(receipt.initial, receipt.logical_tick) == receipt
    except TypedOperatorError:
        return False


__all__.extend([
    "PreparedDiagonalTemporalOperator", "StructuredTemporalReceipt",
    "verify_structured_temporal_receipt",
])
