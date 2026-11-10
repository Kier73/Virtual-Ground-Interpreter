"""Signal-native values and the Z/8Z character backend.

The runtime representation is a normalized complex phasor plus an observer
coordinate and a conservative phase-error bound. No semantic integer is stored.
"""
from __future__ import annotations

from dataclasses import dataclass
import cmath
import math
from typing import Final


OBSERVERS: Final[tuple[int, ...]] = (1, 3, 5, 7)
TAU: Final[float] = 2.0 * math.pi
_EPS: Final[float] = 1e-12


class ValueErrorVGI(ValueError):
    """Invalid signal value or unsupported observer transformation."""


class AmbiguousSymbolObservation(ValueErrorVGI):
    """The phase-error interval overlaps multiple 8-PSK symbol regions."""

    def __init__(self, candidates: tuple[int, ...], phase_error_bound: float):
        self.candidates = candidates
        self.phase_error_bound = phase_error_bound
        super().__init__(
            f"terminal symbol is indeterminate: candidates={candidates}, "
            f"phase_error_bound={phase_error_bound:.6g} rad"
        )


@dataclass(frozen=True, slots=True)
class SignalValue:
    """A signal-domain state.

    `phasor` is the payload after pilot-referenced calibration. `observer` is
    an odd unit modulo 8. `phase_error_bound` is a conservative absolute bound
    (radians) on residual phase error.

    The semantic symbol is intentionally absent from this object.
    """

    phasor: complex
    observer: int = 1
    phase_error_bound: float = 0.0

    def __post_init__(self) -> None:
        z = complex(self.phasor)
        if not (math.isfinite(z.real) and math.isfinite(z.imag)):
            raise ValueErrorVGI("phasor must have finite real and imaginary parts")
        if abs(abs(z) - 1.0) > 1e-7:
            raise ValueErrorVGI("phasor must be normalized to unit magnitude")
        if self.observer not in OBSERVERS:
            raise ValueErrorVGI(f"observer must be one of {OBSERVERS}")
        if not math.isfinite(self.phase_error_bound) or not 0.0 <= self.phase_error_bound <= math.pi:
            raise ValueErrorVGI("phase_error_bound must be finite and in [0, pi]")

    def to_dict(self) -> dict[str, float | int]:
        return {
            "real": float(self.phasor.real),
            "imag": float(self.phasor.imag),
            "observer": self.observer,
            "phase_error_bound": self.phase_error_bound,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SignalValue":
        try:
            return cls(
                complex(float(data["real"]), float(data["imag"])),
                int(data["observer"]),
                float(data.get("phase_error_bound", 0.0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueErrorVGI(f"invalid serialized signal value: {exc}") from exc


@dataclass(frozen=True, slots=True)
class EqualityDecision:
    """A robust equality decision with its geometric evidence."""

    result: bool | None
    distance_rad: float
    uncertainty_rad: float
    tolerance_rad: float

    @property
    def lower_bound_rad(self) -> float:
        return max(0.0, self.distance_rad - self.uncertainty_rad)

    @property
    def upper_bound_rad(self) -> float:
        return min(math.pi, self.distance_rad + self.uncertainty_rad)

    @property
    def margin_rad(self) -> float:
        return abs(self.distance_rad - self.tolerance_rad) - self.uncertainty_rad


class Signal8Backend:
    """Finite signal algebra for Z/8Z using four equivalent observers.

    Observer u represents semantic k as exp(2*pi*i*u*k/8). Reframing uses
    only a phasor power; arithmetic uses multiplication/conjugation.
    Integer observation is a terminal boundary operation.
    """

    domain_id = "signal.phase.cyclic.z8.v1"
    observer_profiles = OBSERVERS

    @staticmethod
    def _normalize(z: complex) -> complex:
        mag = abs(z)
        if not math.isfinite(mag) or mag <= _EPS:
            raise ValueErrorVGI("cannot normalize zero or non-finite phasor")
        return z / mag

    def encode_symbol(self, symbol: int, observer: int = 1, *, phase_error_bound: float = 0.0) -> SignalValue:
        """Encode an external symbolic input into the signal domain.

        This is an ingress operation, not an instruction used by arithmetic.
        """
        if isinstance(symbol, bool) or not isinstance(symbol, int) or not 0 <= symbol < 8:
            raise ValueErrorVGI("symbol must be an integer in [0, 7]")
        if observer not in OBSERVERS:
            raise ValueErrorVGI(f"observer must be one of {OBSERVERS}")
        z = cmath.exp(1j * TAU * ((observer * symbol) % 8) / 8.0)
        return SignalValue(self._normalize(z), observer, phase_error_bound)

    def possible_symbols(self, value: SignalValue) -> tuple[int, ...]:
        """Return every symbol whose decision sector intersects the phase bound."""
        phase = math.atan2(value.phasor.imag, value.phasor.real)
        reach = math.pi / 8.0 + value.phase_error_bound + _EPS
        possible = []
        for symbol in range(8):
            encoded = (value.observer * symbol) % 8
            centre = TAU * encoded / 8.0
            delta = abs(math.atan2(math.sin(phase - centre), math.cos(phase - centre)))
            if delta <= reach:
                possible.append(symbol)
        return tuple(possible)

    def observe_symbol(self, value: SignalValue) -> int:
        """Decode only when the declared phase bound identifies one symbol."""
        possible = self.possible_symbols(value)
        if len(possible) != 1:
            raise AmbiguousSymbolObservation(possible, value.phase_error_bound)
        return possible[0]

    def ingest_iq(self, signal: tuple[complex, ...] | list[complex],
                  pilot: tuple[complex, ...] | list[complex], observer: int = 1,
                  *, phase_error_bound: float = 0.0) -> SignalValue:
        """Calibrate an I/Q payload against its pilot and enter the value domain.

        Implements the pilot-referenced estimate used by the signal experiments:
            z_hat = mean(x[n] * conj(p[n]) / |p[n]|^2)
        The residual phase bound is supplied by the caller; this method does not
        infer a statistically calibrated confidence interval from samples.
        """
        if len(signal) != len(pilot) or len(signal) == 0:
            raise ValueErrorVGI("signal and pilot must have the same nonzero length")
        estimates: list[complex] = []
        for x, p in zip(signal, pilot):
            x, p = complex(x), complex(p)
            if not (math.isfinite(x.real) and math.isfinite(x.imag) and
                    math.isfinite(p.real) and math.isfinite(p.imag)):
                raise ValueErrorVGI("I/Q samples must be finite")
            energy = abs(p) ** 2
            if energy <= _EPS:
                raise ValueErrorVGI("pilot contains a zero-energy sample")
            estimates.append(x * p.conjugate() / energy)
        estimate = sum(estimates) / len(estimates)
        return SignalValue(self._normalize(estimate), observer, phase_error_bound)

    def emit_iq(self, value: SignalValue, pilot: tuple[complex, ...] | list[complex]) -> tuple[complex, ...]:
        """Render a calibrated state onto a supplied complex pilot/carrier."""
        if len(pilot) == 0:
            raise ValueErrorVGI("output pilot must be non-empty")
        return tuple(complex(p) * value.phasor for p in pilot)

    def reframe(self, value: SignalValue, target_observer: int) -> SignalValue:
        """Change observer coordinates without integer decoding."""
        if target_observer not in OBSERVERS:
            raise ValueErrorVGI(f"target observer must be one of {OBSERVERS}")
        if value.observer == target_observer:
            return value
        exponent = (target_observer * pow(value.observer, -1, 8)) % 8
        # Exponent is one of the odd units 1, 3, 5, 7.
        z = self._normalize(value.phasor ** exponent)
        error = min(math.pi, exponent * value.phase_error_bound)
        return SignalValue(z, target_observer, error)

    def _align(self, left: SignalValue, right: SignalValue) -> tuple[SignalValue, SignalValue]:
        if left.observer == right.observer:
            return left, right
        return left, self.reframe(right, left.observer)

    def add(self, left: SignalValue, right: SignalValue) -> SignalValue:
        """Implement modular addition by phasor multiplication."""
        a, b = self._align(left, right)
        return SignalValue(self._normalize(a.phasor * b.phasor), a.observer,
                           min(math.pi, a.phase_error_bound + b.phase_error_bound))

    def sub(self, left: SignalValue, right: SignalValue) -> SignalValue:
        """Implement modular subtraction by multiplication with conjugate."""
        a, b = self._align(left, right)
        return SignalValue(self._normalize(a.phasor * b.phasor.conjugate()), a.observer,
                           min(math.pi, a.phase_error_bound + b.phase_error_bound))

    def compare_equal(self, left: SignalValue, right: SignalValue,
                      tolerance_rad: float) -> EqualityDecision:
        """Robustly compare two signal states without decoding symbols.

        Returns None when the uncertainty interval overlaps the decision
        boundary. The interpreter traps on that indeterminate result by default.
        """
        if not math.isfinite(tolerance_rad) or not 0.0 <= tolerance_rad <= math.pi:
            raise ValueErrorVGI("equality tolerance must be in [0, pi]")
        a, b = self._align(left, right)
        relative = a.phasor * b.phasor.conjugate()
        distance = abs(math.atan2(relative.imag, relative.real))
        uncertainty = min(math.pi, a.phase_error_bound + b.phase_error_bound)
        lower = max(0.0, distance - uncertainty)
        upper = min(math.pi, distance + uncertainty)
        if upper <= tolerance_rad + _EPS:
            result: bool | None = True
        elif lower > tolerance_rad + _EPS:
            result = False
        else:
            result = None
        return EqualityDecision(result, distance, uncertainty, tolerance_rad)

    def compare_identity(self, value: SignalValue, tolerance_rad: float) -> EqualityDecision:
        identity = SignalValue(1.0 + 0.0j, value.observer, 0.0)
        return self.compare_equal(value, identity, tolerance_rad)
