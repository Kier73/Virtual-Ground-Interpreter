"""Build 19: joint endpoint-harmonic, path-signature and observer-kernel tests.

All experiments use deterministic synthetic quaternion trajectories.  The
path signature is the ambient Euclidean signature of the embedded path
(q in R^4, SO(3) matrices in R^9, or Hopf points in R^3), truncated at finite
level.  It is not claimed to be an intrinsic manifold signature.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import factorial
from typing import Iterable

import numpy as np

import relational_atlas as ra

Array = np.ndarray


def slerp(q0: Array, q1: Array, u: float) -> Array:
    """Shortest-arc great-circle interpolation on S^3."""
    a, b = ra.q_normalize(q0), ra.q_normalize(q1)
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    theta = float(np.arccos(dot))
    if theta < 1e-10:
        return ra.q_normalize((1.0-u)*a + u*b)
    # A near-antipodal pair has non-unique shortest geodesics; reject it rather
    # than allowing a numerically arbitrary path.
    if np.pi - theta < 1e-8:
        raise ValueError("slerp endpoints are nearly antipodal; choose an intermediate point")
    return ra.q_normalize(
        (np.sin((1.0-u)*theta)/np.sin(theta))*a
        + (np.sin(u*theta)/np.sin(theta))*b
    )


def sample_s3_polyline(vertices: Array, counts: Iterable[int]) -> Array:
    """Sample piecewise geodesic S^3 path; counts gives samples per segment."""
    V = np.asarray(vertices, dtype=float)
    C = list(counts)
    if V.ndim != 2 or V.shape[1] != 4 or len(V) < 2 or len(C) != len(V)-1:
        raise ValueError("vertices must be (m,4), with one segment count per edge")
    if any(int(c) < 1 for c in C):
        raise ValueError("each segment needs at least one interval")
    out: list[Array] = []
    for idx, c in enumerate(C):
        points = [slerp(V[idx], V[idx+1], u) for u in np.linspace(0.0, 1.0, int(c)+1)]
        out.extend(points if idx == 0 else points[1:])
    return np.asarray(out)


def canonical_s3_path(path: Array, subdivisions: int = 16, tolerance: float = 1e-9) -> Array:
    """Canonicalize samples of a piecewise-great-circle S^3 path.

    Collinear samples along the same shortest geodesic are removed, then each
    retained geodesic segment is resampled uniformly. This makes signatures
    independent of sampling density for the same declared geodesic polyline.
    It does not claim to infer an unknown continuous path from arbitrary data.
    """
    P = np.asarray(path, dtype=float)
    if P.ndim != 2 or P.shape[1] != 4 or len(P) < 1:
        raise ValueError("path must have shape (time,4)")
    if subdivisions < 1 or tolerance <= 0:
        raise ValueError("subdivisions must be positive and tolerance must be positive")
    P = np.stack([ra.q_normalize(q) for q in P])
    if len(P) == 1:
        return P.copy()

    anchors: list[Array] = [P[0].copy()]
    for point in P[1:]:
        point = point.copy()
        while len(anchors) >= 2:
            a, b = anchors[-2], anchors[-1]
            ab = ra.q_distance_s3(a, b)
            bp = ra.q_distance_s3(b, point)
            ap = ra.q_distance_s3(a, point)
            # A point b lies on the same forward shortest geodesic a->point
            # when distances add. Exclude the antipodal ambiguity.
            if ap < np.pi - 1e-8 and abs((ab + bp) - ap) <= tolerance:
                anchors.pop()
            else:
                break
        anchors.append(point)

    if len(anchors) == 1:
        return np.asarray(anchors)
    out: list[Array] = []
    for i in range(len(anchors)-1):
        segment = [slerp(anchors[i], anchors[i+1], u)
                   for u in np.linspace(0.0, 1.0, subdivisions+1)]
        out.extend(segment if i == 0 else segment[1:])
    return np.asarray(out)


def rotation_matrix(q: Array) -> Array:
    """SO(3) adjoint action of a unit quaternion, columns are rotated axes."""
    q = ra.q_normalize(q)
    basis = np.eye(3)
    R = np.zeros((3, 3), dtype=float)
    for j in range(3):
        pure = np.array([0.0, *basis[j]], dtype=float)
        R[:, j] = ra.q_mul(ra.q_mul(q, pure), ra.q_conj(q))[1:]
    # Suppress only roundoff; no polar projection is required for unit q.
    return R


def endpoint_harmonic_feature(q: Array, observer: str = "s3", max_n: int = 4) -> Array:
    """Finite Peter-Weyl endpoint feature adapted to an observer quotient.

    s3: all n=1..max_n (SU(2), including half-integer sectors)
    so3: even n only (antipodal quotient)
    hopf: even n, right zero-weight column only (U(1) fibre quotient)

    Each irreducible block has unit Frobenius norm before equal sector weighting.
    The returned vector is real-valued (real/imaginary parts concatenated).
    """
    if observer not in {"s3", "so3", "hopf"}:
        raise ValueError("observer must be 's3', 'so3', or 'hopf'")
    if max_n < 1 or max_n > 6:
        raise ValueError("max_n must be between 1 and 6")
    if observer == "s3":
        sectors = list(range(1, max_n + 1))
    else:
        sectors = list(range(2, max_n + 1, 2))
    if not sectors:
        raise ValueError("max_n selects no sectors for this observer")
    blocks: list[Array] = []
    for n in sectors:
        D = ra.su2_irrep(q, n)
        if observer == "hopf":
            D = D[:, n // 2:n // 2 + 1]
        D = D / np.linalg.norm(D, ord="fro")
        blocks.append(np.concatenate([D.real.reshape(-1), D.imag.reshape(-1)]))
    scale = 1.0 / np.sqrt(len(blocks))
    return scale * np.concatenate(blocks)


def observer_path(path: Array, observer: str, canonicalize: bool = True) -> Array:
    """Map a quaternion trajectory into the observer's visible coordinates."""
    P = np.asarray(path, dtype=float)
    if P.ndim != 2 or P.shape[1] != 4:
        raise ValueError("path must have shape (time,4)")
    P = np.stack([ra.q_normalize(q) for q in P])
    if canonicalize and observer in {"s3", "so3"}:
        P = canonical_s3_path(P)
    if observer == "s3":
        return P
    if observer == "so3":
        return np.stack([rotation_matrix(q).reshape(-1) for q in P])
    if observer == "hopf":
        return np.stack([ra.hopf_map(q) for q in P])
    raise ValueError("observer must be 's3', 'so3', or 'hopf'")


