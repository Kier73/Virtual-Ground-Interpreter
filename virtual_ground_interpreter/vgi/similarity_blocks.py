"""GEOMETRY-FIRST-007: certify common operator blocks in a discovered basis.

An exact finite-prime-field commutant is used only to *discover* candidate
coordinates. Every factor is then verified against the resulting similarity
transformation. This certifies declared mathematical operands, not a host.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any

from .affine import ModularAffineMap
from .typed_operator_navigation import (
    DenseMap, DiagonalMap, FiniteSpace, OperatorChain, TypedOperatorError,
    TypedVector, _digest, _int,
)

Matrix = tuple[tuple[int, ...], ...]


def _field(graph: OperatorChain) -> tuple[int, int]:
    if not isinstance(graph, OperatorChain) or graph.domain != graph.codomain:
        raise TypedOperatorError("similarity search requires a closed typed endomorphism")
    n, p = graph.domain.dimension, graph.domain.modulus
    if not 2 <= n <= 16 or not 2 <= p <= 257:
        raise TypedOperatorError("bounded discovery requires 2..16 dimensions and modulus <=257")
    if any(p % candidate == 0 for candidate in range(2, int(p ** .5) + 1)):
        raise TypedOperatorError("similarity search requires a prime field (not a composite ring)")
    if any(f.domain != graph.domain or f.codomain != graph.domain for f in graph.factors):
        raise TypedOperatorError("all factors must have the same exact typed frame")
    return n, p


def _mat(leaf: DenseMap | DiagonalMap) -> Matrix:
    if isinstance(leaf, DenseMap):
        return leaf.rows
    if isinstance(leaf, DiagonalMap):
        n = len(leaf.diagonal)
        return tuple(tuple(leaf.diagonal[i] if i == j else 0 for j in range(n)) for i in range(n))
    raise TypedOperatorError("unsupported operator in common-basis discovery")


def _eye(n: int) -> Matrix:
    return tuple(tuple(int(i == j) for j in range(n)) for i in range(n))


def _mul(a: Matrix, b: Matrix, p: int) -> Matrix:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(len(b))) % p
                       for j in range(len(b[0]))) for i in range(len(a)))


def _mv(a: Matrix, v: tuple[int, ...], p: int) -> tuple[int, ...]:
    return tuple(sum(x * y for x, y in zip(row, v)) % p for row in a)


def _columns(columns: tuple[tuple[int, ...], ...]) -> Matrix:
    return tuple(tuple(col[i] for col in columns) for i in range(len(columns[0])))


def _rref(rows: list[list[int]], width: int, p: int) -> tuple[list[list[int]], list[int]]:
    """Canonical row reduced echelon form in a finite prime field."""
    m = [list(x) for x in rows]
    if any(len(row) != width for row in m):
        raise TypedOperatorError("invalid linear system")
    pivots: list[int] = []
    lead = 0
    for col in range(width):
        pivot = next((r for r in range(lead, len(m)) if m[r][col] % p), None)
        if pivot is None:
            continue
        m[lead], m[pivot] = m[pivot], m[lead]
        val = m[lead][col] % p
        scale = pow(val, -1, p)
        m[lead] = [(u * scale) % p for u in m[lead]]
        for r in range(len(m)):
            if r != lead and m[r][col] % p:
                multiplier = m[r][col] % p
                m[r] = [(x - multiplier * y) % p for x, y in zip(m[r], m[lead])]
        pivots.append(col)
        lead += 1
        if lead == len(m):
            break
    return m, pivots


def _kernel(rows: list[list[int]], width: int, p: int) -> tuple[tuple[int, ...], ...]:
    reduced, pivots = _rref(rows, width, p)
    free = [j for j in range(width) if j not in pivots]
    output = []
    for f in free:
        v = [0] * width
        v[f] = 1
        for r, pivot in enumerate(pivots):
            v[pivot] = (-reduced[r][f]) % p
        output.append(tuple(v))
    return tuple(output)


def _inverse(matrix: Matrix, p: int) -> Matrix:
    n = len(matrix)
    augmented = [list(row) + list(_eye(n)[i]) for i, row in enumerate(matrix)]
    for k in range(n):
        pivot = next((i for i in range(k, n) if augmented[i][k] % p), None)
        if pivot is None:
            raise TypedOperatorError("candidate coordinate basis is singular")
        augmented[k], augmented[pivot] = augmented[pivot], augmented[k]
        scale = pow(augmented[k][k] % p, -1, p)
        augmented[k] = [(v * scale) % p for v in augmented[k]]
        for i in range(n):
            if i == k:
                continue
            factor = augmented[i][k] % p
            if factor:
                augmented[i] = [(a - factor * b) % p for a, b in zip(augmented[i], augmented[k])]
    return tuple(tuple(row[n:]) for row in augmented)


def _commutant_basis(graph: OperatorChain) -> tuple[Matrix, ...]:
    n, p = _field(graph)
    # Solve C*A - A*C = 0 for every individual input factor, exactly.
    constraints = []
    for leaf in graph.factors:
        a = _mat(leaf)
        for i in range(n):
            for j in range(n):
                row = [0] * (n*n)
                for k in range(n):
                    row[i*n+k] += a[k][j]
                    row[k*n+j] -= a[i][k]
                constraints.append([v % p for v in row])
    kernel = _kernel(constraints, n*n, p)
    return tuple(tuple(tuple(v[i*n:(i+1)*n]) for i in range(n)) for v in kernel)


def _eigenspaces(candidate: Matrix, p: int) -> tuple[tuple[int, tuple[tuple[int, ...], ...]], ...]:
    n = len(candidate)
    out = []
    total = 0
    for eigenvalue in range(p):
        equations = [[(candidate[i][j] - (eigenvalue if i == j else 0)) % p
                      for j in range(n)] for i in range(n)]
        basis = _kernel(equations, n, p)
        if basis:
            out.append((eigenvalue, basis))
            total += len(basis)
    return tuple(out) if total == n and len(out) > 1 else ()


def _canonical_matrix(matrix: Any, n: int, p: int, label: str) -> Matrix:
    if not isinstance(matrix, (tuple, list)) or len(matrix) != n:
        raise TypedOperatorError(f"{label} must be an {n}x{n} matrix")
    rows = []
    for row in matrix:
        if not isinstance(row, (tuple, list)) or len(row) != n:
            raise TypedOperatorError(f"{label} matrix shape differs")
        if any(type(v) is not int or v < 0 or v >= p for v in row):
            raise TypedOperatorError(f"{label} has noncanonical coefficient")
        rows.append(tuple(row))
    return tuple(rows)


def _compose_block(block_factors: tuple[Matrix, ...], p: int) -> Matrix:
    size = len(block_factors[0])
    result = _eye(size)
    for factor in reversed(block_factors):
        result = _mul(factor, result, p)
    return result


def _local_factors(graph: OperatorChain, basis: Matrix, inv: Matrix,
                   blocks: tuple[tuple[int, ...], ...], p: int) -> tuple[tuple[Matrix, ...], ...]:
    """Independently prove all factors block diagonal in the proposed basis."""
    factors = [ _mul(_mul(inv, _mat(leaf), p), basis, p) for leaf in graph.factors ]
    local = []
    for indices in blocks:
        local.append(tuple(tuple(tuple(f[i][j] for j in indices) for i in indices)
                           for f in factors))
    for transformed in factors:
        for a, first in enumerate(blocks):
            for b, second in enumerate(blocks):
                if a != b and any(transformed[i][j] != 0 for i in first for j in second):
                    raise TypedOperatorError("factor does not preserve proposed common eigenspaces")
    return tuple(local)


def _candidate_matrix(basis: tuple[Matrix, ...], weights: tuple[int, ...], p: int) -> Matrix:
    n = len(basis[0])
    return tuple(tuple(sum(w * a[i][j] for w, a in zip(weights,basis)) % p
                       for j in range(n)) for i in range(n))


def discover_similarity_blocks(graph: OperatorChain, *, max_candidates: int = 24
                              ) -> "CertifiedSimilarityBlocks":
    """Bounded centralizer/eigenspace search; fail closed when no split is proved.

    Complete commutant basis is derived by exact elimination. Candidate search
    for split semisimple witnesses is bounded, so failure is not a proof of
    indecomposability. All accepted splits are later checked independently.
    """
    n, p = _field(graph)
    _int(max_candidates, "candidate budget", 1)
    if max_candidates > 256:
        raise TypedOperatorError("candidate budget exceeds 256")
    centralizer = _commutant_basis(graph)
    if len(centralizer) <= 1:
        raise TypedOperatorError("only a scalar commutant found; no common split certified")
    r = len(centralizer)
    rng = random.Random(int(graph.fingerprint[:16], 16))
    # Reserve room for mixtures even if the centralizer has many generators.
    # A single standard nullspace vector may be nilpotent/non-splitting.
    singleton_count = min(r, max(1, max_candidates // 2))
    weights = [tuple(int(i == k) for i in range(r)) for k in range(singleton_count)]
    weights += [tuple(pow(j + 1, i, p) for i in range(r))
                for j in range(min(max_candidates - len(weights), 4))]
    while len(weights) < max_candidates:
        weights.append(tuple(rng.randrange(p) for _ in range(r)))
    best: tuple[Any, ...] | None = None
    for w in weights[:max_candidates]:
        c = _candidate_matrix(centralizer, w, p)
        eigenspaces = _eigenspaces(c, p)
        if not eigenspaces:
            continue
        score = (len(eigenspaces), -sum(len(vectors)**3 for _, vectors in eigenspaces))
        if best is None or score > best[0]:
            best = (score,c,eigenspaces)
    if best is None:
        raise TypedOperatorError("no fully splitting finite-field commutant witness found")
    _, c, eigenspaces = best
    columns = tuple(vector for _, vectors in eigenspaces for vector in vectors)
    pmat = _columns(columns)
    inv = _inverse(pmat, p)
    indices = []
    eigenvalues = []
    cursor = 0
    for lam, vectors in eigenspaces:
        indices.append(tuple(range(cursor, cursor + len(vectors))))
        eigenvalues.append(lam)
        cursor += len(vectors)
    blocks = tuple(indices)
    local = _local_factors(graph, pmat, inv, blocks, p)
    products = tuple(_compose_block(x, p) for x in local)
    return CertifiedSimilarityBlocks(graph, c, pmat, inv, blocks, tuple(eigenvalues), products)


@dataclass(frozen=True, slots=True)
class CertifiedSimilarityBlocks:
    """An exact typed-graph, commutant, basis and decomposed-product witness."""
    graph: OperatorChain
    centralizer_witness: Matrix
    basis: Matrix
    inverse_basis: Matrix
    blocks: tuple[tuple[int, ...], ...]
    eigenvalues: tuple[int, ...]
    local_composites: tuple[Matrix, ...]
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        n, p = _field(self.graph)
        c = _canonical_matrix(self.centralizer_witness,n,p,"commutant witness")
        basis = _canonical_matrix(self.basis,n,p,"basis")
        inv = _canonical_matrix(self.inverse_basis,n,p,"inverse basis")
        if _mul(basis,inv,p) != _eye(n) or _mul(inv,basis,p) != _eye(n):
            raise TypedOperatorError("basis and inverse are not mutually invertible")
        if not isinstance(self.blocks,tuple) or len(self.blocks)<2:
            raise TypedOperatorError("a proper direct-sum decomposition is required")
        if not isinstance(self.eigenvalues,tuple) or len(self.eigenvalues)!=len(self.blocks):
            raise TypedOperatorError("one eigenvalue required per block")
        if any(type(v) is not int or not 0<=v<p for v in self.eigenvalues):
            raise TypedOperatorError("invalid eigenvalue")
        if len(set(self.eigenvalues)) != len(self.eigenvalues):
            raise TypedOperatorError("decomposition requires distinct witness eigenvalues")
        expected = 0
        for block in self.blocks:
            if not isinstance(block,tuple) or block != tuple(range(expected, expected+len(block))) or not block:
                raise TypedOperatorError("basis blocks must be nonempty consecutive coordinates")
            expected+=len(block)
        if expected != n:
            raise TypedOperatorError("basis blocks do not span the entire input space")
        # Verify C*A=A*C for all supplied factors, not only the composite.
        for leaf in self.graph.factors:
            a=_mat(leaf)
            if _mul(c,a,p)!=_mul(a,c,p):
                raise TypedOperatorError("commutant witness fails an original operator")
        for indices, eigenvalue in zip(self.blocks,self.eigenvalues):
            for index in indices:
                vector=tuple(basis[row][index] for row in range(n))
                if _mv(c,vector,p)!=tuple(eigenvalue*x%p for x in vector):
                    raise TypedOperatorError("basis column not a witness eigenvector")
        local=_local_factors(self.graph,basis,inv,self.blocks,p)
        if not isinstance(self.local_composites,(tuple,list)) or len(self.local_composites)!=len(local):
            raise TypedOperatorError("invalid number of local products")
        canonical=[]
        for i,(factors,submitted) in enumerate(zip(local,self.local_composites)):
            m=_canonical_matrix(submitted,len(self.blocks[i]),p,"local product")
            if m!=_compose_block(factors,p):
                raise TypedOperatorError("block product differs from original factor composition")
            canonical.append(m)
        object.__setattr__(self,"centralizer_witness",c)
        object.__setattr__(self,"basis",basis)
        object.__setattr__(self,"inverse_basis",inv)
        object.__setattr__(self,"local_composites",tuple(canonical))
        object.__setattr__(self,"fingerprint",_digest({
            "schema":"VGI-CertifiedSimilarityBlocks-1", "graph":self.graph.fingerprint,
            "witness":c,"basis":basis,"inverse":inv,"blocks":self.blocks,
            "eigenvalues":self.eigenvalues,"local_composites":canonical,
            "proof":"CA=AC and P_inv P=I and transformed_factor_offblock=0"
        }))

    @classmethod
    def discover(cls,graph:OperatorChain,*,max_candidates:int=24)->"CertifiedSimilarityBlocks":
        return discover_similarity_blocks(graph,max_candidates=max_candidates)

    @property
    def block_sizes(self)->tuple[int,...]:
        return tuple(len(block) for block in self.blocks)

    @property
    def cost_proxy(self)->int:
        return sum(len(block)**3 for block in self.blocks)

    def state_at(self,initial:TypedVector,logical_tick:int)->"SimilarityNavigationReceipt":
        _int(logical_tick,"logical tick")
        if not isinstance(initial,TypedVector) or initial.space!=self.graph.domain:
            raise TypedOperatorError("similarity navigation input typed frame mismatch")
        p=self.graph.domain.modulus
        source=_mv(self.inverse_basis,initial.values,p)
        evolved=[0]*len(source)
        for indices,local in zip(self.blocks,self.local_composites):
            start=tuple(source[i] for i in indices)
            part=ModularAffineMap(p,local,(0,)*len(indices)).power(start,logical_tick)
            for j,value in zip(indices,part):
                evolved[j]=value
        result=TypedVector(self.graph.codomain,_mv(self.basis,tuple(evolved),p))
        return SimilarityNavigationReceipt(self.fingerprint,initial,logical_tick,result,
             self.block_sizes,logical_tick.bit_length(),len(self.blocks),0,
             "verified_common_similarity_block_power")


@dataclass(frozen=True, slots=True)
class SimilarityNavigationReceipt:
    certificate_fingerprint:str
    initial:TypedVector
    logical_tick:int
    result:TypedVector
    block_sizes:tuple[int,...]
    exponent_bits:int
    local_powers:int
    dense_composites_during_query:int
    method:str

    def to_dict(self)->dict[str,Any]:
        return {"format":"VGI-SimilarityNavigationReceipt-1",
                "certificate_fingerprint":self.certificate_fingerprint,
                "initial":self.initial.to_dict(),"logical_tick":self.logical_tick,
                "result":self.result.to_dict(),"block_sizes":self.block_sizes,
                "exponent_bits":self.exponent_bits,"local_powers":self.local_powers,
                "dense_composites_during_query":self.dense_composites_during_query,
                "method":self.method,"scope":"admitted_finite_prime_field_math_only"}


def verify_similarity_receipt(certificate:CertifiedSimilarityBlocks,
                              receipt:SimilarityNavigationReceipt)->bool:
    if not isinstance(certificate,CertifiedSimilarityBlocks) or not isinstance(receipt,SimilarityNavigationReceipt):
        return False
    try:
        return certificate.state_at(receipt.initial,receipt.logical_tick)==receipt
    except (ValueError,TypeError,AttributeError):
        return False