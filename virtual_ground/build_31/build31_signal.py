"""Build 31: compositional signal algebra and observer-coordinate changes.

The payload remains a calibrated complex signal state between operations.
Integer decoding is reserved for terminal observation and test oracles.
This is a finite, numerical complex-baseband model over Z/8Z.
"""
from __future__ import annotations

from dataclasses import dataclass
import cmath
import math
import random
from typing import Iterable, Sequence

# Exact, unchanged Build 30 phase/FSK primitives are vendored as signal_code.py.
from signal_code import (
    PhaseOperand,
    SignalCodeError,
    decode_phase_symbol,
    encode_phase_operand,
    encode_output_carrier,
    phase_symbol,
    recover_phase_symbol,
)

MODULUS = 8
OBSERVER_UNITS = (1, 3, 5, 7)


class Build31Error(ValueError):
    """Invalid signal state, observer coordinate, or operation."""


@dataclass(frozen=True)
class SignalState:
    """A pilot-referenced phase signal and its current observer coordinate.

    ``observer`` is an odd unit modulo 8. The represented semantic value k is
    carried as chi_u(k) = exp(2*pi*i*u*k/8). No integer payload is stored.
    """
    operand: PhaseOperand
    observer: int = 1

    def __post_init__(self) -> None:
        if self.observer not in OBSERVER_UNITS:
            raise Build31Error("observer coordinate must be one of 1, 3, 5, 7")
        if len(self.operand.signal) != len(self.operand.pilot) or not self.operand.signal:
            raise Build31Error("signal and pilot must be non-empty and equal length")


@dataclass(frozen=True)
class ChannelSpec:
    """Scalar complex channel with an optional pilot-reference phase error.

    The data path is multiplied by gain*exp(i*phase). The pilot path is
    multiplied by gain*exp(i*(phase-calibration_error)). Consequently the
    pilot-referenced estimate carries +calibration_error residual phase.
    """
    gain: float = 1.0
    phase: float = 0.0
    calibration_error: float = 0.0
    noise_sigma: float = 0.0
    seed: int = 0

    def __post_init__(self) -> None:
        values = (self.gain, self.phase, self.calibration_error, self.noise_sigma)
        if not all(math.isfinite(x) for x in values):
            raise Build31Error("channel parameters must be finite")
        if self.gain <= 0 or self.noise_sigma < 0:
            raise Build31Error("channel gain must be positive and noise non-negative")


def inverse_unit_mod8(unit: int) -> int:
    if unit not in OBSERVER_UNITS:
        raise Build31Error("observer coordinate must be an odd unit modulo 8")
    return next(v for v in OBSERVER_UNITS if (unit * v) % MODULUS == 1)


def _normalise(z: complex) -> complex:
    if not (math.isfinite(z.real) and math.isfinite(z.imag)):
        raise Build31Error("phasor must be finite")
    magnitude = abs(z)
    if magnitude <= 1e-12:
        raise Build31Error("phasor magnitude is too small")
    return z / magnitude


def make_pilot(
    sample_count: int,
    *,
    sample_rate: int = 8192,
    carrier_hz: float = 512.0,
    gain: float = 1.0,
    phase_offset: float = 0.0,
) -> tuple[complex, ...]:
    if sample_count < 8 or sample_rate <= 0 or gain <= 0:
        raise Build31Error("invalid pilot configuration")
    if not all(math.isfinite(x) for x in (carrier_hz, gain, phase_offset)):
        raise Build31Error("pilot parameters must be finite")
    return tuple(
        gain * cmath.exp(1j * (2 * math.pi * carrier_hz * n / sample_rate + phase_offset))
        for n in range(sample_count)
    )


def emit_state(
    phasor: complex,
    *,
    observer: int = 1,
    pilot: Sequence[complex] | None = None,
    sample_count: int = 128,
    noise_sigma: float = 0.0,
    seed: int = 0,
) -> SignalState:
    """Emit a phasor as a calibrated signal-plus-pilot state."""
    if observer not in OBSERVER_UNITS:
        raise Build31Error("observer coordinate must be one of 1, 3, 5, 7")
    if noise_sigma < 0 or not math.isfinite(noise_sigma):
        raise Build31Error("noise sigma must be finite and non-negative")
    pilot_values = tuple(pilot) if pilot is not None else make_pilot(sample_count)
    if not pilot_values:
        raise Build31Error("pilot cannot be empty")
    if not all(math.isfinite(p.real) and math.isfinite(p.imag) for p in pilot_values):
        raise Build31Error("pilot samples must be finite")
    rng = random.Random(seed)
    z = _normalise(phasor)
    signal = tuple(
        p * z + complex(rng.gauss(0.0, noise_sigma), rng.gauss(0.0, noise_sigma))
        for p in pilot_values
    )
    return SignalState(PhaseOperand(signal, pilot_values), observer)


def encode_state(
    value: int,
    *,
    observer: int = 1,
    sample_count: int = 128,
    sample_rate: int = 8192,
    gain: float = 1.0,
    phase_offset: float = 0.0,
    noise_sigma: float = 0.0,
    seed: int = 0,
) -> SignalState:
    """Encode one semantic Z/8Z value in a selected observer coordinate."""
    if not isinstance(value, int) or not 0 <= value < MODULUS:
        raise Build31Error("semantic value must be an integer in Z/8Z")
    if observer not in OBSERVER_UNITS:
        raise Build31Error("observer coordinate must be one of 1, 3, 5, 7")
    encoded_index = (observer * value) % MODULUS
    operand = encode_phase_operand(
        encoded_index,
        sample_count=sample_count,
        sample_rate=sample_rate,
        gain=gain,
        phase_offset=phase_offset,
        noise_sigma=noise_sigma,
        seed=seed,
    )
    return SignalState(operand, observer)