def signature_feature(points: Array, depth: int = 3) -> Array:
    """Weighted vectorization of signature levels 1..depth (degree 0 omitted)."""
    sig = ra.truncated_path_signature(points, depth=depth)
    blocks = [sig[k].reshape(-1) / np.sqrt(factorial(k)) for k in range(1, depth+1)]
    return np.concatenate(blocks).astype(float, copy=False)


def endpoint_feature_matrix(paths: list[Array], observer: str, max_n: int) -> Array:
    return np.stack([endpoint_harmonic_feature(p[-1], observer, max_n) for p in paths])


def path_feature_matrix(paths: list[Array], observer: str, depth: int) -> Array:
    return np.stack([signature_feature(observer_path(p, observer), depth) for p in paths])


def linear_gram(features: Array) -> Array:
    X = np.asarray(features, dtype=float)
    return X @ X.T


def kernel_distance_matrix(K: Array) -> Array:
    """Hilbert feature distance induced by a positive-semidefinite Gram matrix."""
    G = np.asarray(K, dtype=float)
    diag = np.diag(G)
    D2 = diag[:, None] + diag[None, :] - 2.0*G
    return np.sqrt(np.maximum(D2, 0.0))


def normalized_kernel(K: Array) -> Array:
    """Scale a PSD Gram matrix to mean diagonal one (without row normalization)."""
    G = np.asarray(K, dtype=float)
    mean_diag = float(np.mean(np.diag(G)))
    if not np.isfinite(mean_diag) or mean_diag <= 0:
        raise ValueError("kernel must have positive finite mean diagonal")
    return G / mean_diag


def representation_kernels(
    paths: list[Array], observer: str, max_n: int = 4, depth: int = 3
) -> dict[str, Array]:
    """Endpoint, path, and direct-sum joint observer kernels.

    The observer kernel is a Gram construction over the selected feature map;
    it supplies relational distances but no independent observations.
    """
    E = endpoint_feature_matrix(paths, observer, max_n)
    S = path_feature_matrix(paths, observer, depth)
    K_end = linear_gram(E)
    K_path = linear_gram(S)
    K_end_n = normalized_kernel(K_end)
    K_path_n = normalized_kernel(K_path)
    K_joint = 0.5*K_end_n + 0.5*K_path_n
    return {"endpoint": K_end_n, "path": K_path_n, "joint": K_joint}


def time_augmented_signature(path: Array, times: Array, observer: str = "s3", depth: int = 3) -> Array:
    P = observer_path(path, observer, canonicalize=False)
    T = np.asarray(times, dtype=float)
    if T.shape != (len(P),) or np.any(np.diff(T) < 0):
        raise ValueError("times must match path length and be nondecreasing")
    return signature_feature(np.column_stack([T, P]), depth)


def feature_distance(a: Array, b: Array) -> float:
    return float(np.linalg.norm(np.asarray(a, dtype=float)-np.asarray(b, dtype=float)))


