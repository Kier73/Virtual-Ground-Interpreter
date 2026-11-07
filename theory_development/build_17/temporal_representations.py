#!/usr/bin/env python3
"""Build 17 temporal representation probes (standard-library only).

This module compares symmetry-adapted summaries of one synthetic temporal
signal. It deliberately distinguishes invariant summaries from covariant
representations and from lossy descriptors.
"""
from __future__ import annotations

import cmath
import math
import statistics
from typing import Sequence

from harmonic_representations import (
    dft,
    graph_fourier,
    graph_laplacian,
    symmetric_jacobi_eigensystem,
    eigenvalue_multiplicity_groups,
    permute_square_matrix,
)


def relative_l2(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vectors must have equal lengths")
    den = math.sqrt(sum(float(x) ** 2 for x in a))
    if den <= 1e-15:
        return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b)))
    return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b))) / den


def complex_relative_l2(a: Sequence[complex], b: Sequence[complex]) -> float:
    if len(a) != len(b):
        raise ValueError("vectors must have equal lengths")
    den = math.sqrt(sum(abs(complex(x)) ** 2 for x in a))
    num = math.sqrt(sum(abs(complex(x)-complex(y)) ** 2 for x,y in zip(a,b)))
    return num / den if den > 1e-15 else num


def circular_shift(values: Sequence[float], shift: int) -> list[float]:
    n = len(values)
    if n == 0:
        raise ValueError("cannot shift an empty vector")
    s = shift % n
    return [float(values[(i-s) % n]) for i in range(n)]


def fourier_magnitude(values: Sequence[float]) -> list[float]:
    if not values:
        raise ValueError("signal must be non-empty")
    return [abs(v) for v in dft([complex(x) for x in values])]


def spectral_centroid(values: Sequence[float]) -> float:
    """Power-weighted DFT-bin centroid in cycles/sample (one-sided bins)."""
    mags = fourier_magnitude(values)
    n = len(mags)
    stop = n // 2 + 1
    powers = [mags[k] ** 2 for k in range(stop)]
    total = sum(powers)
    if total <= 1e-15:
        return 0.0
    return sum((k / n) * p for k, p in enumerate(powers)) / total