def decode_state(state: SignalState) -> int:
    """Terminal observation: decode the phasor and map it to semantic Z/8Z."""
    coordinate_index = decode_phase_symbol(recover_phase_symbol(state.operand))
    return (inverse_unit_mod8(state.observer) * coordinate_index) % MODULUS


def reframe_state(
    state: SignalState,
    target_observer: int,
    *,
    pilot: Sequence[complex] | None = None,
    noise_sigma: float = 0.0,
    seed: int = 0,
) -> SignalState:
    """Change observer coordinates by a signal-domain group automorphism.

    If the source coordinate is u and target is v, apply z -> z**(v*u^-1).
    This is a phasor operation; it does not decode the semantic integer.
    """
    if target_observer not in OBSERVER_UNITS:
        raise Build31Error("target observer must be one of 1, 3, 5, 7")
    z = recover_phase_symbol(state.operand)
    exponent = (target_observer * inverse_unit_mod8(state.observer)) % MODULUS
    reframed = _normalise(z ** exponent)
    return emit_state(
        reframed,
        observer=target_observer,
        pilot=pilot if pilot is not None else state.operand.pilot,
        noise_sigma=noise_sigma,
        seed=seed,
    )


def apply_channel(state: SignalState, channel: ChannelSpec) -> SignalState:
    """Apply a scalar channel separately to data and its pilot reference."""
    rng = random.Random(channel.seed)
    h_signal = channel.gain * cmath.exp(1j * channel.phase)
    h_pilot = channel.gain * cmath.exp(1j * (channel.phase - channel.calibration_error))
    signal = tuple(
        x * h_signal + complex(rng.gauss(0.0, channel.noise_sigma),
                               rng.gauss(0.0, channel.noise_sigma))
        for x in state.operand.signal
    )
    pilot = tuple(p * h_pilot for p in state.operand.pilot)
    return SignalState(PhaseOperand(signal, pilot), state.observer)


def binary_signal_operation(
    opcode: str,
    a: SignalState,
    b: SignalState,
    *,
    output_observer: int | None = None,
    output_pilot: Sequence[complex] | None = None,
    output_noise_sigma: float = 0.0,
    seed: int = 0,
) -> SignalState:
    """Compose ADD8/SUB8 directly on calibrated signal states.

    Inputs are reframed into ``output_observer`` when necessary. Only complex
    phasors are recovered. No integer/symbol decode occurs in this function.
    """
    if opcode not in ("ADD8", "SUB8"):
        raise Build31Error("supported operations are ADD8 and SUB8")
    target = output_observer if output_observer is not None else a.observer
    if target not in OBSERVER_UNITS:
        raise Build31Error("output observer must be one of 1, 3, 5, 7")
    aa = a if a.observer == target else reframe_state(a, target, seed=seed + 1)
    bb = b if b.observer == target else reframe_state(b, target, seed=seed + 2)
    za = recover_phase_symbol(aa.operand)
    zb = recover_phase_symbol(bb.operand)
    if opcode == "ADD8":
        zout = za * zb
    else:
        zout = za * zb.conjugate()
    chosen_pilot = tuple(output_pilot) if output_pilot is not None else aa.operand.pilot
    return emit_state(
        zout,
        observer=target,
        pilot=chosen_pilot,
        noise_sigma=output_noise_sigma,
        seed=seed + 3,
    )


def symbolic_operation(opcode: str, a: int, b: int) -> int:
    """Verification oracle only; not called by signal-domain execution."""
    if opcode == "ADD8":
        return (a + b) % MODULUS
    if opcode == "SUB8":
        return (a - b) % MODULUS
    raise Build31Error("unsupported operation")


def symbolic_chain(a: int, b: int, c: int, op1: str, op2: str) -> int:
    return symbolic_operation(op2, symbolic_operation(op1, a, b), c)


def signal_chain(
    a: SignalState,
    b: SignalState,
    c: SignalState,
    op1: str,
    op2: str,
    *,
    intermediate_observer: int | None = None,
    output_observer: int | None = None,
    intermediate_pilot: Sequence[complex] | None = None,
    output_pilot: Sequence[complex] | None = None,
    intermediate_noise_sigma: float = 0.0,
    output_noise_sigma: float = 0.0,
    seed: int = 0,
) -> SignalState:
    """Execute two composable operations, with optional observer switching."""
    stage1_observer = intermediate_observer if intermediate_observer is not None else a.observer
    stage2_observer = output_observer if output_observer is not None else stage1_observer
    first = binary_signal_operation(
        op1, a, b, output_observer=stage1_observer, output_pilot=intermediate_pilot,
        output_noise_sigma=intermediate_noise_sigma, seed=seed + 10,
    )
    return binary_signal_operation(
        op2, first, c, output_observer=stage2_observer, output_pilot=output_pilot,
        output_noise_sigma=output_noise_sigma, seed=seed + 20,
    )


def phase_residual(reference: complex, observed: complex) -> float:
    """Signed wrapped phase error observed/reference in radians."""
    ratio = _normalise(observed) * _normalise(reference).conjugate()
    return math.atan2(ratio.imag, ratio.real)


def signal_state_summary(state: SignalState) -> dict[str, float | int]:
    z = recover_phase_symbol(state.operand)
    return {
        "observer": state.observer,
        "phase_rad": math.atan2(z.imag, z.real),
        "magnitude": abs(z),
        "sample_count": len(state.operand.signal),
    }
