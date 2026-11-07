#!/usr/bin/env python3
"""Build 16 harmonic representations: finite DFT and graph Fourier tools.

Standard-library implementation intended for transparent, small test cases.
The DFT uses the unitary 1/sqrt(N) convention. The graph transform uses an
orthonormal eigensystem of a real symmetric combinatorial graph Laplacian.
"""
from __future__ import annotations

import cmath
import math
from typing import Sequence

ComplexVector = Sequence[complex]
Matrix = list[list[float]]


def dft(values: Sequence[complex]) -> list[complex]:
    """Unitary forward DFT: X[k] = N^-1/2 sum_n x[n] exp(-2πikn/N)."""
    n = len(values)
    if n == 0:
        raise ValueError("DFT requires at least one sample")
    scale = 1.0 / math.sqrt(n)
    return [scale * sum(complex(values[j]) * cmath.exp(-2j * math.pi * k * j / n)
                         for j in range(n)) for k in range(n)]


def idft(coefficients: Sequence[complex]) -> list[complex]:
    """Unitary inverse DFT, with the positive-exponent convention."""
    n = len(coefficients)
    if n == 0:
        raise ValueError("inverse DFT requires at least one coefficient")
    scale = 1.0 / math.sqrt(n)
    return [scale * sum(complex(coefficients[k]) * cmath.exp(2j * math.pi * k * j / n)
                         for k in range(n)) for j in range(n)]


def inner_product(x: Sequence[complex], y: Sequence[complex]) -> complex:
    if len(x) != len(y):
        raise ValueError("vectors must have equal length")
    return sum(complex(a).conjugate() * complex(b) for a, b in zip(x, y))


def norm_squared(x: Sequence[complex]) -> float:
    return float(inner_product(x, x).real)


def fourier_diagnostics(values: Sequence[complex]) -> dict:
    """Check reconstruction, energy, inner product and fourth power identity."""
    coeffs = dft(values)
    reconstructed = idft(coeffs)
    # F^4 = I for the chosen DFT matrix. This is checked on the same vector.
    f1 = dft(values)
    f2 = dft(f1)
    f3 = dft(f2)
    f4 = dft(f3)
    return {
        "sample_count": len(values),
        "input_norm_squared": norm_squared(values),
        "frequency_norm_squared": norm_squared(coeffs),
        "parseval_abs_error": abs(norm_squared(values) - norm_squared(coeffs)),
        "reconstruction_max_abs_error": max((abs(complex(a)-b) for a, b in zip(values, reconstructed)), default=0.0),
        "fourth_power_identity_max_abs_error": max((abs(complex(a)-b) for a, b in zip(values, f4)), default=0.0),
        "transform_convention": "unitary_forward_N^-1/2_negative_exponent_inverse_positive_exponent",
    }


def circular_shift(values: Sequence[complex], shift: int) -> list[complex]:
    n = len(values)
    if not n:
        raise ValueError("cannot shift an empty vector")
    s = shift % n
    return [complex(values[(j - s) % n]) for j in range(n)]


def spectrum_magnitude(values: Sequence[complex]) -> list[float]:
    return [abs(v) for v in dft(values)]


