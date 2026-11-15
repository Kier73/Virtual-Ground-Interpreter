"""GEOMETRY-FIRST-006: discover exact coordinate invariant blocks from opaque maps.

Factor support, not declared operator types, defines the finest common
coordinate partition for the admitted typed graph. This is deliberately
narrower than discovering arbitrary invariant subspaces under a basis change.

The certificate is an exact mathematical statement about immutable finite-ring
operator operands. It does not establish external host authority or execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .affine import ModularAffineMap
from .typed_operator_navigation import (
    DenseMap, DiagonalMap, FiniteSpace, OperatorChain, TypedOperatorError,
    TypedVector, _digest, _int,
)

Block = tuple[int, ...]
Matrix = tuple[tuple[int, ...], ...]


def _admissible(graph: OperatorChain) -> tuple[int, int]:
    if not isinstance(graph, OperatorChain) or graph.domain != graph.codomain:
        raise TypedOperatorError("block discovery requires a closed typed endomorphism")
    n, modulus = graph.domain.dimension, graph.domain.modulus
    for leaf in graph.factors:
        if leaf.domain.dimension != n or leaf.codomain.dimension != n:
            raise TypedOperatorError("each factor must retain one common coordinate dimension")
        if leaf.domain.modulus != modulus or leaf.codomain.modulus != modulus:
            raise TypedOperatorError("coordinate factors must share the exact ring")
    return n, modulus


def infer_coordinate_blocks(graph: OperatorChain) -> tuple[Block, ...]:
    """Finest coordinate-aligned common invariant decomposition of all factors.

    Build an undirected graph between any i!=j for which an *individual*
    factor's coefficient A[i,j] != 0. Connected components then give the
    finest common coordinate blocks. No matrix product is materialized.

    This is conservative: cancellation between dense factors or invariance in
    a non-coordinate basis is not discovered by this method.
    """
    n, _ = _admissible(graph)
    parent = list(range(n))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def link(i: int, j: int) -> None:
        a, b = root(i), root(j)
        if a != b:
            parent[max(a, b)] = min(a, b)

    for leaf in graph.factors:
        if isinstance(leaf, DenseMap):
            for i, row in enumerate(leaf.rows):
                for j, value in enumerate(row):
                    if i != j and value != 0:
                        link(i, j)
        elif not isinstance(leaf, DiagonalMap):
            raise TypedOperatorError("unsupported factor in block inference")

    components: dict[int, list[int]] = {}
    for i in range(n):
        components.setdefault(root(i), []).append(i)
    return tuple(sorted((tuple(indices) for indices in components.values()),
                        key=lambda block: block[0]))


def _block_factor(leaf: DenseMap | DiagonalMap, block: Block) -> Matrix:
    if isinstance(leaf, DenseMap):
        return tuple(tuple(leaf.rows[i][j] for j in block) for i in block)
    return tuple(tuple(leaf.diagonal[i] if i == j else 0 for j in block)
                 for i in block)


def _multiply(left: Matrix, right: Matrix, modulus: int) -> Matrix:
    """Exact block-local multiplication; never constructs ambient n-by-n AB."""
    size = len(left)
    return tuple(tuple(sum(left[i][k] * right[k][j]
                           for k in range(size)) % modulus
                       for j in range(size)) for i in range(size))


def _composite_block(graph: OperatorChain, block: Block, modulus: int) -> Matrix:
    size = len(block)
    result = tuple(tuple(int(i == j) for j in range(size)) for i in range(size))
    for leaf in reversed(graph.factors):
        result = _multiply(_block_factor(leaf, block), result, modulus)
    return result


def _validate_block_matrix(value: Any, size: int, modulus: int) -> Matrix:
    try:
        rows = tuple(tuple(row) for row in value)
    except TypeError as exc:
        raise TypedOperatorError("block matrix must contain finite rows") from exc
    if len(rows) != size or any(len(row) != size for row in rows):
        raise TypedOperatorError("block matrix shape mismatch")
    if any(type(entry) is not int or not 0 <= entry < modulus
           for row in rows for entry in row):
        raise TypedOperatorError("block coefficients must be canonical integers")
    return rows


@dataclass(frozen=True, slots=True)
class CertifiedInvariantBlocks:
    """Exact, construction-time-audited block certificate for an immutable graph.

    Validation independently recomputes the entire support partition and
    each small-block composite from canonical admitted operands. Since *each*
    factor preserves each block, its composition does too. The certificate
    does not rely on probabilistic vectors or sample-based extrapolation.
    """
    graph: OperatorChain
    blocks: tuple[Block, ...]
    local_composites: tuple[Matrix, ...]
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        n, modulus = _admissible(self.graph)
        inferred = infer_coordinate_blocks(self.graph)
        if len(inferred) <= 1:
            raise TypedOperatorError("no proper coordinate-block decomposition found")
        if not isinstance(self.blocks, (tuple, list)) or tuple(self.blocks) != inferred:
            raise TypedOperatorError("claimed blocks disagree with exact factor support")
        if not isinstance(self.local_composites, (tuple, list)) or len(self.local_composites) != len(inferred):
            raise TypedOperatorError("incorrect number of block-local composites")
        checked: list[Matrix] = []
        for b, submitted in zip(inferred, self.local_composites):
            canonical = _validate_block_matrix(submitted, len(b), modulus)
            if canonical != _composite_block(self.graph, b, modulus):
                raise TypedOperatorError("local block transform is not the exact graph composition")
            checked.append(canonical)
        if set().union(*map(set, inferred)) != set(range(n)):
            raise TypedOperatorError("blocks do not cover the coordinate basis")
        object.__setattr__(self, "blocks", inferred)
        object.__setattr__(self, "local_composites", tuple(checked))
        object.__setattr__(self, "fingerprint", _digest({
            "schema": "VGI-CertifiedInvariantBlocks-1",
            "graph": self.graph.fingerprint,
            "blocks": inferred,
            "local_composites": checked,
            "proof": "every_offblock_coefficient_of_every_factor_is_zero",
            "coordinate_convention": "shared_ordered_coordinate_indices_across_typed_frames",
        }))

    @classmethod
    def discover(cls, graph: OperatorChain) -> "CertifiedInvariantBlocks":
        blocks = infer_coordinate_blocks(graph)
        if len(blocks) <= 1:
            raise TypedOperatorError("graph has no proper shared coordinate blocks")
        return cls(graph, blocks, tuple(_composite_block(graph, block, graph.domain.modulus)
                                        for block in blocks))

    @property
    def coordinate_count(self) -> int:
        return self.graph.domain.dimension

    @property
    def block_sizes(self) -> tuple[int, ...]:
        return tuple(len(b) for b in self.blocks)

    @property
    def power_cost_proxy(self) -> int:
        """Sum of cubes; useful comparison proxy, not measured arithmetic cost."""
        return sum(len(b) ** 3 for b in self.blocks)

    def state_at(self, initial: TypedVector, logical_tick: int) -> "BlockNavigationReceipt":
        _int(logical_tick, "logical tick")
        if not isinstance(initial, TypedVector) or initial.space != self.graph.domain:
            raise TypedOperatorError("block navigation input frame mismatch")
        m = self.graph.domain.modulus
        result = [0] * self.coordinate_count
        for block, local in zip(self.blocks, self.local_composites):
            part = tuple(initial.values[i] for i in block)
            transform = ModularAffineMap(m, local, (0,) * len(block))
            evolved = transform.power(part, logical_tick)
            for i, component in zip(block, evolved):
                result[i] = component
        return BlockNavigationReceipt(
            self.fingerprint, initial, logical_tick,
            TypedVector(self.graph.codomain, tuple(result)),
            self.block_sizes,
            logical_tick.bit_length(),
            len(self.blocks),
            0,
            "exact_common_coordinate_block_power",
        )


@dataclass(frozen=True, slots=True)
class BlockNavigationReceipt:
    certificate_fingerprint: str
    initial: TypedVector
    logical_tick: int
    result: TypedVector
    block_sizes: tuple[int, ...]
    exponent_bits: int
    local_powers: int
    full_composite_materializations_during_query: int
    method: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "VGI-BlockNavigationReceipt-1",
            "certificate_fingerprint": self.certificate_fingerprint,
            "initial": self.initial.to_dict(),
            "logical_tick": self.logical_tick,
            "result": self.result.to_dict(),
            "block_sizes": self.block_sizes,
            "exponent_bits": self.exponent_bits,
            "local_powers": self.local_powers,
            "full_composite_materializations_during_query": self.full_composite_materializations_during_query,
            "method": self.method,
            "scope": "exact_declared_typed_finite_ring_graph_only",
        }


def verify_block_receipt(certificate: CertifiedInvariantBlocks,
                         receipt: BlockNavigationReceipt) -> bool:
    if not isinstance(certificate, CertifiedInvariantBlocks) or not isinstance(receipt, BlockNavigationReceipt):
        return False
    try:
        return certificate.state_at(receipt.initial, receipt.logical_tick) == receipt
    except (TypedOperatorError, ValueError):
        return False


__all__ = ["infer_coordinate_blocks", "CertifiedInvariantBlocks",
           "BlockNavigationReceipt", "verify_block_receipt"]