#!/usr/bin/env python3
"""Dynamic codonic response experiment using stable AR(2) laws.

This module asks whether a codonic law's response to sinusoidal probes has a
repeatable spectral signature, and whether its pole parameters can be recovered
from that signature. It is a mathematical signal-processing experiment, not a
biological or emotional model.
"""
from __future__ import annotations

from dataclasses import dataclass
import cmath
import json
import math
from typing import Mapping, Sequence

from vl_response_geometry import Expr, Observer, default_registry, seed_identity, norm, normalize, dot


def eval_variables(expr: Expr, variables: Mapping[str, float], registry) -> float:
    if expr.op == "$var":
        if expr.value not in variables:
            raise KeyError(f"Missing variable {expr.value!r}")
        return float(variables[expr.value])
    if expr.op == "$const":
        return float(expr.value)
    spec = registry[expr.op]
    if len(expr.args) != spec.arity:
        raise ValueError(f"{expr.op} expects {spec.arity} arguments")
    args = [eval_variables(arg, variables, registry) for arg in expr.args]
    value = float(spec.fn(*args))
    if not math.isfinite(value):
        raise ValueError(f"Non-finite result from {expr.op}")
    return value


@dataclass(frozen=True)
class AR2Seed:
    radius: float
    omega0: float

    def __post_init__(self):
        if not (0.0 < self.radius < 1.0):
            raise ValueError("radius must be strictly between 0 and 1 for stable oscillatory poles")
        if not (0.0 < self.omega0 < math.pi):
            raise ValueError("omega0 must be between 0 and pi")

    @property
    def a1(self) -> float:
        return 2.0 * self.radius * math.cos(self.omega0)

    @property
    def a2(self) -> float:
        return -(self.radius ** 2)

    def codonic_law(self) -> Expr:
        """x_t = a1*x_(t-1) + a2*x_(t-2) + u_t, using local ad/mx codons."""
        c, v, call = Expr.const, Expr.var, Expr.call
        term1 = call("mx", c(self.a1), v("x1"))
        term2 = call("mx", c(self.a2), v("x2"))
        return call("ad", term1, call("ad", term2, v("u")))

    def poles(self) -> tuple[complex, complex]:
        return (
            self.radius * cmath.exp(1j * self.omega0),
            self.radius * cmath.exp(-1j * self.omega0),
        )

    def identity(self) -> dict[str, str]:
        return seed_identity(self.codonic_law(), default_registry())


def analytic_transfer(seed: AR2Seed, omega: float) -> complex:
    z1 = cmath.exp(-1j * omega)
    z2 = z1 * z1
    denominator = 1.0 - seed.a1 * z1 - seed.a2 * z2
    if abs(denominator) < 1e-14:
        raise ZeroDivisionError("Transfer function singular on the evaluation grid")
    return 1.0 / denominator


def simulate_gain(seed: AR2Seed, drive_omega: float, n_samples: int = 12000) -> tuple[float, float]:
    """Estimate steady-state gain and phase by least-squares sine/cosine fit."""
    if n_samples < 1000:
        raise ValueError("n_samples must be >= 1000")
    law = seed.codonic_law()
    registry = default_registry()
    x1 = x2 = 0.0
    ys = []
    for t in range(n_samples):
        u = math.sin(drive_omega * t)
        y = eval_variables(law, {"x1": x1, "x2": x2, "u": u}, registry)
        x2, x1 = x1, y
        if t >= n_samples // 2:
            ys.append((t, y))
    ss = sum(math.sin(drive_omega * t) ** 2 for t, _ in ys)
    cc = sum(math.cos(drive_omega * t) ** 2 for t, _ in ys)
    sc = sum(math.sin(drive_omega * t) * math.cos(drive_omega * t) for t, _ in ys)
    sy = sum(math.sin(drive_omega * t) * y for t, y in ys)
    cy = sum(math.cos(drive_omega * t) * y for t, y in ys)
    det = ss * cc - sc * sc
    if abs(det) < 1e-12:
        raise ArithmeticError("Sine/cosine regression is ill-conditioned")
    a = (sy * cc - cy * sc) / det
    b = (cy * ss - sy * sc) / det
    return math.hypot(a, b), math.atan2(b, a)


def unwrap_phase(phases: Sequence[float]) -> list[float]:
    if not phases:
        return []
    result = [float(phases[0])]
    offset = 0.0
    for prev_raw, raw in zip(phases, phases[1:]):
        delta = raw - prev_raw
        if delta > math.pi:
            offset -= 2.0 * math.pi
        elif delta < -math.pi:
            offset += 2.0 * math.pi
        result.append(raw + offset)
    return result