def symmetric_jacobi_eigensystem(matrix: Sequence[Sequence[float]], *,
                                  tolerance: float = 1e-12,
                                  max_sweeps: int = 100) -> tuple[list[float], Matrix]:
    """Eigenvalues and orthonormal eigenvectors (columns) for symmetric A.

    Cyclic/max-pivot Jacobi rotations are sufficient for the small graphs used
    here. Eigenvalues are sorted ascending and corresponding eigenvectors are
    returned as columns in the row-major matrix `vectors[row][mode]`.
    """
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("matrix must be non-empty and square")
    a = [[float(matrix[i][j]) for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(n):
            if not math.isfinite(a[i][j]):
                raise ValueError("matrix entries must be finite")
            if abs(a[i][j] - a[j][i]) > 1e-10:
                raise ValueError("matrix must be symmetric")
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    for _ in range(max_sweeps * max(1, n * n)):
        p, q, largest = 0, 0, 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(a[i][j]) > largest:
                    p, q, largest = i, j, abs(a[i][j])
        if largest <= tolerance:
            break
        apq = a[p][q]
        tau = (a[q][q] - a[p][p]) / (2.0 * apq)
        t = (1.0 if tau >= 0 else -1.0) / (abs(tau) + math.sqrt(1.0 + tau*tau))
        c = 1.0 / math.sqrt(1.0 + t*t)
        s = t * c
        app, aqq = a[p][p], a[q][q]
        a[p][p] = app - t * apq
        a[q][q] = aqq + t * apq
        a[p][q] = a[q][p] = 0.0
        for k in range(n):
            if k != p and k != q:
                akp, akq = a[k][p], a[k][q]
                a[k][p] = a[p][k] = c*akp - s*akq
                a[k][q] = a[q][k] = s*akp + c*akq
        for k in range(n):
            vkp, vkq = v[k][p], v[k][q]
            v[k][p] = c*vkp - s*vkq
            v[k][q] = s*vkp + c*vkq
    else:
        raise RuntimeError("Jacobi eigensolver did not converge")

    order = sorted(range(n), key=lambda i: a[i][i])
    eigenvalues = [a[i][i] for i in order]
    eigenvectors = [[v[row][col] for col in order] for row in range(n)]
    return eigenvalues, eigenvectors


def graph_laplacian(adjacency: Sequence[Sequence[float]]) -> Matrix:
    """Combinatorial Laplacian L=D-A for an undirected weighted graph."""
    n = len(adjacency)
    if n == 0 or any(len(row) != n for row in adjacency):
        raise ValueError("adjacency must be non-empty and square")
    a = [[float(adjacency[i][j]) for j in range(n)] for i in range(n)]
    for i in range(n):
        if abs(a[i][i]) > 1e-12:
            raise ValueError("self-loops are not supported in this Laplacian builder")
        for j in range(n):
            if not math.isfinite(a[i][j]) or a[i][j] < 0:
                raise ValueError("edge weights must be finite and nonnegative")
            if abs(a[i][j] - a[j][i]) > 1e-10:
                raise ValueError("adjacency must be symmetric")
    degrees = [sum(row) for row in a]
    return [[(degrees[i] if i == j else 0.0) - a[i][j] for j in range(n)] for i in range(n)]


def graph_fourier(adjacency: Sequence[Sequence[float]],
                  signal: Sequence[float]) -> dict:
    """Graph Fourier transform via an orthonormal Laplacian eigenbasis."""
    n = len(adjacency)
    if len(signal) != n:
        raise ValueError("signal length must equal graph node count")
    lap = graph_laplacian(adjacency)
    eigenvalues, u = symmetric_jacobi_eigensystem(lap)
    x = [float(z) for z in signal]
    coeffs = [sum(u[row][k] * x[row] for row in range(n)) for k in range(n)]
    reconstructed = [sum(u[row][k] * coeffs[k] for k in range(n)) for row in range(n)]
    input_energy = sum(z*z for z in x)
    coeff_energy = sum(z*z for z in coeffs)
    return {
        "eigenvalues": eigenvalues,
        "eigenvectors_columns": u,
        "coefficients": coeffs,
        "reconstruction": reconstructed,
        "input_energy": input_energy,
        "spectral_energy": coeff_energy,
        "parseval_abs_error": abs(input_energy-coeff_energy),
        "reconstruction_max_abs_error": max((abs(x[i]-reconstructed[i]) for i in range(n)), default=0.0),
        "laplacian": lap,
    }


def permute_square_matrix(matrix: Sequence[Sequence[float]], permutation: Sequence[int]) -> Matrix:
    n = len(matrix)
    if sorted(permutation) != list(range(n)):
        raise ValueError("permutation must contain each index exactly once")
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    return [[float(matrix[permutation[i]][permutation[j]]) for j in range(n)] for i in range(n)]


def eigenvalue_multiplicity_groups(values: Sequence[float], *, tolerance: float = 1e-8) -> list[dict]:
    """Group adjacent sorted eigenvalues; basis vectors in a repeated eigenspace
    are not individually canonical, even though the eigenspace is.
    """
    if not values:
        return []
    groups = []
    start = 0
    for i in range(1, len(values)+1):
        if i == len(values) or abs(values[i]-values[start]) > tolerance:
            group = list(values[start:i])
            groups.append({"eigenvalue_mean": sum(group)/len(group), "multiplicity": len(group)})
            start = i
    return groups


def event_graph_adjacency(event_graph: dict, *, observer_prefix: str = "L") -> list[list[float]]:
    """Convert a Build-15 observer-local subgraph into a simple weighted graph.

    Successor edges have unit weight. Recurrence edges receive an RBF weight
    exp(-motif_distance^2 / 2). Cross-observer correspondence edges are omitted.
    """
    nodes = [node for node in event_graph["nodes"] if node["id"].startswith(observer_prefix + ":")]
    nodes.sort(key=lambda node: node["local_index"])
    n = len(nodes)
    if n == 0:
        raise ValueError("observer subgraph has no nodes")
    index = {node["id"]: i for i, node in enumerate(nodes)}
    a = [[0.0] * n for _ in range(n)]
    for edge in event_graph["edges"]:
        src, dst = edge["source"], edge["target"]
        if src not in index or dst not in index:
            continue
        if edge["type"] == "successor":
            weight = 1.0
        elif edge["type"] == "recurrence":
            d = float(edge.get("motif_distance", 0.0))
            weight = math.exp(-0.5*d*d)
        else:
            continue
        i, j = index[src], index[dst]
        a[i][j] += weight
        a[j][i] += weight
    return a