def max_psd_violation(K: Array) -> float:
    eig = np.linalg.eigvalsh((K + K.T)/2.0)
    return float(max(0.0, -float(np.min(eig))))


def make_fixture_paths() -> dict[str, Array]:
    """Build deterministic S^3 paths covering separation and quotient cases."""
    q0 = np.array([1.0, 0.0, 0.0, 0.0])
    q1 = ra.q_normalize(np.array([0.5, 0.5, 0.5, 0.5]))
    q_mid = ra.q_normalize(np.array([0.5, -0.5, 0.5, -0.5]))
    q_alt = ra.q_normalize(np.array([0.15, 0.72, -0.31, 0.60]))
    q_extra = ra.q_normalize(np.array([-0.2, 0.4, 0.8, 0.3]))

    reference = sample_s3_polyline(np.stack([q0, q_mid, q1]), [8, 8])
    alternate = sample_s3_polyline(np.stack([q0, q_alt, q1]), [8, 8])

    # A right-fibre phase that changes continuously. Every projected Hopf
    # point is identical to the reference path, while the lift is different.
    betas = np.linspace(0.0, 0.8, len(reference))
    fibre_shifted = np.stack([
        ra.q_mul(q, ra.fibre_element(float(beta)))
        for q, beta in zip(reference, betas)
    ])

    # Same piecewise geodesic path, sampled at different densities.
    # Same sampled geometric path; only its independent time labels change.
    reparameterized = reference.copy()

    # Add an exact forward/reverse excursion at an existing path vertex.
    idx = len(reference)//2
    x = reference[idx]
    tree_excursion = np.vstack([
        reference[:idx+1], q_extra, x, reference[idx+1:]
    ])

    # The antipodal lift describes the same SO(3) rotations and same Hopf base.
    antipodal = -reference

    # Same state-space path; timing allocations are compared separately.
    timed_path = reference.copy()

    return {
        "reference": reference,
        "alternate_same_endpoint": alternate,
        "fibre_shifted": fibre_shifted,
        "reparameterized": reparameterized,
        "tree_like_excursion": tree_excursion,
        "antipodal_lift": antipodal,
        "timed_path": timed_path,
    }