def orthogonal_basis(xs: Sequence[float]) -> tuple[tuple[float, ...], ...]:
    raw = [
        [1.0 for _ in xs],
        [x for x in xs],
        [x * x for x in xs],
        [math.sin(2.0 * math.pi * x) for x in xs],
    ]
    basis = []
    for vector in raw:
        residual = list(vector)
        for q in basis:
            proj = dot(residual, q)
            residual = [a - proj * b for a, b in zip(residual, q)]
        unit = normalize(residual)
        if unit is None:
            raise RuntimeError("Dependent spectral feature basis")
        basis.append(unit)
    return tuple(basis)


@dataclass(frozen=True)
class SpectralResponse:
    frequencies: tuple[float, ...]
    gains: tuple[float, ...]
    phases: tuple[float, ...]
    features: tuple[float, float, float, float]
    q_resp: tuple[float, float, float, float] | None
    peak_frequency: float
    peak_gain: float


def spectral_response(
    seed: AR2Seed,
    observer: Observer | None = None,
    n_freq: int = 129,
) -> SpectralResponse:
    """Measure a transfer curve and compress it to an observer-specific S^3 point.

    Four orthogonal modes describe log-gain over normalized frequency:
    DC, linear tilt, curvature, and oscillatory variation. The full curves are
    retained alongside the projection, so the projection can be audited.
    """
    if n_freq < 17 or n_freq % 2 == 0:
        raise ValueError("n_freq must be odd and at least 17")
    observer = observer or Observer.identity("balanced")
    freqs = tuple(0.025 + (math.pi - 0.05) * i / (n_freq - 1) for i in range(n_freq))
    hs = [analytic_transfer(seed, w) for w in freqs]
    gains = tuple(abs(h) for h in hs)
    phases = tuple(cmath.phase(h) for h in hs)
    log_gains = tuple(math.log(max(g, 1e-15)) for g in gains)
    normalized_freqs = tuple(w / math.pi for w in freqs)
    basis = orthogonal_basis(normalized_freqs)
    coeffs = tuple(dot(log_gains, b) for b in basis)
    features = observer.observe(coeffs)
    amplitude = norm(features)
    q_resp = normalize(features)
    peak_i = max(range(len(gains)), key=gains.__getitem__)
    return SpectralResponse(
        frequencies=freqs,
        gains=gains,
        phases=phases,
        features=tuple(features),
        q_resp=q_resp,
        peak_frequency=freqs[peak_i],
        peak_gain=gains[peak_i],
    )


def demo() -> dict:
    seeds = {
        "low_mode": AR2Seed(0.92, 0.35),
        "mid_mode": AR2Seed(0.92, 1.10),
        "high_mode": AR2Seed(0.92, 2.20),
        "low_damped": AR2Seed(0.65, 0.35),
        "mid_damped": AR2Seed(0.65, 1.10),
    }
    observers = {
        "balanced": Observer.identity("balanced"),
        "low_frequency_sensitive": Observer.diagonal("low_frequency_sensitive", (2.0, 1.0, 0.5, 0.5)),
        "oscillation_sensitive": Observer.diagonal("oscillation_sensitive", (0.5, 0.5, 1.0, 2.0)),
    }
    out = {}
    for oname, obs in observers.items():
        out[oname] = {}
        for name, seed in seeds.items():
            result = spectral_response(seed, obs)
            out[oname][name] = {
                "seed_sigma64": seed.identity()["sigma64"],
                "radius": seed.radius,
                "omega0": seed.omega0,
                "poles": [[p.real, p.imag] for p in seed.poles()],
                "features": list(result.features),
                "q_resp": list(result.q_resp) if result.q_resp else None,
                "peak_frequency": result.peak_frequency,
                "peak_gain": result.peak_gain,
            }
    verification = {}
    for name, seed in {"low_mode": seeds["low_mode"], "mid_mode": seeds["mid_mode"], "high_mode": seeds["high_mode"]}.items():
        probe = seed.omega0
        measured_gain, measured_phase = simulate_gain(seed, probe)
        theoretical = analytic_transfer(seed, probe)
        verification[name] = {
            "probe_frequency": probe,
            "measured_gain": measured_gain,
            "analytic_gain": abs(theoretical),
            "relative_gain_error": abs(measured_gain - abs(theoretical)) / abs(theoretical),
            "measured_phase": measured_phase,
            "analytic_phase": cmath.phase(theoretical),
        }
    return {
        "experiment": "VL Dynamic Codonic Response / AR(2) resonance probe 0.1",
        "equation": "x[t] = 2*r*cos(omega0)*x[t-1] - r^2*x[t-2] + u[t]",
        "pole_pair": "r*exp(+/- i*omega0)",
        "scope": "Synthetic stable linear systems; mathematical frequency response only.",
        "observers": out,
        "simulation_vs_analytic": verification,
    }


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2, sort_keys=True))
