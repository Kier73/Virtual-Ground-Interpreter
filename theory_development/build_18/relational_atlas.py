"""Build 18: executable core for the Relational Invariant Atlas.

Requires NumPy. Quaternions use (w, x, y, z). The chosen Hopf map is
q -> q*i*q^{-1}; its fibres are right multiplication by exp(i*beta).

This module is a numerical research harness, not an empirical sensor result.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import comb, factorial
from typing import Callable, Iterable

import numpy as np

Array = np.ndarray


def q_normalize(q: Array) -> Array:
    q = np.asarray(q, dtype=float)
    n = np.linalg.norm(q)
    if not np.isfinite(n) or n == 0:
        raise ValueError("quaternion must have finite nonzero norm")
    return q / n


def q_conj(q: Array) -> Array:
    q = np.asarray(q, dtype=float)
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=float)


def q_mul(a: Array, b: Array) -> Array:
    """Hamilton product for scalar-first quaternions."""
    aw, ax, ay, az = np.asarray(a, dtype=float)
    bw, bx, by, bz = np.asarray(b, dtype=float)
    return np.array([
        aw*bw - ax*bx - ay*by - az*bz,
        aw*bx + ax*bw + ay*bz - az*by,
        aw*by - ax*bz + ay*bw + az*bx,
        aw*bz + ax*by - ay*bx + az*bw,
    ])


def q_distance_s3(a: Array, b: Array) -> float:
    """Intrinsic geodesic distance on the unit S^3, in [0, pi]."""
    a, b = q_normalize(a), q_normalize(b)
    return float(np.arccos(np.clip(np.dot(a, b), -1.0, 1.0)))


def su2_matrix(q: Array) -> Array:
    """Unit quaternion -> SU(2) matrix [[a+ib,c+id],[-c+id,a-ib]]."""
    a, b, c, d = q_normalize(q)
    return np.array([[a + 1j*b, c + 1j*d],
                     [-c + 1j*d, a - 1j*b]], dtype=complex)


def fibre_element(beta: float) -> Array:
    """exp(i beta), the selected U(1) subgroup of unit quaternions."""
    return np.array([np.cos(beta), np.sin(beta), 0.0, 0.0])


def hopf_map(q: Array) -> Array:
    """Hopf map S^3 -> S^2 represented by q*i*q^{-1} in R^3."""
    q = q_normalize(q)
    i_quat = np.array([0.0, 1.0, 0.0, 0.0])
    v = q_mul(q_mul(q, i_quat), q_conj(q))
    out = v[1:]
    return out / np.linalg.norm(out)


def symmetric_basis(n: int) -> Array:
    """Orthonormal basis matrix for Sym^n(C^2) inside (C^2)^tensor n.

    Column k is the normalized symmetric sum of bitstrings with k zeros.
    Basis index k has U(1) weight 2*k-n.
    """
    if n < 0 or n > 6:
        raise ValueError("n must be between 0 and 6 for this reference implementation")
    words = list(product((0, 1), repeat=n))
    B = np.zeros((2**n if n else 1, n + 1), dtype=complex)
    if n == 0:
        B[0, 0] = 1.0
        return B
    for k in range(n + 1):
        ids = [i for i, w in enumerate(words) if sum(x == 0 for x in w) == k]
        B[ids, k] = 1.0 / np.sqrt(comb(n, k))
    return B


def su2_irrep(q: Array, n: int) -> Array:
    """Spin j=n/2 irreducible representation as Sym^n of the fundamental."""
    U = su2_matrix(q)
    if n == 0:
        return np.ones((1, 1), dtype=complex)
    kron = U
    for _ in range(n - 1):
        kron = np.kron(kron, U)
    B = symmetric_basis(n)
    return B.conj().T @ kron @ B


def haar_s3_samples(count: int, seed: int = 1801) -> Array:
    """Haar-uniform points on SU(2) ~= S^3 via normalized Gaussian samples."""
    if count <= 0:
        raise ValueError("count must be positive")
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(count, 4))
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def antipodal_parity(q: Array, n: int) -> float:
    """Return ||D^(n/2)(-q) - (-1)^n D^(n/2)(q)||_F."""
    return float(np.linalg.norm(su2_irrep(-q, n) - ((-1)**n)*su2_irrep(q, n)))


def fibre_average_rep(q: Array, n: int, samples: int = 256) -> Array:
    """Numerically average D^(n/2)(q exp(i beta)) over the Hopf fibre."""
    if samples < 4:
        raise ValueError("at least four fibre samples required")
    out = np.zeros((n + 1, n + 1), dtype=complex)
    for beta in np.linspace(0.0, 2*np.pi, samples, endpoint=False):
        out += su2_irrep(q_mul(q, fibre_element(beta)), n)
    return out / samples


def fibre_projector_expected(n: int) -> Array:
    """Right-U(1) invariant weight projector; nonzero only for integer spin."""
    P = np.zeros((n + 1, n + 1), dtype=complex)
    if n % 2 == 0:
        P[n // 2, n // 2] = 1.0
    return P


def haar_schur_error(n: int = 1, count: int = 20000, seed: int = 1802) -> float:
    """Monte-Carlo max error in Schur orthogonality for one spin n/2.

    E[D_ab conj(D_cd)] = delta_ac delta_bd/(n+1), for normalized Haar measure.
    """
    qs = haar_s3_samples(count, seed)
    Ds = np.stack([su2_irrep(q, n) for q in qs])
    empirical = np.einsum("sij,skl->ijkl", Ds, Ds.conj(), optimize=True) / count
    expected = np.zeros_like(empirical)
    for a in range(n + 1):
        for b in range(n + 1):
            expected[a, b, a, b] = 1.0 / (n + 1)
    return float(np.max(np.abs(empirical - expected)))


def intertwiner_residual(
    rep_a: Callable[[Array], Array],
    rep_b: Callable[[Array], Array],
    T: Array,
    group_elements: Iterable[Array],
) -> float:
    """Max ||T rho_a(g) - rho_b(g) T||_F over supplied group elements."""
    T = np.asarray(T, dtype=complex)
    errors = [np.linalg.norm(T @ rep_a(g) - rep_b(g) @ T, ord="fro")
              for g in group_elements]
    return float(max(errors, default=0.0))


def gram_matrix(features: Array) -> Array:
    """Hermitian Gram matrix; rows are samples, columns are features."""
    X = np.asarray(features, dtype=complex)
    return X @ X.conj().T


def unitary_intertwiner_demo(seed: int = 1803) -> dict:
    """Construct two equivalent observer coordinates related by a unitary T."""
    rng = np.random.default_rng(seed)
    Z = rng.normal(size=(3, 3)) + 1j*rng.normal(size=(3, 3))
    Q, _ = np.linalg.qr(Z)
    T = Q
    qs = haar_s3_samples(8, seed + 1)
    group_elements = list(qs[:4])
    rep_a = lambda q: su2_irrep(q, 2)
    # T must be 3x3, matching spin-1 representation.
    rep_b = lambda q: T @ rep_a(q) @ T.conj().T
    residual = intertwiner_residual(rep_a, rep_b, T, group_elements)
    features = np.stack([rep_a(q).reshape(-1) for q in qs])
    mapped = features @ np.kron(T, T.conj()).T
    gram_error = float(np.linalg.norm(gram_matrix(features) - gram_matrix(mapped)))
    return {"intertwiner_residual": residual, "gram_matrix_error": gram_error}


def truncated_path_signature(points: Array, depth: int = 3) -> list[Array]:
    """Signature of a piecewise-linear R^d path, through tensor degree `depth`.

    Each list element is a tensor of shape (d,)*k. Degree zero is scalar [1].
    Uses Chen concatenation of segment exponentials; designed for small d/depth.
    """
    X = np.asarray(points, dtype=float)
    if X.ndim != 2 or X.shape[0] < 1:
        raise ValueError("points must have shape (time, dimension)")
    if depth < 0 or depth > 5:
        raise ValueError("depth must be between 0 and 5")
    d = X.shape[1]
    S = [np.array(1.0)] + [np.zeros((d,)*k, dtype=float) for k in range(1, depth + 1)]
    for dx in np.diff(X, axis=0):
        E = [np.array(1.0)]
        tensor_power = None
        for k in range(1, depth + 1):
            tensor_power = dx.copy() if k == 1 else np.tensordot(tensor_power, dx, axes=0)
            E.append(tensor_power / factorial(k))
        C = [np.array(1.0)]
        for k in range(1, depth + 1):
            total = np.zeros((d,)*k, dtype=float)
            for r in range(k + 1):
                left, right = S[r], E[k-r]
                total += np.tensordot(left, right, axes=0).reshape((d,)*k)
            C.append(total)
        S = C
    return S


def signature_error(a: list[Array], b: list[Array]) -> float:
    if len(a) != len(b):
        raise ValueError("signature depths differ")
    return float(np.sqrt(sum(np.linalg.norm(x-y)**2 for x, y in zip(a, b))))


def relational_distance(features: Array) -> Array:
    """Pairwise Euclidean distances in feature space (observer pseudometric)."""
    X = np.asarray(features, dtype=float)
    dif = X[:, None, :] - X[None, :, :]
    return np.linalg.norm(dif, axis=-1)


@dataclass(frozen=True)
class ObserverChart:
    name: str
    visible_coordinates: tuple[str, ...]
    lost_coordinates: tuple[str, ...]
    symmetry: str
    representation: str


OBSERVER_CHARTS = (
    ObserverChart("S3-lift", ("base", "fibre_phase"), (), "SU(2) left/right", "Wigner-D / Peter-Weyl"),
    ObserverChart("Hopf-base", ("base",), ("fibre_phase",), "right U(1) quotient", "spherical harmonics / integer-spin sector"),
    ObserverChart("Clock-free path", ("ordered path geometry",), ("absolute duration",), "increasing reparameterization", "path signature"),
    ObserverChart("Timed path", ("ordered path geometry", "elapsed-time coordinate"), (), "joint path reparameterization", "time-augmented path signature"),
    ObserverChart("Local event stream", ("event order", "relative intervals", "marks"), ("global epoch",), "local affine clock", "event graph / interval signature"),
)