def stft_magnitude(values: Sequence[float], *, frame_size: int = 64,
                   hop: int = 16) -> list[list[float]]:
    """Circular Hann-window STFT magnitude, [frame][frequency_bin].

    Rectangular finite boundary semantics are explicit: frames wrap around
    the finite periodic record. This makes exact circular-shift covariance
    testable without adding a hidden padding convention.
    """
    n = len(values)
    if n == 0 or frame_size < 4 or hop < 1 or n % hop != 0:
        raise ValueError("require nonempty signal, frame_size>=4, hop>=1, N divisible by hop")
    if frame_size > n:
        raise ValueError("frame_size cannot exceed signal length")
    window = [0.5 - 0.5 * math.cos(2.0 * math.pi * j / frame_size)
              for j in range(frame_size)]
    out: list[list[float]] = []
    for start in range(0, n, hop):
        frame = [float(values[(start+j) % n]) * window[j] for j in range(frame_size)]
        spectrum = dft([complex(x) for x in frame])
        out.append([abs(z) for z in spectrum[:frame_size//2+1]])
    return out


def stft_shift_covariance_error(values: Sequence[float], shift: int, *,
                                frame_size: int = 64, hop: int = 16) -> float:
    if shift % hop:
        raise ValueError("for exact frame covariance, shift must be a multiple of hop")
    a = stft_magnitude(values, frame_size=frame_size, hop=hop)
    b = stft_magnitude(circular_shift(values, shift), frame_size=frame_size, hop=hop)
    frames = len(a)
    frame_shift = (shift // hop) % frames
    expected = [a[(i-frame_shift) % frames] for i in range(frames)]
    flat_expected = [x for row in expected for x in row]
    flat_actual = [x for row in b for x in row]
    return relative_l2(flat_expected, flat_actual)


def stationary_haar_detail_coefficients(values: Sequence[float], *,
                                         max_level: int = 5) -> list[list[float]]:
    """Undecimated periodic Haar-like detail coefficients at dyadic scales.

    At each level, compare the mean of the first half of a circular window
    with the second half, normalized by sqrt(window length). This is a
    redundant multiscale descriptor, not an orthonormal DWT and not a full
    wavelet-frame implementation.
    """
    n = len(values)
    if n == 0 or max_level < 1:
        raise ValueError("nonempty signal and positive max_level required")
    levels: list[list[float]] = []
    for level in range(1, max_level+1):
        width = 2 ** level
        if width > n:
            break
        half = width // 2
        norm = math.sqrt(width)
        coeffs = []
        for i in range(n):
            left = sum(float(values[(i+j) % n]) for j in range(half))
            right = sum(float(values[(i+half+j) % n]) for j in range(half))
            coeffs.append((left-right)/norm)
        levels.append(coeffs)
    return levels


def stationary_haar_detail_energies(values: Sequence[float], *,
                                    max_level: int = 5) -> list[float]:
    coeffs = stationary_haar_detail_coefficients(values, max_level=max_level)
    n = len(values)
    return [sum(c*c for c in level)/n for level in coeffs]


def log_mellin_magnitude(log_samples: Sequence[float]) -> list[float]:
    """Unitary discrete Mellin magnitude for samples uniform in u=log(t).

    This is the DFT of y(u)=f(exp(u)); it corresponds to the Mellin transform
    on L²(R+, dt/t), up to finite periodic sampling and normalization.
    """
    return fourier_magnitude(log_samples)


def positive_log_grid_signal(sample_count: int = 256) -> tuple[list[float], list[float]]:
    """Deterministic log-periodic positive-time signal and uniform log grid."""
    if sample_count < 32:
        raise ValueError("sample_count must be >=32")
    u0, period = -3.0, 6.0
    du = period / sample_count
    u = [u0+i*du for i in range(sample_count)]
    # A periodic set of unequal-width positive pulses in log time. The pattern
    # is not a set of global amplitude ranks or unique per-event labels.
    centers = [0.11, 0.39, 0.84, 1.23, 1.91, 2.14, 2.86, 3.51, 4.04, 4.72, 5.31]
    widths = [0.045,0.07,0.05,0.09,0.055,0.08,0.045,0.065,0.05,0.075,0.06]
    values = []
    for x in u:
        y = 0.0
        for j, (c,w) in enumerate(zip(centers,widths)):
            # Periodic Gaussian pulse in the log coordinate.
            d = min(abs(x-c), period-abs(x-c))
            y += math.exp(-0.5*(d/w)**2)
        values.append(y)
    return u, values


def interpolate_periodic(values: Sequence[float], position: float) -> float:
    n = len(values)
    p = position % n
    i0 = int(math.floor(p))
    frac = p-i0
    return (1-frac)*float(values[i0]) + frac*float(values[(i0+1)%n])


def time_dilate_log_samples(values: Sequence[float], sample_shift: int) -> list[float]:
    """Apply t -> exp(sample_shift*du)*t, a circular log-grid translation."""
    return circular_shift(values, sample_shift)


def gaussian_event_signal(sample_count: int = 512) -> tuple[list[float], list[int]]:
    """Same-shape event pulses; no event-specific amplitudes or mark ranks."""
    if sample_count < 128:
        raise ValueError("sample_count must be >=128")
    centers = [42, 66, 96, 128, 176, 213, 271, 319, 391, 447]
    sigma = 2.25
    out = []
    for i in range(sample_count):
        x = 0.0
        for center in centers:
            d = i-center
            x += math.exp(-0.5*(d/sigma)**2)
        out.append(x)
    return out, centers


def linear_interpolate(values: Sequence[float], position: float) -> float:
    n = len(values)
    if position < 0 or position > n-1:
        return 0.0
    i0 = int(math.floor(position))
    i1 = min(n-1, i0+1)
    frac = position-i0
    return (1-frac)*float(values[i0]) + frac*float(values[i1])


def dilate_signal_about_center(values: Sequence[float], factor: float) -> list[float]:
    if factor <= 0 or not math.isfinite(factor):
        raise ValueError("dilation factor must be finite and positive")
    n = len(values)
    center = (n-1)/2.0
    return [linear_interpolate(values, center+(i-center)/factor) for i in range(n)]


def quadratic_clock_map(t: float, duration: float, severity: float) -> float:
    """Strictly increasing phi(t)=t+a*T*(t/T)^2, a>=0."""
    if duration <= 0 or severity < 0:
        raise ValueError("duration must be positive and severity nonnegative")
    return t + severity*duration*(t/duration)**2


def warp_signal_quadratic(values: Sequence[float], severity: float) -> list[float]:
    """Resample x through monotone clock map; output uses uniform warped time."""
    n = len(values)
    duration = float(n-1)
    mapped = [quadratic_clock_map(float(i), duration, severity) for i in range(n)]
    end = mapped[-1]
    out = []
    j = 0
    for q in range(n):
        target = q*end/(n-1)
        while j+1 < n and mapped[j+1] < target:
            j += 1
        if j+1 >= n:
            out.append(float(values[-1]))
        else:
            span = mapped[j+1]-mapped[j]
            frac = (target-mapped[j])/span if span else 0.0
            out.append((1-frac)*float(values[j])+frac*float(values[j+1]))
    return out


def normalized_log_intervals(times: Sequence[float]) -> list[float]:
    if len(times) < 2:
        return []
    gaps = [float(b)-float(a) for a,b in zip(times,times[1:])]
    if any(g <= 0 for g in gaps):
        raise ValueError("event times must be strictly increasing")
    med = statistics.median(gaps)
    return [math.log(g/med) for g in gaps]


def event_graph(times: Sequence[float], *, motif_tolerance: float = 0.60) -> tuple[list[list[float]], list[float]]:
    """Path plus recurrence-motif graph; node signal is local log-gap mean."""
    if len(times) < 3:
        raise ValueError("at least three events required")
    gaps = [float(b)-float(a) for a,b in zip(times,times[1:])]
    if any(g <= 0 for g in gaps):
        raise ValueError("event times must be strictly increasing")
    med = statistics.median(gaps)
    z = [math.log(g/med) for g in gaps]
    motifs = [(z[i],z[i+1]) for i in range(len(z)-1)]
    n = len(times)
    adjacency = [[0.0]*n for _ in range(n)]
    for i in range(n-1):
        adjacency[i][i+1] = adjacency[i+1][i] = 1.0
    for i in range(len(motifs)):
        for j in range(i+3,len(motifs)):
            d = math.hypot(motifs[i][0]-motifs[j][0], motifs[i][1]-motifs[j][1])
            if d <= motif_tolerance:
                w = math.exp(-0.5*(d/max(motif_tolerance,1e-12))**2)
                a,b=i,j
                adjacency[a][b] += w
                adjacency[b][a] += w
    node_signal = [z[0]]
    for i in range(1,n-1):
        node_signal.append(0.5*(z[i-1]+z[i]))
    node_signal.append(z[-1])
    return adjacency, node_signal


def graph_spectral_signature(times: Sequence[float], *, motif_tolerance: float = 0.60) -> dict:
    adjacency, node_signal = event_graph(times, motif_tolerance=motif_tolerance)
    gf = graph_fourier(adjacency,node_signal)
    eigvals = gf["eigenvalues"]
    coeffs = gf["coefficients"]
    groups = eigenvalue_multiplicity_groups(eigvals,tolerance=1e-8)
    energy_groups = []
    offset = 0
    for group in groups:
        m = group["multiplicity"]
        energy_groups.append({
            "eigenvalue_mean": group["eigenvalue_mean"],
            "multiplicity": m,
            "projected_signal_energy": sum(coeffs[k]**2 for k in range(offset,offset+m)),
        })
        offset += m
    return {"adjacency":adjacency,"node_signal":node_signal,"motif_tolerance":motif_tolerance,"eigenvalues":eigvals,
            "eigenvalue_groups":groups,"spectral_energy_groups":energy_groups,
            "parseval_abs_error":gf["parseval_abs_error"],
            "reconstruction_max_abs_error":gf["reconstruction_max_abs_error"]}


def graph_relabel_spectral_signature(times: Sequence[float], permutation: Sequence[int], *, motif_tolerance: float = 0.60) -> dict:
    base = graph_spectral_signature(times, motif_tolerance=motif_tolerance)
    adjacency = permute_square_matrix(base["adjacency"],permutation)
    signal = [base["node_signal"][i] for i in permutation]
    gf = graph_fourier(adjacency,signal)
    groups = eigenvalue_multiplicity_groups(gf["eigenvalues"],tolerance=1e-8)
    energies=[]
    k=0
    for g in groups:
        m=g["multiplicity"]
        energies.append({"eigenvalue_mean":g["eigenvalue_mean"],
                         "multiplicity":m,
                         "projected_signal_energy":sum(gf["coefficients"][j]**2 for j in range(k,k+m))})
        k += m
    return {"eigenvalues":gf["eigenvalues"],"eigenvalue_groups":groups,
            "spectral_energy_groups":energies,
            "parseval_abs_error":gf["parseval_abs_error"]}


def spectral_group_distance(a: dict, b: dict) -> float:
    ga,gb=a["spectral_energy_groups"],b["spectral_energy_groups"]
    if len(ga)!=len(gb):
        return 1.0
    va=[]; vb=[]
    for x,y in zip(ga,gb):
        if x["multiplicity"] != y["multiplicity"]:
            return 1.0
        va.extend([x["eigenvalue_mean"],x["projected_signal_energy"]])
        vb.extend([y["eigenvalue_mean"],y["projected_signal_energy"]])
    return relative_l2(va,vb)


def permute_signal(values: Sequence[float], permutation: Sequence[int]) -> list[float]:
    if sorted(permutation)!=list(range(len(values))):
        raise ValueError("invalid permutation")
    return [float(values[i]) for i in permutation]


def graph_signature_permutation_diagnostic(times: Sequence[float], *, motif_tolerance: float = 0.60) -> dict:
    base=graph_spectral_signature(times, motif_tolerance=motif_tolerance)
    n=len(times)
    permutation=list(reversed(range(n)))
    rel=graph_relabel_spectral_signature(times,permutation,motif_tolerance=motif_tolerance)
    ev_err=max(abs(a-b) for a,b in zip(base["eigenvalues"],rel["eigenvalues"]))
    # Compare projector energy by grouped eigenvalue; ordering is sorted.
    eng_err=0.0
    if len(base["spectral_energy_groups"]) != len(rel["spectral_energy_groups"]):
        eng_err=float("inf")
    else:
        for a,b in zip(base["spectral_energy_groups"],rel["spectral_energy_groups"]):
            eng_err=max(eng_err,abs(a["projected_signal_energy"]-b["projected_signal_energy"]))
    return {"eigenvalue_max_abs_error":ev_err,
            "eigenspace_energy_max_abs_error":eng_err,
            "note":"Compare eigenspace energies, not individual eigenvector columns, because repeated eigenspaces admit basis rotations."}


def run_representation_comparison() -> dict:
    # A single unlabelled impulse train: all event pulses share the same shape
    # and amplitude, so no global event-mark rank can drive the conclusions.
    x, centers=gaussian_event_signal()
    shift=32
    x_shift=circular_shift(x,shift)
    x_dilate=dilate_signal_about_center(x,1.15)
    x_warp=warp_signal_quadratic(x,0.35)

    # Linear Fourier: exact invariance to circular translations, but not
    # invariance to a change of time scale. The centroid should move lower
    # under a widened signal.
    f0,fshift,fdilate,fwarp=(fourier_magnitude(v) for v in (x,x_shift,x_dilate,x_warp))
    centroid0=spectral_centroid(x)
    centroid_d=spectral_centroid(x_dilate)

    # STFT: not globally invariant as a coefficient array; it is covariant to
    # frame shifts (a column permutation for this aligned circular shift).
    stft_cov=stft_shift_covariance_error(x,shift)
    stft_base=stft_magnitude(x)
    stft_warp=stft_magnitude(x_warp)
    stft_warp_error=relative_l2([v for r in stft_base for v in r],
                                [v for r in stft_warp for v in r])

    # Undecimated Haar detail-energy descriptor: shift invariant after pooling
    # all circular translations; temporal dilation redistributes scale energy.
    haar0=stationary_haar_detail_energies(x,max_level=6)
    haarshift=stationary_haar_detail_energies(x_shift,max_level=6)
    haardilate=stationary_haar_detail_energies(x_dilate,max_level=6)
    haarshift_err=relative_l2(haar0,haarshift)
    haar_scale_moment=lambda e: sum((i+1)*v for i,v in enumerate(e))/max(sum(e),1e-15)

    # Mellin: unitary DFT along u=log(t) for a log-periodic positive-domain
    # pattern. Dilation by one eighth of the log-period rolls this sample grid.
    _,log_x=positive_log_grid_signal(256)
    mellin_shift=8
    log_x_dilated=time_dilate_log_samples(log_x,mellin_shift)
    mellin0=log_mellin_magnitude(log_x)
    mellin1=log_mellin_magnitude(log_x_dilated)

    # Event graph: use event times only, no amplitude/mark ranks. Affine clock
    # change preserves normalized log gaps and recurrence graph exactly.
    t0=[float(v) for v in centers]
    t_affine=[19.0+2.75*v for v in t0]
    t_nonlinear=[quadratic_clock_map(v,511.0,0.35) for v in t0]
    graph0=graph_spectral_signature(t0)
    graph_affine=graph_spectral_signature(t_affine)
    graph_nonlinear=graph_spectral_signature(t_nonlinear)
    graph_perm=graph_signature_permutation_diagnostic(t0)

    # Interval sequence: uniform affine clock maps disappear under median
    # normalization; nonlinear drift does not.
    intervals0=normalized_log_intervals(t0)
    intervals_aff=normalized_log_intervals(t_affine)
    intervals_nl=normalized_log_intervals(t_nonlinear)

    motif_threshold_sweep=[]
    for threshold in (0.30,0.45,0.60,0.80,1.00):
        ga=graph_spectral_signature(t0,motif_tolerance=threshold)
        gb=graph_spectral_signature(t_nonlinear,motif_tolerance=threshold)
        edge_count=lambda mat: sum(1 for i in range(len(mat)) for j in range(i+2,len(mat)) if mat[i][j]>0.0)
        motif_threshold_sweep.append({
            "motif_tolerance":threshold,
            "base_recurrence_edges":edge_count(ga["adjacency"]),
            "nonlinear_recurrence_edges":edge_count(gb["adjacency"]),
            "laplacian_spectrum_relative_difference":relative_l2(ga["eigenvalues"],gb["eigenvalues"]),
            "eigenspace_signature_distance":spectral_group_distance(ga,gb),
        })

    return {
        "build":17,
        "provenance":"synthetic_unlabelled_event_pulse_fixture_only",
        "synthetic_signal":{"sample_count":len(x),"event_count":len(centers),
            "event_pulse_amplitudes":"identical; no event-specific amplitude marks",
            "event_centers_sample_indices":centers},
        "transformations":{"circular_translation_samples":shift,
            "linear_time_dilation_factor":1.15,
            "nonlinear_clock_map":"phi(t)=t+0.35*T*(t/T)^2; strictly increasing",
            "log_time_dilation_samples":mellin_shift},
        "fourier":{"circular_shift_magnitude_relative_error":relative_l2(f0,fshift),
            "dilation_magnitude_relative_error_same_frequency_bins":relative_l2(f0,fdilate),
            "nonlinear_warp_magnitude_relative_error_same_frequency_bins":relative_l2(f0,fwarp),
            "spectral_centroid_base_cycles_per_sample":centroid0,
            "spectral_centroid_dilated_cycles_per_sample":centroid_d,
            "spectral_centroid_dilated_to_base_ratio":centroid_d/centroid0 if centroid0 else None,
            "interpretation":"Magnitude is invariant to circular translation; dilation changes frequency coordinates rather than preserving bins."},
        "stft":{"circular_shift_covariance_relative_error":stft_cov,
            "nonlinear_warp_unaligned_field_relative_error":stft_warp_error,
            "frame_count":len(stft_base),"frequency_bins_per_frame":len(stft_base[0]),
            "interpretation":"Aligned frame shifts permute columns; STFT is covariant/localized, not invariant as an indexed field."},
        "stationary_haar_detail_energy":{"base_by_level":haar0,
            "circular_shift_energy_relative_error":haarshift_err,
            "dilated_by_level":haardilate,
            "scale_moment_base":haar_scale_moment(haar0),
            "scale_moment_dilated":haar_scale_moment(haardilate),
            "interpretation":"Undecimated Haar-like detail energies are pooled over all circular positions, giving shift invariance; dilation redistributes scale energy. This is a descriptor, not an orthonormal DWT."},
        "mellin":{"transform_measure":"L2(R_+, dt/t), via uniform log-time coordinate u=log(t)",
            "log_grid_period":6.0,"sample_count":len(log_x),
            "dilation_factor":math.exp(6.0*mellin_shift/len(log_x)),
            "dilation_magnitude_relative_error":relative_l2(mellin0,mellin1),
            "interpretation":"Dilation acts as translation in log time; finite circular log-grid DFT magnitude is invariant to that shift. This is a periodic finite-window realization, not a claim about arbitrary boundaries."},
        "event_graph_fourier":{"affine_clock_eigenvalue_relative_error":relative_l2(graph0["eigenvalues"],graph_affine["eigenvalues"]),
            "affine_clock_eigenspace_energy_distance":spectral_group_distance(graph0,graph_affine),
            "nonlinear_clock_eigenvalue_relative_error":relative_l2(graph0["eigenvalues"],graph_nonlinear["eigenvalues"]),
            "nonlinear_clock_eigenspace_energy_distance":spectral_group_distance(graph0,graph_nonlinear),
            "node_relabeling":graph_perm,
            "graph_node_count":len(t0),
            "motif_tolerance":0.60,
            "base_recurrence_edge_count":sum(1 for i in range(len(graph0["adjacency"])) for j in range(i+2,len(graph0["adjacency"])) if graph0["adjacency"][i][j] > 0.0),
            "nonlinear_recurrence_edge_count":sum(1 for i in range(len(graph_nonlinear["adjacency"])) for j in range(i+2,len(graph_nonlinear["adjacency"])) if graph_nonlinear["adjacency"][i][j] > 0.0),
            "interpretation":"The chosen normalized-interval recurrence graph is invariant to affine time maps; nonlinear drift changes interval motifs. Laplacian spectra are node-relabel invariant but not complete graph identifiers."},
        "event_graph_threshold_sensitivity":motif_threshold_sweep,
        "interval_sequence":{"affine_clock_relative_error":relative_l2(intervals0,intervals_aff),
            "nonlinear_clock_relative_error":relative_l2(intervals0,intervals_nl),
            "base_log_intervals":intervals0,"nonlinear_log_intervals":intervals_nl},
        "caveats":[
            "All signals and event streams are generated fixtures; no physical sensor measurements were processed.",
            "The event graph is built from known synthetic event times, not a noisy peak detector.",
            "Finite DFT/STFT use circular boundary semantics.",
            "The Mellin test uses a log-periodic signal on a finite periodic log grid.",
            "Stationary Haar detail energies are redundant pooled descriptors, not a complete wavelet transform.",
            "Graph spectral signatures can collide for non-isomorphic graphs; they are not complete invariants."
        ]
    }