def run_experiment() -> dict:
    paths_map = make_fixture_paths()
    paths = [paths_map[k] for k in paths_map]
    names = list(paths_map)
    idx = {name: i for i, name in enumerate(names)}
    ref = idx["reference"]

    all_kernels: dict[str, dict[str, Array]] = {}
    pairwise: dict[str, dict[str, dict[str, float]]] = {}
    for observer in ("s3", "so3", "hopf"):
        kernels = representation_kernels(paths, observer, max_n=4, depth=3)
        all_kernels[observer] = kernels
        pairwise[observer] = {}
        for case in names:
            j = idx[case]
            pairwise[observer][case] = {
                key: float(kernel_distance_matrix(K)[ref, j])
                for key, K in kernels.items()
            }

    # Endpoint redundancy: for fixed q(0), the first signature level is
    # exactly q(T)-q(0). Endpoint harmonics are a nonlinear coordinate of q(T).
    q_start = paths_map["reference"][0]
    q_end = paths_map["reference"][-1]
    sig1 = ra.truncated_path_signature(paths_map["reference"], depth=1)[1]
    endpoint_reconstruction_error = float(np.linalg.norm((q_start + sig1) - q_end))
    endpoint_harmonic_reconstruction_error = feature_distance(
        endpoint_harmonic_feature(q_start + sig1, "s3", 4),
        endpoint_harmonic_feature(q_end, "s3", 4),
    )

    # Pair separation by signature truncation level.
    depth_separation = {}
    for depth in range(1, 5):
        f_ref = signature_feature(observer_path(paths_map["reference"], "s3"), depth)
        f_alt = signature_feature(observer_path(paths_map["alternate_same_endpoint"], "s3"), depth)
        depth_separation[str(depth)] = feature_distance(f_ref, f_alt)

    # Geometric reparameterization versus timed representation.
    timed_points = paths_map["reference"]
    split = len(timed_points)//2
    times_uniform = np.linspace(0.0, 1.0, len(timed_points))
    times_skewed = np.concatenate([
        np.linspace(0.0, 0.9, split+1),
        np.linspace(0.9, 1.0, len(timed_points)-split)[1:],
    ])
    geom_uniform = signature_feature(observer_path(timed_points, "s3"), depth=3)
    geom_skewed = signature_feature(observer_path(timed_points, "s3"), depth=3)
    timed_uniform = time_augmented_signature(timed_points, times_uniform, "s3", 3)
    timed_skewed = time_augmented_signature(timed_points, times_skewed, "s3", 3)

    # Observer quotient checks: q and -q collapse for SO(3), and arbitrary
    # right-fibre phase changes collapse for Hopf-base features.
    q = paths_map["reference"][-1]
    q_fibre = ra.q_mul(q, ra.fibre_element(0.8))
    quotient_checks = {
        "s3_antipodal_endpoint_distance": feature_distance(
            endpoint_harmonic_feature(q, "s3", 4),
            endpoint_harmonic_feature(-q, "s3", 4)),
        "so3_antipodal_endpoint_distance": feature_distance(
            endpoint_harmonic_feature(q, "so3", 4),
            endpoint_harmonic_feature(-q, "so3", 4)),
        "hopf_fibre_endpoint_distance": feature_distance(
            endpoint_harmonic_feature(q, "hopf", 4),
            endpoint_harmonic_feature(q_fibre, "hopf", 4)),
        "hopf_projection_max_path_error": float(np.max(np.linalg.norm(
            np.stack([ra.hopf_map(x) for x in paths_map["reference"]])
            - np.stack([ra.hopf_map(x) for x in paths_map["fibre_shifted"]]), axis=1))),
    }

    # Kernel is exactly the Hilbert distance induced by its feature map.
    obs = "s3"
    sig_features = path_feature_matrix(paths, obs, depth=3)
    K_sig = linear_gram(sig_features)
    i_a, i_b = idx["reference"], idx["alternate_same_endpoint"]
    induced = kernel_distance_matrix(K_sig)[i_a, i_b]
    direct = feature_distance(sig_features[i_a], sig_features[i_b])
    kernel_geometry_error = abs(induced-direct)

    # Common left/right group action: both signature and endpoint kernels are
    # invariant when the same SU(2) isometry acts on every trajectory.
    a = ra.q_normalize(np.array([0.7, -0.2, 0.4, 0.5]))
    b = ra.q_normalize(np.array([0.8, 0.1, -0.3, 0.4]))
    moved = [np.stack([ra.q_mul(ra.q_mul(a, q), b) for q in p]) for p in paths]
    moved_kernels = representation_kernels(moved, "s3", max_n=4, depth=3)
    common_action_errors = {
        name: float(np.linalg.norm(all_kernels["s3"][name] - moved_kernels[name]))
        for name in ("endpoint", "path", "joint")
    }

    # Perturbation probe: small ambient perturbations, projected back to S^3.
    rng = np.random.default_rng(1901)
    noise_errors = {}
    for sigma in (1e-4, 1e-3, 1e-2):
        noisy = paths_map["reference"] + rng.normal(0.0, sigma, paths_map["reference"].shape)
        noisy = np.stack([ra.q_normalize(x) for x in noisy])
        clean_f = signature_feature(paths_map["reference"], depth=3)
        noisy_f = signature_feature(noisy, depth=3)
        noise_errors[str(sigma)] = feature_distance(clean_f, noisy_f)

    psd_violations = {
        observer: {
            key: max_psd_violation(K)
            for key, K in mats.items()
        }
        for observer, mats in all_kernels.items()
    }

    return {
        "status": "synthetic_joint_representation_experiment_complete",
        "data_provenance": "deterministic_synthetic_quaternion_paths",
        "path_names": names,
        "pairwise_kernel_distances_from_reference": pairwise,
        "signature_separation_by_depth_same_endpoints": depth_separation,
        "fixed_start_endpoint_reconstruction_error": endpoint_reconstruction_error,
        "fixed_start_endpoint_harmonic_reconstruction_error": endpoint_harmonic_reconstruction_error,
        "time_vs_geometry": {
            "geometric_signature_reparameterization_distance": feature_distance(geom_uniform, geom_skewed),
            "time_augmented_signature_distance": feature_distance(timed_uniform, timed_skewed),
        },
        "observer_quotient_checks": quotient_checks,
        "kernel_geometry_error": kernel_geometry_error,
        "common_left_right_action_kernel_errors": common_action_errors,
        "small_perturbation_signature_distances": noise_errors,
        "kernel_psd_violations": psd_violations,
        "interpretation": {
            "endpoint_harmonics": "symmetry-adapted endpoint coordinates; cannot distinguish different paths with the same endpoint",
            "path_signature": "captures ordered path information up to its tree-like equivalence; finite truncation is not complete",
            "observer_kernel": "organizes feature relationships as a PSD Gram geometry; it adds no information beyond its feature map",
            "joint_representation": "can combine complementary endpoint and path distinctions, but may contain redundant coordinates",
        },
    }


if __name__ == "__main__":
    import json
    from pathlib import Path
    out = run_experiment()
    target = Path(__file__).resolve().parent / "reports" / "build_19_results.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
