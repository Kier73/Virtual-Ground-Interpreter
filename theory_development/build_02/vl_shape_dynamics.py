#!/usr/bin/env python3
"""Build 02: shape, movement, observer, and geometric phase.

Standard-library-only exploratory model.  It separates:
  * path geometry (the unparameterized oriented curve),
  * temporal tone (how quickly the curve is traversed),
  * observer (which coordinates / connection are measured), and
  * intention (which measured properties are relevant to a comparison).

The connection used here is a deliberately simple toy model, not a model of a
particular biological organism or bicycle:
    A(x,y) = (-alpha*y/2, beta*x/2)
    dpsi = A_x dx + A_y dy.
For alpha=beta=1, the integral around a closed loop equals its signed area.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

Point = tuple[float, float]
Matrix2 = tuple[tuple[float, float], tuple[float, float]]


@dataclass(frozen=True)
class Observer:
    name: str
    projection: Matrix2 = ((1.0, 0.0), (0.0, 1.0))
    alpha: float = 1.0
    beta: float = 1.0

    def __post_init__(self) -> None:
        values = [self.alpha, self.beta, *self.projection[0], *self.projection[1]]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("observer parameters must be finite")
        if any(len(row) != 2 for row in self.projection):
            raise ValueError("projection must be 2x2")

    @property
    def det(self) -> float:
        a, b = self.projection[0]
        c, d = self.projection[1]
        return a * d - b * c

    def observe(self, p: Point) -> Point:
        x, y = p
        a, b = self.projection[0]
        c, d = self.projection[1]
        return (a * x + b * y, c * x + d * y)


@dataclass(frozen=True)
class Intention:
    """Weights over response features; weights express task relevance, not truth."""
    name: str
    weights: Mapping[str, float]

    def __post_init__(self) -> None:
        if not self.weights:
            raise ValueError("an intention must select at least one feature")
        if any((not math.isfinite(float(v)) or float(v) < 0.0) for v in self.weights.values()):
            raise ValueError("intention weights must be finite and non-negative")
        if not any(float(v) > 0 for v in self.weights.values()):
            raise ValueError("at least one intention weight must be positive")


@dataclass(frozen=True)
class Trace:
    times: tuple[float, ...]
    shape: tuple[Point, ...]
    observed: tuple[Point, ...]
    dpsi: tuple[float, ...]
    phase_rate: tuple[float, ...]


FEATURE_SCALES: dict[str, float] = {
    "signed_area": math.pi,
    "geometric_phase": math.pi,
    "path_length": 2.0 * math.pi,
    "winding": 1.0,
    "phase_rate_rms": 2.0,
    "phase_rate_cv": 1.0,
    "closure_error": 1.0,
    "radial_decay_rate": 1.0,
}


def ellipse_trace(
    a: float = 1.0,
    b: float = 1.0,
    n: int = 2048,
    timing: str = "uniform",
    warp: float = 0.45,
    direction: int = 1,
) -> tuple[tuple[float, ...], tuple[Point, ...]]:
    """Sample one oriented ellipse once; nonuniform timing preserves the same path.

    phi(t)=2*pi*(t + warp*sin(2*pi*t)/(2*pi)) has positive derivative when
    abs(warp)<1.  direction=-1 reverses the path orientation.
    """
    if a <= 0 or b <= 0 or n < 16:
        raise ValueError("a,b must be positive and n >= 16")
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or +1")
    if abs(warp) >= 1.0:
        raise ValueError("abs(warp) must be < 1 to preserve monotone timing")
    ts = tuple(i / n for i in range(n + 1))
    points: list[Point] = []
    for t in ts:
        if timing == "uniform":
            u = t
        elif timing == "warped":
            u = t + warp * math.sin(2.0 * math.pi * t) / (2.0 * math.pi)
        else:
            raise ValueError("timing must be 'uniform' or 'warped'")
        phi = direction * 2.0 * math.pi * u
        points.append((a * math.cos(phi), b * math.sin(phi)))
    return ts, tuple(points)


def stable_limit_cycle_trace(
    a: float = 1.0,
    b: float = 1.0,
    omega: float = 2.0 * math.pi,
    kappa: float = 0.7,
    delta: float = 0.35,
    duration: float = 8.0,
    n: int = 8192,
) -> tuple[tuple[float, ...], tuple[Point, ...], tuple[float, ...]]:
    """A stable limit-cycle neighbourhood in elliptical coordinates.

    rho(t)=1+delta*exp(-kappa*t), theta(t)=omega*t.
    The orbit rho=1 is the limiting cycle.  kappa is the transverse decay rate;
    phase is neutral (not contracting) in this idealized model.
    """
    if a <= 0 or b <= 0 or omega <= 0 or kappa <= 0 or duration <= 0 or n < 32:
        raise ValueError("positive a,b,omega,kappa,duration and n >= 32 required")
    if delta == 0 or not math.isfinite(delta):
        raise ValueError("delta must be finite and non-zero")
    ts = tuple(duration * i / n for i in range(n + 1))
    points: list[Point] = []
    errors: list[float] = []
    for t in ts:
        rho = 1.0 + delta * math.exp(-kappa * t)
        theta = omega * t
        points.append((a * rho * math.cos(theta), b * rho * math.sin(theta)))
        errors.append(rho - 1.0)
    return ts, tuple(points), tuple(errors)


def project_trace(points: Sequence[Point], observer: Observer) -> tuple[Point, ...]:
    return tuple(observer.observe(p) for p in points)


def discrete_line_integral(points: Sequence[Point], alpha: float = 1.0, beta: float = 1.0) -> float:
    """Midpoint line integral of A=(-alpha*y/2, beta*x/2) along a polyline."""
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx, dy = x1 - x0, y1 - y0
        xm, ym = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        ax, ay = -alpha * ym / 2.0, beta * xm / 2.0
        total += ax * dx + ay * dy
    return total


def signed_area(points: Sequence[Point]) -> float:
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(points, points[1:]))


def path_length(points: Sequence[Point]) -> float:
    return sum(math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(points, points[1:]))


def winding_number(points: Sequence[Point], eps: float = 1e-12) -> float:
    """Angle sum / 2pi; well-defined when the curve avoids the origin."""
    increments = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if math.hypot(x0, y0) <= eps or math.hypot(x1, y1) <= eps:
            raise ValueError("winding number undefined when the path meets the origin")
        cross = x0 * y1 - y0 * x1
        dot = x0 * x1 + y0 * y1
        increments += math.atan2(cross, dot)
    return increments / (2.0 * math.pi)


def trace_with_observer(
    times: Sequence[float], points: Sequence[Point], observer: Observer
) -> Trace:
    if len(times) != len(points) or len(times) < 2:
        raise ValueError("times and points must have equal length >= 2")
    obs = project_trace(points, observer)
    dpsi = []
    rates = []
    for i, ((x0, y0), (x1, y1)) in enumerate(zip(obs, obs[1:])):
        dt = times[i + 1] - times[i]
        if dt <= 0:
            raise ValueError("times must be strictly increasing")
        dx, dy = x1 - x0, y1 - y0
        xm, ym = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        ax, ay = -observer.alpha * ym / 2.0, observer.beta * xm / 2.0
        inc = ax * dx + ay * dy
        dpsi.append(inc)
        rates.append(inc / dt)
    return Trace(tuple(times), tuple(points), obs, tuple(dpsi), tuple(rates))


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def rms(values: Sequence[float]) -> float:
    return math.sqrt(mean([v * v for v in values])) if values else 0.0


def coefficient_of_variation(values: Sequence[float]) -> float:
    m = mean(values)
    if abs(m) < 1e-14:
        return 0.0
    variance = mean([(v - m) ** 2 for v in values])
    return math.sqrt(max(0.0, variance)) / abs(m)


def response_signature(trace: Trace, observer: Observer, radial_decay_rate: float | None = None) -> dict[str, float]:
    """Separate path invariants from temporal descriptors in a named signature."""
    phase = sum(trace.dpsi)
    rate_rms = rms(trace.phase_rate)
    return {
        "signed_area": signed_area(trace.observed),
        "geometric_phase": phase,
        "path_length": path_length(trace.observed),
        "winding": winding_number(trace.observed) if abs(observer.det) > 1e-12 else 0.0,
        "phase_rate_rms": rate_rms,
        "phase_rate_cv": coefficient_of_variation(trace.phase_rate),
        "closure_error": math.dist(trace.observed[0], trace.observed[-1]),
        "radial_decay_rate": float(radial_decay_rate) if radial_decay_rate is not None else 0.0,
    }


def intention_distance(a: Mapping[str, float], b: Mapping[str, float], intention: Intention) -> float:
    """Weighted Euclidean distance over intention-selected, scaled features."""
    terms = []
    for key, weight in intention.weights.items():
        if key not in a or key not in b or key not in FEATURE_SCALES:
            raise KeyError(f"unknown or missing feature {key!r}")
        scale = FEATURE_SCALES[key]
        terms.append(float(weight) * ((float(a[key]) - float(b[key])) / scale) ** 2)
    return math.sqrt(sum(terms) / sum(float(w) for w in intention.weights.values()))


def estimate_decay_rate(times: Sequence[float], radial_errors: Sequence[float]) -> float:
    """Estimate kappa from log(abs(rho-1)) = intercept - kappa*t via OLS."""
    if len(times) != len(radial_errors) or len(times) < 3:
        raise ValueError("at least three paired time/error points are required")
    usable = [(float(t), math.log(abs(float(e)))) for t, e in zip(times, radial_errors) if abs(e) > 1e-14]
    if len(usable) < 3:
        raise ValueError("insufficient non-zero radial errors")
    mt = mean([p[0] for p in usable])
    my = mean([p[1] for p in usable])
    denom = sum((t - mt) ** 2 for t, _ in usable)
    if denom <= 0:
        raise ValueError("time values must vary")
    slope = sum((t - mt) * (y - my) for t, y in usable) / denom
    return -slope


def moving_average(values: Sequence[float], window: int) -> tuple[float, ...]:
    """Centered moving average with edge-shortened windows; illustrative low-pass."""
    if window < 1 or window % 2 == 0:
        raise ValueError("window must be a positive odd integer")
    half = window // 2
    out = []
    for i in range(len(values)):
        lo, hi = max(0, i - half), min(len(values), i + half + 1)
        out.append(mean(values[lo:hi]))
    return tuple(out)


def mse(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("MSE requires equal non-empty sequences")
    return mean([(x - y) ** 2 for x, y in zip(a, b)])


def build_report() -> dict:
    n = 4096
    a, b = 1.2, 0.7
    obs_identity = Observer("identity")
    t_u, p_u = ellipse_trace(a, b, n, timing="uniform")
    t_w, p_w = ellipse_trace(a, b, n, timing="warped", warp=0.45)
    tr_u = trace_with_observer(t_u, p_u, obs_identity)
    tr_w = trace_with_observer(t_w, p_w, obs_identity)
    sig_u = response_signature(tr_u, obs_identity)
    sig_w = response_signature(tr_w, obs_identity)

    intents = {
        "shape_only": Intention("shape_only", {"signed_area": 1.0, "geometric_phase": 1.0, "path_length": 0.5, "winding": 1.0}),
        "temporal_tone": Intention("temporal_tone", {"phase_rate_rms": 1.0, "phase_rate_cv": 1.0}),
        "combined": Intention("combined", {"signed_area": 1.0, "geometric_phase": 1.0, "phase_rate_rms": 1.0, "phase_rate_cv": 1.0}),
    }

    observers = {
        "identity": Observer("identity"),
        "area_preserving_stretch": Observer("area_preserving_stretch", ((2.0, 0.0), (0.0, 0.5))),
        "contract_y": Observer("contract_y", ((1.0, 0.0), (0.0, 0.5))),
        "rotated": Observer("rotated", ((0.0, -1.0), (1.0, 0.0))),
        "rank_one_blind_y": Observer("rank_one_blind_y", ((1.0, 0.0), (0.0, 0.0))),
    }
    observer_results = {}
    for name, obs in observers.items():
        tr = trace_with_observer(t_u, p_u, obs)
        sig = response_signature(tr, obs)
        observer_results[name] = {
            "det_projection": obs.det,
            "signed_area": sig["signed_area"],
            "geometric_phase": sig["geometric_phase"],
            "winding": sig["winding"],
            "path_length": sig["path_length"],
        }

    # A radially perturbed stable limit cycle: estimate transverse return rate.
    kappa_true = 0.7
    ts, pts, radial_errors = stable_limit_cycle_trace(
        a=1.0, b=0.8, omega=2.0 * math.pi, kappa=kappa_true,
        delta=0.35, duration=8.0, n=8192,
    )
    # Downsample for report size while retaining the analytically known envelope.
    stride = 32
    kappa_est = estimate_decay_rate(ts[::stride], radial_errors[::stride])
    period = 2.0 * math.pi / (2.0 * math.pi)
    per_cycle_phase = []
    for cycle in range(8):
        lo_t, hi_t = cycle * period, (cycle + 1) * period
        start = min(range(len(ts)), key=lambda i: abs(ts[i] - lo_t))
        end = min(range(len(ts)), key=lambda i: abs(ts[i] - hi_t))
        seg = pts[start:end + 1]
        per_cycle_phase.append(discrete_line_integral(seg))

    # Noise-filter caution: high-frequency noise is removable here because we
    # deliberately place it outside the low-frequency signal band.
    n_noise = 2000
    clean = [math.sin(2.0 * math.pi * 2.0 * i / n_noise) for i in range(n_noise)]
    noise = [0.5 * math.sin(2.0 * math.pi * 80.0 * i / n_noise) for i in range(n_noise)]
    mixed = [x + z for x, z in zip(clean, noise)]
    filtered = moving_average(mixed, 25)
    high_frequency_signal = [math.sin(2.0 * math.pi * 80.0 * i / n_noise) for i in range(n_noise)]
    high_frequency_filtered = moving_average(high_frequency_signal, 25)
    high_frequency_gain = rms(high_frequency_filtered) / rms(high_frequency_signal)
    noise_report = {
        "raw_mse_to_clean_low_frequency_signal": mse(mixed, clean),
        "filtered_mse_to_clean_low_frequency_signal": mse(filtered, clean),
        "high_frequency_component_gain_after_same_filter": high_frequency_gain,
        "filter_window": 25,
        "desired_signal_cycles": 2,
        "added_noise_cycles": 80,
        "warning": "The filter suppresses the high-frequency component whether it is noise or desired signal. Separation only works here because the assumed signal and noise bands do not overlap.",
    }

    return {
        "build": "02",
        "title": "Shape, Movement, Observer, and Geometric Phase",
        "scope": "Synthetic geometric/dynamical experiment; no biological or bicycle model is claimed.",
        "ellipse": {"semi_axis_a": a, "semi_axis_b": b, "samples": n, "analytic_signed_area": math.pi * a * b},
        "time_reparameterization": {
            "uniform": sig_u,
            "warped": sig_w,
            "shape_intention_distance": intention_distance(sig_u, sig_w, intents["shape_only"]),
            "temporal_tone_distance": intention_distance(sig_u, sig_w, intents["temporal_tone"]),
            "combined_distance": intention_distance(sig_u, sig_w, intents["combined"]),
        },
        "observer_geometry": observer_results,
        "stable_limit_cycle": {
            "transverse_decay_rate_true": kappa_true,
            "transverse_decay_rate_estimated": kappa_est,
            "absolute_estimation_error": abs(kappa_true - kappa_est),
            "per_cycle_phase_accumulation": per_cycle_phase,
            "limiting_cycle_phase": math.pi * 1.0 * 0.8,
        },
        "filtering_tradeoff": noise_report,
        "interpretation": {
            "path_invariant": "The closed-loop integral is invariant to monotone time reparameterization when the same oriented path and connection are used.",
            "temporal_tone": "The time-resolved phase-rate profile changes under nonuniform traversal speed.",
            "observer": "A rank-deficient observation map collapses a dimension and can erase the loop/phase information.",
            "intention": "An intention selects which response coordinates contribute to a comparison; it does not alter the raw measurements.",
            "stability": "The transverse error decays exponentially toward the limiting cycle in this model.",
        },
    }


def main() -> None:
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
